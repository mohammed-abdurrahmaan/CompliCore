"""
Predictive Intelligence Routes
- Hiring growth projection
- Financial exposure forecasting
- Scenario modeling
- AI-driven compliance alerts
"""

from fastapi import HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from collections import Counter
import math
import os
import uuid


class ScenarioRequest(BaseModel):
    add_full_time: int = 0
    add_part_time: int = 0
    remove_full_time: int = 0
    remove_part_time: int = 0
    change_contribution_pct: Optional[float] = None  # new employer contribution %
    new_plan_mv_pct: Optional[float] = None  # swap plan MV%
    drop_mec_coverage: bool = False


def register_predictive_routes(router, db, get_current_user):
    """Register all predictive intelligence routes."""

    async def _get_workforce_snapshot(employer_id):
        """Shared helper: gather employees, plans, enrollments for an employer."""
        employees = await db.employee_profiles.find(
            {"employer_id": employer_id}, {"_id": 0}
        ).to_list(500)
        if not employees:
            employees = await db.payroll_employees.find(
                {"employer_id": employer_id}, {"_id": 0}
            ).to_list(500)

        plans = await db.plan_library.find(
            {"employer_id": employer_id, "status": "active"}, {"_id": 0}
        ).to_list(100)

        enrollments = await db.enrollments.find(
            {"employer_id": employer_id, "status": "enrolled"}, {"_id": 0}
        ).to_list(500)

        assignments = await db.plan_assignments.find(
            {"employer_id": employer_id}, {"_id": 0}
        ).to_list(1000)

        employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})

        ft = [e for e in employees if e.get("is_full_time")]
        pt = [e for e in employees if not e.get("is_full_time")]
        pt_hours = sum(e.get("monthly_hours", 0) for e in pt)
        fte = round(pt_hours / 120, 2) if pt_hours > 0 else 0
        total_fte = len(ft) + fte
        is_ale = total_fte >= 50

        medical_plans = [p for p in plans if p.get("category") == "medical"]
        mec_plans = [p for p in medical_plans if p.get("mec_qualified")]
        mec_plan_ids = {p["id"] for p in mec_plans}

        # MEC coverage: count FT employees actually enrolled/assigned to MEC-qualified plans
        mec_covered_ids = set()
        for e in enrollments:
            if e.get("plan_id") in mec_plan_ids:
                mec_covered_ids.add(e.get("employee_id"))
        for a in assignments:
            if a.get("plan_id") in mec_plan_ids:
                mec_covered_ids.add(a.get("employee_id"))

        ft_ids = {e.get("id") for e in ft}
        mec_covered_ft = len(mec_covered_ids & ft_ids)
        mec_pct = round(mec_covered_ft / len(ft) * 100, 1) if ft else 100

        return {
            "employees": employees,
            "ft": ft,
            "pt": pt,
            "ft_count": len(ft),
            "pt_count": len(pt),
            "fte": fte,
            "total_fte": total_fte,
            "is_ale": is_ale,
            "plans": plans,
            "medical_plans": medical_plans,
            "mec_plans": mec_plans,
            "mec_pct": mec_pct,
            "mec_covered_ft": mec_covered_ft,
            "enrollments": enrollments,
            "assignments": assignments,
            "employer": employer,
        }

    # =============================================
    # 1. RULE-BASED COMPLIANCE ALERTS
    # =============================================

    @router.get("/predictive/alerts/{employer_id}")
    async def get_compliance_alerts(employer_id: str, user=Depends(get_current_user)):
        """Generate rule-based compliance alerts from current data."""
        snap = await _get_workforce_snapshot(employer_id)
        alerts = []

        # --- ALE Threshold ---
        buffer = 50 - snap["total_fte"]
        if snap["is_ale"]:
            alerts.append({
                "id": "ale-status",
                "severity": "info",
                "category": "ALE Status",
                "title": "Your organization is an Applicable Large Employer",
                "detail": f"Total FTE: {snap['total_fte']} (threshold: 50). ACA employer mandate applies.",
                "action": "Ensure all full-time employees are offered MEC coverage."
            })
        elif buffer <= 5:
            alerts.append({
                "id": "ale-near",
                "severity": "warning",
                "category": "ALE Threshold",
                "title": f"Only {round(buffer, 1)} FTEs away from ALE status",
                "detail": f"Current FTE: {snap['total_fte']}. Hiring {math.ceil(buffer)} more full-time employees will trigger ACA employer mandate.",
                "action": "Plan MEC coverage strategy before crossing the 50-FTE threshold."
            })
        elif buffer <= 10:
            alerts.append({
                "id": "ale-approaching",
                "severity": "low",
                "category": "ALE Threshold",
                "title": f"{round(buffer, 1)} FTEs away from ALE threshold",
                "detail": f"Current FTE: {snap['total_fte']}. Monitor hiring trends.",
                "action": "No immediate action needed, but plan ahead."
            })

        # --- MEC Coverage Gap ---
        if snap["is_ale"] and snap["ft_count"] > 0:
            pct = snap["mec_pct"]
            gap = snap["ft_count"] - snap["mec_covered_ft"]
            if pct < 95:
                penalty = round(max(0, snap["ft_count"] - 30) * 3340, 2)
                alerts.append({
                    "id": "mec-gap",
                    "severity": "critical",
                    "category": "MEC Coverage",
                    "title": f"MEC coverage at {pct}% — below 95% requirement",
                    "detail": f"{gap} full-time employee(s) not offered MEC. Potential 4980H(a) penalty: ${penalty:,.0f}/year.",
                    "action": f"Offer MEC-qualified coverage to {gap} uncovered employees immediately."
                })

        # --- Minimum Value Failures ---
        # MV fails if actuarial value < 60% OR employer contribution < 60% of premium
        mv_failing = []
        for p in snap["medical_plans"]:
            if p.get("mv_percentage") is None:
                continue
            mv_pct = p.get("mv_percentage", 0) or 0
            er_contrib = (p.get("employer_contribution") or {}).get("self_only", 0) or 0
            total_prem = (p.get("premiums") or {}).get("self_only", 0) or 0
            er_pct = (er_contrib / total_prem * 100) if total_prem > 0 else 0
            if mv_pct < 60 or er_pct < 60:
                mv_failing.append(p)
        if mv_failing:
            names = ", ".join(p["plan_name"] for p in mv_failing[:3])
            alerts.append({
                "id": "mv-fail",
                "severity": "critical",
                "category": "Minimum Value",
                "title": f"{len(mv_failing)} plan(s) below 60% MV threshold",
                "detail": f"Plans: {names}. Employees on these plans may qualify for marketplace subsidies, triggering 4980H(b) penalties ($4,460/employee/year).",
                "action": "Redesign plans to meet 60% MV or get actuarial certification."
            })

        # --- Affordability Risk ---
        if snap["medical_plans"]:
            cheapest = min(
                (p.get("employee_cost", {}).get("self_only", 0) for p in snap["medical_plans"]),
                default=0
            )
            annual_cost = cheapest * 12
            low_salary_at_risk = [
                e for e in snap["ft"]
                if (e.get("annual_salary") or 0) > 0 and annual_cost > (e.get("annual_salary") or 1) * 0.0996
            ]
            if low_salary_at_risk:
                alerts.append({
                    "id": "afford-risk",
                    "severity": "warning",
                    "category": "Affordability",
                    "title": f"{len(low_salary_at_risk)} employee(s) may find coverage unaffordable",
                    "detail": f"Lowest self-only cost is ${cheapest:,.0f}/mo (${annual_cost:,.0f}/yr). These employees' premiums exceed 9.96% of their W-2 wages.",
                    "action": "Consider increasing employer contribution or offering a lower-cost plan tier."
                })

        # --- Unenrolled Eligible Employees ---
        eligible_not_enrolled = [
            e for e in snap["ft"]
            if e.get("offered_mec") and not e.get("enrolled")
        ]
        if eligible_not_enrolled:
            alerts.append({
                "id": "unenrolled",
                "severity": "low",
                "category": "Enrollment",
                "title": f"{len(eligible_not_enrolled)} eligible employee(s) not enrolled",
                "detail": "These employees were offered coverage but haven't enrolled. While not a penalty risk (offer was made), low enrollment can affect plan pricing.",
                "action": "Send enrollment reminders or review plan attractiveness."
            })

        # --- No Plans Configured ---
        if not snap["medical_plans"]:
            alerts.append({
                "id": "no-plans",
                "severity": "critical",
                "category": "Plan Library",
                "title": "No medical plans configured",
                "detail": "Without active medical plans, no MEC offer can be made. If ALE, this triggers maximum penalties.",
                "action": "Add medical plans in the Plan Library immediately."
            })

        # --- Pending Certifications ---
        uncertified = [
            p for p in snap["medical_plans"]
            if p.get("mv_percentage") is None or (not p.get("mv_certified") and not p.get("certification_source"))
        ]
        if uncertified:
            alerts.append({
                "id": "uncertified",
                "severity": "low",
                "category": "Certifications",
                "title": f"{len(uncertified)} plan(s) without MV certification",
                "detail": "Plans without actuarial MV certification may not hold up to IRS scrutiny.",
                "action": "Request actuarial certification through the Marketplace."
            })

        alerts.sort(key=lambda a: {"critical": 0, "warning": 1, "info": 2, "low": 3}.get(a["severity"], 4))

        return {
            "alerts": alerts,
            "total": len(alerts),
            "critical": sum(1 for a in alerts if a["severity"] == "critical"),
            "warnings": sum(1 for a in alerts if a["severity"] == "warning"),
        }

    # =============================================
    # 2. HIRING GROWTH PROJECTION
    # =============================================

    @router.get("/predictive/growth/{employer_id}")
    async def get_growth_projection(employer_id: str, user=Depends(get_current_user)):
        """Project workforce growth based on hiring trends."""
        snap = await _get_workforce_snapshot(employer_id)
        employees = snap["employees"]

        # Parse hire dates and bucket by month
        now = datetime.now(timezone.utc)
        hires_by_month = Counter()
        for emp in employees:
            hd = emp.get("hire_date", "")
            if hd:
                try:
                    dt = datetime.fromisoformat(hd).replace(tzinfo=timezone.utc) if "T" not in hd else datetime.fromisoformat(hd)
                    key = f"{dt.year}-{dt.month:02d}"
                    hires_by_month[key] = hires_by_month.get(key, 0) + 1
                except Exception:
                    pass

        # Build monthly history for last 12 months
        history = []
        for i in range(11, -1, -1):
            dt = now - timedelta(days=30 * i)
            key = f"{dt.year}-{dt.month:02d}"
            history.append({"month": key, "hires": hires_by_month.get(key, 0)})

        # Average monthly hire rate (last 6 months with data)
        recent = [h["hires"] for h in history[-6:]]
        avg_monthly_hires = round(sum(recent) / max(len(recent), 1), 1)

        # Project next 6 months
        projections = []
        projected_total = len(employees)
        projected_ft = snap["ft_count"]
        ft_ratio = snap["ft_count"] / max(len(employees), 1)

        for i in range(1, 7):
            dt = now + timedelta(days=30 * i)
            new_hires = round(avg_monthly_hires)
            new_ft = round(new_hires * ft_ratio)
            projected_total += new_hires
            projected_ft += new_ft
            projected_fte = projected_ft + snap["fte"]
            projections.append({
                "month": f"{dt.year}-{dt.month:02d}",
                "projected_total": projected_total,
                "projected_ft": projected_ft,
                "projected_fte": round(projected_fte, 1),
                "is_ale": projected_fte >= 50,
                "new_hires": new_hires,
            })

        # When does ALE trigger?
        ale_trigger_month = None
        if not snap["is_ale"]:
            for p in projections:
                if p["is_ale"]:
                    ale_trigger_month = p["month"]
                    break

        return {
            "current": {
                "total": len(employees),
                "full_time": snap["ft_count"],
                "part_time": snap["pt_count"],
                "total_fte": snap["total_fte"],
                "is_ale": snap["is_ale"],
            },
            "avg_monthly_hires": avg_monthly_hires,
            "ft_hire_ratio": round(ft_ratio * 100, 1),
            "history": history,
            "projections": projections,
            "ale_trigger_month": ale_trigger_month,
        }

    # =============================================
    # 3. FINANCIAL EXPOSURE FORECASTING
    # =============================================

    @router.get("/predictive/exposure/{employer_id}")
    async def get_financial_exposure(employer_id: str, user=Depends(get_current_user)):
        """Forecast financial exposure: penalties, premiums, worst-case scenarios."""
        snap = await _get_workforce_snapshot(employer_id)
        ft_count = snap["ft_count"]

        # Penalty rates (2025)
        PENALTY_A_RATE = 3340  # per FT employee (minus 30)
        PENALTY_B_RATE = 5010  # per affected employee

        # Current MEC coverage — use enrollment/assignment-based calculation from snapshot
        mec_pct = snap["mec_pct"]

        # 4980H(a) penalty
        penalty_a = round(max(0, ft_count - 30) * PENALTY_A_RATE) if mec_pct < 95 and snap["is_ale"] else 0

        # 4980H(b) penalty: employees on MV-failing plans
        mv_failing_plans = []
        for p in snap["medical_plans"]:
            if p.get("mv_percentage") is None:
                continue
            mv_pct = p.get("mv_percentage", 0) or 0
            er_contrib = (p.get("employer_contribution") or {}).get("self_only", 0) or 0
            total_prem = (p.get("premiums") or {}).get("self_only", 0) or 0
            er_pct = (er_contrib / total_prem * 100) if total_prem > 0 else 0
            if mv_pct < 60 or er_pct < 60:
                mv_failing_plans.append(p)
        failing_ids = {p["id"] for p in mv_failing_plans}
        b_affected = sum(1 for a in snap["assignments"] if a.get("plan_id") in failing_ids)
        penalty_b = b_affected * PENALTY_B_RATE

        # Affordability penalty exposure
        cheapest_ee_cost = 0
        if snap["medical_plans"]:
            cheapest_ee_cost = min(
                (p.get("employee_cost", {}).get("self_only", 0) for p in snap["medical_plans"]),
                default=0
            )
        annual_ee_cost = cheapest_ee_cost * 12
        afford_at_risk = sum(
            1 for e in snap["ft"]
            if (e.get("annual_salary") or 0) > 0 and annual_ee_cost > (e.get("annual_salary") or 1) * 0.0996
        )
        afford_penalty = afford_at_risk * PENALTY_B_RATE

        # Premium costs
        total_er_annual = sum(e.get("employer_contribution", 0) * 12 for e in snap["enrollments"])
        total_ee_annual = sum(e.get("employee_premium", 0) * 12 for e in snap["enrollments"])

        # Worst case: lose ALE + no coverage
        worst_case_a = round(max(0, ft_count - 30) * PENALTY_A_RATE) if snap["is_ale"] else 0

        return {
            "current_exposure": {
                "penalty_a": penalty_a,
                "penalty_a_reason": "4980H(a): MEC not offered to 95%+ FT employees" if penalty_a > 0 else "Compliant",
                "penalty_b": penalty_b,
                "penalty_b_reason": f"4980H(b): {b_affected} employees on MV-failing plans" if penalty_b > 0 else "Compliant",
                "affordability_exposure": afford_penalty,
                "afford_at_risk_count": afford_at_risk,
                "total_penalty_exposure": penalty_a + penalty_b + afford_penalty,
            },
            "premium_costs": {
                "annual_employer_cost": round(total_er_annual),
                "annual_employee_cost": round(total_ee_annual),
                "annual_total": round(total_er_annual + total_ee_annual),
                "monthly_employer_cost": round(total_er_annual / 12) if total_er_annual else 0,
            },
            "worst_case": {
                "max_penalty_a": worst_case_a,
                "max_penalty_b": ft_count * PENALTY_B_RATE,
                "total_worst_case": worst_case_a + ft_count * PENALTY_B_RATE,
            },
            "rates": {
                "penalty_a_rate": PENALTY_A_RATE,
                "penalty_b_rate": PENALTY_B_RATE,
                "affordability_threshold": 9.96,
            },
            "workforce": {
                "ft_count": ft_count,
                "mec_pct": mec_pct,
                "mec_covered_ft": snap["mec_covered_ft"],
                "is_ale": snap["is_ale"],
                "total_fte": snap["total_fte"],
            },
        }

    # =============================================
    # 4. SCENARIO MODELING
    # =============================================

    @router.post("/predictive/scenario/{employer_id}")
    async def run_scenario(employer_id: str, data: ScenarioRequest, user=Depends(get_current_user)):
        """What-if scenario modeling for workforce and benefits changes."""
        snap = await _get_workforce_snapshot(employer_id)

        PENALTY_A_RATE = 3340
        PENALTY_B_RATE = 5010

        # Current state
        current_ft = snap["ft_count"]
        current_pt = snap["pt_count"]
        current_fte = snap["total_fte"]
        current_ale = snap["is_ale"]

        current_mec_pct = snap["mec_pct"]
        mec_covered = snap["mec_covered_ft"]
        current_penalty_a = round(max(0, current_ft - 30) * PENALTY_A_RATE) if current_mec_pct < 95 and current_ale else 0

        # Scenario state
        new_ft = max(0, current_ft + data.add_full_time - data.remove_full_time)
        new_pt = max(0, current_pt + data.add_part_time - data.remove_part_time)
        # Assume new PT employees work average 20hrs/week
        new_pt_fte = round(new_pt * (20 * 4.33) / 120, 2)
        new_total_fte = round(new_ft + new_pt_fte, 2)
        new_ale = new_total_fte >= 50

        # MEC coverage in scenario: new hires won't have MEC enrollment yet
        new_mec_covered = mec_covered if not data.drop_mec_coverage else 0
        new_mec_pct = round(new_mec_covered / new_ft * 100, 1) if new_ft > 0 else 100

        # Penalty A
        new_penalty_a = round(max(0, new_ft - 30) * PENALTY_A_RATE) if new_mec_pct < 95 and new_ale else 0

        # Penalty B from MV change
        mv_affected = 0
        if data.new_plan_mv_pct is not None and data.new_plan_mv_pct < 60:
            mv_affected = new_ft  # worst case: all FT on the failing plan
        new_penalty_b = mv_affected * PENALTY_B_RATE

        # Premium impact
        current_er_monthly = sum(e.get("employer_contribution", 0) for e in snap["enrollments"])
        if data.change_contribution_pct is not None and snap["enrollments"]:
            avg_total = sum(e.get("total_premium", 0) for e in snap["enrollments"]) / len(snap["enrollments"])
            new_er_per_ee = avg_total * (data.change_contribution_pct / 100)
            projected_er_monthly = new_er_per_ee * len(snap["enrollments"])
        else:
            projected_er_monthly = current_er_monthly

        return {
            "current": {
                "ft": current_ft,
                "pt": current_pt,
                "total_fte": current_fte,
                "is_ale": current_ale,
                "mec_pct": current_mec_pct,
                "penalty_a": current_penalty_a,
                "penalty_b": 0,
                "total_penalty": current_penalty_a,
                "monthly_er_cost": round(current_er_monthly),
            },
            "scenario": {
                "ft": new_ft,
                "pt": new_pt,
                "total_fte": new_total_fte,
                "is_ale": new_ale,
                "mec_pct": new_mec_pct,
                "penalty_a": new_penalty_a,
                "penalty_b": new_penalty_b,
                "total_penalty": new_penalty_a + new_penalty_b,
                "monthly_er_cost": round(projected_er_monthly),
            },
            "delta": {
                "fte_change": round(new_total_fte - current_fte, 2),
                "ale_changed": current_ale != new_ale,
                "penalty_change": (new_penalty_a + new_penalty_b) - current_penalty_a,
                "cost_change_monthly": round(projected_er_monthly - current_er_monthly),
            },
            "warnings": _scenario_warnings(snap, data, new_total_fte, new_ale, new_mec_pct),
        }

    def _scenario_warnings(snap, data, new_fte, new_ale, new_mec_pct):
        warnings = []
        if not snap["is_ale"] and new_ale:
            warnings.append("This scenario triggers ALE status. Full ACA employer mandate will apply.")
        if snap["is_ale"] and not new_ale:
            warnings.append("This scenario drops below ALE threshold. Employer mandate no longer applies.")
        if new_mec_pct < 95 and new_ale:
            warnings.append(f"MEC coverage would be {new_mec_pct}% — below 95% safe harbor. Penalty A applies.")
        if data.new_plan_mv_pct is not None and data.new_plan_mv_pct < 60:
            warnings.append(f"New plan MV of {data.new_plan_mv_pct}% is below 60%. Penalty B risk for all enrolled employees.")
        if data.drop_mec_coverage:
            warnings.append("Dropping MEC coverage triggers maximum 4980H(a) penalties for ALE employers.")
        return warnings


    # =============================================
    # 5. AI-POWERED SUMMARY (tab-specific)
    # =============================================

    class AiSummaryRequest(BaseModel):
        tab: str = "alerts"

    @router.post("/predictive/ai-summary/{employer_id}")
    async def get_ai_summary(employer_id: str, body: AiSummaryRequest = AiSummaryRequest(), user=Depends(get_current_user)):
        """Generate AI-powered compliance insights, tailored per tab."""
        snap = await _get_workforce_snapshot(employer_id)
        employer_name = snap["employer"].get("name", "Employer") if snap["employer"] else "Employer"
        tab = body.tab

        ft_count = snap["ft_count"]
        pt_count = snap["pt_count"]
        total_fte = snap["total_fte"]
        is_ale = snap["is_ale"]
        mec_pct = snap["mec_pct"]
        mec_covered = snap["mec_covered_ft"]

        mv_failing = []
        for p in snap["medical_plans"]:
            if p.get("mv_percentage") is None:
                continue
            mv_pct = p.get("mv_percentage", 0) or 0
            er_contrib = (p.get("employer_contribution") or {}).get("self_only", 0) or 0
            total_prem = (p.get("premiums") or {}).get("self_only", 0) or 0
            er_pct = (er_contrib / total_prem * 100) if total_prem > 0 else 0
            if mv_pct < 60 or er_pct < 60:
                mv_failing.append(p)

        enrollments = snap["enrollments"]
        enrolled_count = len(enrollments)
        declined = await db.enrollments.count_documents({"employer_id": employer_id, "status": "declined"})

        hire_dates = []
        for emp in snap["employees"]:
            hd = emp.get("hire_date", "")
            if hd:
                try:
                    dt = datetime.fromisoformat(hd)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    hire_dates.append(dt)
                except Exception:
                    pass

        now_utc = datetime.now(timezone.utc)
        recent_hires_6mo = sum(1 for d in hire_dates if d > now_utc - timedelta(days=180)) if hire_dates else 0
        recent_hires_3mo = sum(1 for d in hire_dates if d > now_utc - timedelta(days=90)) if hire_dates else 0

        penalty_a = round(max(0, ft_count - 30) * 3340) if mec_pct < 95 and is_ale else 0
        penalty_b = len(mv_failing) * 5010 if mv_failing else 0
        total_penalty = penalty_a + penalty_b

        total_er_monthly = sum(e.get("employer_contribution", 0) for e in enrollments)
        total_ee_monthly = sum(e.get("employee_premium", 0) for e in enrollments)

        cheapest_ee_cost = 0
        if snap["medical_plans"]:
            cheapest_ee_cost = min((p.get("employee_cost", {}).get("self_only", 0) for p in snap["medical_plans"]), default=0)
        annual_ee_cost = cheapest_ee_cost * 12
        afford_at_risk = sum(1 for e in snap["ft"] if (e.get("annual_salary") or 0) > 0 and annual_ee_cost > (e.get("annual_salary") or 1) * 0.0996)

        ctx = {
            "employer_name": employer_name, "ft_count": ft_count, "pt_count": pt_count,
            "total_fte": total_fte, "is_ale": is_ale, "mec_pct": mec_pct,
            "mec_covered": mec_covered, "mv_failing": mv_failing,
            "enrolled_count": enrolled_count, "declined": declined,
            "recent_hires_6mo": recent_hires_6mo, "recent_hires_3mo": recent_hires_3mo,
            "penalty_a": penalty_a, "penalty_b": penalty_b, "total_penalty": total_penalty,
            "total_er_monthly": total_er_monthly, "total_ee_monthly": total_ee_monthly,
            "afford_at_risk": afford_at_risk, "snap": snap,
        }

        api_key = os.environ.get("EMERGENT_LLM_KEY", "")
        if api_key:
            try:
                from emergentintegrations.llm.chat import LlmChat, UserMessage
                prompt_data = _build_llm_prompt(tab, ctx)
                for provider, model in [("google", "gemini-2.0-flash"), ("openai", "gpt-4o-mini")]:
                    try:
                        chat = LlmChat(
                            api_key=api_key,
                            session_id=f"pi-{tab}-{employer_id}-{uuid.uuid4().hex[:8]}",
                            system_message=prompt_data["system"]
                        ).with_model(provider, model)
                        response = await chat.send_message(UserMessage(text=prompt_data["user"]))
                        return {"summary": response, "generated": True, "tab": tab, "generated_at": datetime.now(timezone.utc).isoformat()}
                    except Exception:
                        continue
            except Exception:
                pass

        return _generate_tab_summary(tab, ctx)


def _build_llm_prompt(tab, ctx):
    base = f"Company: {ctx['employer_name']}, {ctx['ft_count']} FT + {ctx['pt_count']} PT = {ctx['total_fte']} FTE, ALE: {'Yes' if ctx['is_ale'] else 'No'}, MEC: {ctx['mec_pct']}%, Penalty: ${ctx['total_penalty']:,}"
    prompts = {
        "alerts": {
            "system": "You are an ACA compliance analyst. Analyze alerts and prioritize risks. Be concise with bullet points. Under 200 words.",
            "user": f"Prioritize these compliance risks and suggest immediate actions:\n{base}\nMV-failing plans: {len(ctx['mv_failing'])}\nAffordability at-risk: {ctx['afford_at_risk']}\nUncovered FT: {ctx['ft_count'] - ctx['mec_covered']}"
        },
        "growth": {
            "system": "You are a workforce planning analyst for ACA compliance. Analyze hiring trends and ALE impact. Under 200 words.",
            "user": f"Analyze hiring growth impact on ACA compliance:\n{base}\nRecent hires (6mo): {ctx['recent_hires_6mo']}, (3mo): {ctx['recent_hires_3mo']}\nALE buffer: {round(50 - ctx['total_fte'], 1)} FTEs"
        },
        "exposure": {
            "system": "You are a financial analyst for ACA penalty exposure. Provide cost analysis and savings recommendations. Under 200 words.",
            "user": f"Analyze financial exposure:\n{base}\n4980H(a): ${ctx['penalty_a']:,}, 4980H(b): ${ctx['penalty_b']:,}\nEmployer premiums: ${ctx['total_er_monthly']:,}/mo\nAffordability at-risk: {ctx['afford_at_risk']}"
        },
        "scenario": {
            "system": "You are an ACA strategic advisor. Suggest what-if scenarios for this employer. Under 200 words.",
            "user": f"Suggest valuable scenarios:\n{base}\nMEC gap: {ctx['ft_count'] - ctx['mec_covered']} uncovered\nMV-failing: {len(ctx['mv_failing'])} plans"
        },
    }
    return prompts.get(tab, prompts["alerts"])


def _generate_tab_summary(tab, ctx):
    lines = []
    name = ctx["employer_name"]
    ft = ctx["ft_count"]
    fte = ctx["total_fte"]
    is_ale = ctx["is_ale"]
    mec_pct = ctx["mec_pct"]
    covered = ctx["mec_covered"]
    gap = ft - covered
    penalty_a = ctx["penalty_a"]
    penalty_b = ctx["penalty_b"]
    total_penalty = ctx["total_penalty"]

    if tab == "alerts":
        if total_penalty > 0:
            lines.append("COMPLIANCE RISK: HIGH")
            lines.append(f"{name} faces ${total_penalty:,}/year in potential IRS penalties. Immediate action required.")
        else:
            lines.append("COMPLIANCE STATUS: GOOD")
            lines.append(f"{name} is currently compliant with ACA employer mandate requirements.")
        lines.append("")
        if mec_pct < 95 and is_ale:
            target = math.ceil(ft * 0.95) - covered
            lines.append(f"CRITICAL — MEC Coverage at {mec_pct}%")
            lines.append(f"- {gap} of {ft} full-time employees lack MEC-qualified coverage")
            lines.append(f"- Enroll {target} more to reach 95% and eliminate ${penalty_a:,} penalty")
        if ctx["mv_failing"]:
            names = ", ".join(p["plan_name"] for p in ctx["mv_failing"][:3])
            lines.append(f"\nCRITICAL — {len(ctx['mv_failing'])} plan(s) below 60% MV: {names}")
            lines.append(f"- Each affected employee triggers $5,010/year in 4980H(b) penalties")
        if ctx["afford_at_risk"] > 0:
            lines.append(f"\nWARNING — {ctx['afford_at_risk']} employee(s) may find coverage unaffordable")
            lines.append(f"- Premiums exceed 9.96% of their income")
        total_dec = ctx["enrolled_count"] + ctx["declined"]
        if total_dec > 0:
            rate = round(ctx["enrolled_count"] / total_dec * 100)
            if rate < 70:
                lines.append(f"\nINFO — Enrollment rate at {rate}% — low participation may affect plan pricing")
        lines.append("\nPRIORITY ACTIONS:")
        acts = []
        if mec_pct < 95 and is_ale:
            acts.append("Extend MEC offers to all uncovered full-time employees")
        if ctx["mv_failing"]:
            acts.append("Get actuarial certification or redesign MV-failing plans")
        if ctx["afford_at_risk"] > 0:
            acts.append("Review contribution structure for affordability compliance")
        if not acts:
            acts.append("Maintain current compliance posture and monitor changes")
        for i, a in enumerate(acts, 1):
            lines.append(f"  {i}. {a}")

    elif tab == "growth":
        buffer = round(50 - fte, 1)
        lines.append("WORKFORCE GROWTH ANALYSIS")
        lines.append(f"{name}: {ft} full-time + {ctx['pt_count']} part-time = {fte} FTE")
        lines.append("")
        if is_ale:
            lines.append(f"ALE STATUS — Active ({abs(buffer)} FTE over 50 threshold)")
            lines.append(f"- ACA employer mandate applies to all full-time employees")
            lines.append(f"- Every new FT hire increases penalty base by $3,340/year if MEC < 95%")
        else:
            lines.append(f"ALE STATUS — Not ALE ({buffer} FTE below threshold)")
            if buffer <= 5:
                lines.append(f"- CAUTION: Only {buffer} FTEs away — {math.ceil(buffer)} new FT hires trigger mandate")
                lines.append(f"- Have MEC coverage ready before crossing the threshold")
            elif buffer <= 10:
                lines.append(f"- Approaching threshold — plan MEC strategy proactively")
        lines.append(f"\nHIRING TREND")
        lines.append(f"- Last 6 months: {ctx['recent_hires_6mo']} new hires")
        lines.append(f"- Last 3 months: {ctx['recent_hires_3mo']} new hires")
        if ctx["recent_hires_6mo"] > 0:
            monthly_rate = round(ctx["recent_hires_6mo"] / 6, 1)
            lines.append(f"- Average: {monthly_rate} hires/month")
            if is_ale and mec_pct < 95:
                lines.append(f"- Each new uncovered FT hire adds $3,340/year to penalty exposure")
        else:
            lines.append(f"- No recent hiring activity detected")
        lines.append(f"\nKEY INSIGHT:")
        if is_ale and ctx["recent_hires_6mo"] > 3:
            lines.append(f"  Active hiring + low MEC coverage = rapidly growing penalty. Prioritize coverage.")
        elif not is_ale and buffer <= 5:
            lines.append(f"  {math.ceil(buffer)} hires from ALE status. Prepare MEC plans before crossing 50 FTE.")
        else:
            lines.append(f"  Workforce stable. Monitor seasonal or project-based hiring that could shift FTE.")

    elif tab == "exposure":
        monthly_penalty = round(total_penalty / 12)
        lines.append("FINANCIAL EXPOSURE ANALYSIS")
        lines.append(f"Annual penalty risk: ${total_penalty:,} (${monthly_penalty:,}/month)")
        lines.append("")
        if penalty_a > 0:
            lines.append(f"4980H(a) PENALTY — ${penalty_a:,}/year")
            lines.append(f"- MEC coverage at {mec_pct}% (needs 95%)")
            lines.append(f"- Formula: ({ft} - 30) x $3,340 = {max(0, ft - 30)} x $3,340")
            lines.append(f"- TO ELIMINATE: Offer MEC plans to {gap} more FT employees")
        if penalty_b > 0:
            lines.append(f"\n4980H(b) PENALTY — ${penalty_b:,}/year")
            lines.append(f"- {len(ctx['mv_failing'])} plan(s) below 60% minimum value")
            lines.append(f"- Affected employees may get marketplace subsidies ($5,010 each)")
        if ctx["afford_at_risk"] > 0:
            lines.append(f"\nAFFORDABILITY RISK — ${ctx['afford_at_risk'] * 5010:,}/year potential")
            lines.append(f"- {ctx['afford_at_risk']} employees' premiums exceed 9.96% of income")
        er_annual = ctx["total_er_monthly"] * 12
        lines.append(f"\nCOST SUMMARY")
        lines.append(f"- Employer premiums: ${er_annual:,.0f}/year (${ctx['total_er_monthly']:,.0f}/mo)")
        lines.append(f"- Penalty exposure: ${total_penalty:,}/year")
        lines.append(f"- Total ACA spend: ${er_annual + total_penalty:,.0f}/year")
        lines.append(f"\nBOTTOM LINE:")
        if total_penalty > 0:
            lines.append(f"  Every month costs ${monthly_penalty:,} in avoidable penalties. 12-month total: ${total_penalty:,}.")
        else:
            lines.append(f"  No current penalty exposure. Maintain coverage and monitor affordability.")

    elif tab == "scenario":
        lines.append("RECOMMENDED SCENARIOS TO MODEL")
        lines.append(f"Based on {name}'s profile ({fte} FTE, {mec_pct}% MEC, ${total_penalty:,} exposure):")
        lines.append("")
        n = 1
        if mec_pct < 95 and is_ale:
            lines.append(f"{n}. FIX MEC COMPLIANCE")
            lines.append(f"   Imagine enrolling {gap} uncovered FT employees in MEC plans")
            lines.append(f"   Expected: Penalty drops from ${total_penalty:,} to $0")
            lines.append("")
            n += 1
        if is_ale:
            lines.append(f"{n}. GROWTH IMPACT")
            lines.append(f"   Try: Add 10 or 25 full-time employees")
            lines.append(f"   See: How penalties scale with growth at {mec_pct}% MEC")
            lines.append("")
            n += 1
        if not is_ale:
            buffer = round(50 - fte, 1)
            lines.append(f"{n}. ALE TRIGGER POINT")
            lines.append(f"   Try: Add {math.ceil(buffer)} full-time employees")
            lines.append(f"   See: When ACA mandate kicks in")
            lines.append("")
            n += 1
        if ctx["mv_failing"]:
            lines.append(f"{n}. PLAN REDESIGN")
            lines.append(f"   Try: Set new plan MV to 65% (above 60%)")
            lines.append(f"   See: 4980H(b) penalties eliminated")
            lines.append("")
            n += 1
        lines.append(f"{n}. WORST CASE — 'Drop MEC' preset")
        lines.append(f"   See: Maximum penalty exposure if coverage lapses")
        lines.append("")
        n += 1
        if is_ale:
            lines.append(f"{n}. DOWNSIZING — Reduce 10 FT employees")
            fte_after = round(fte - 10, 1)
            lines.append(f"   See: {'Drops below ALE — no more mandate' if fte_after < 50 else 'Still ALE, but reduced penalty base'}")

    return {
        "summary": "\n".join(lines),
        "generated": True,
        "tab": tab,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
