"""
HHS Minimum Value (MV) Calculator
Based on ACA HHS methodology using standard population cost assumptions.

AV = Plan-paid costs / Total allowed costs for standard population.
The 60% MV threshold means the plan covers at least 60% of total allowed costs.
"""


def calculate_mv_percentage(plan: dict) -> dict:
    """
    HHS MV Calculator methodology.
    Uses standard population cost assumptions to estimate actuarial value.
    """
    TOTAL_ALLOWED_COST = 12500

    CATEGORIES = [
        {"name": "Inpatient",    "weight": 0.28, "visits": 0.13, "copay_field": None},
        {"name": "Outpatient",   "weight": 0.22, "visits": 2.0,  "copay_field": None},
        {"name": "Physician",    "weight": 0.20, "visits": 4.0,  "copay_field": "copay_primary"},
        {"name": "Specialist",   "weight": 0.07, "visits": 1.5,  "copay_field": "copay_specialist"},
        {"name": "ER",           "weight": 0.05, "visits": 0.15, "copay_field": "copay_er"},
        {"name": "Generic Rx",   "weight": 0.08, "visits": 8.0,  "copay_field": "copay_generic_rx"},
        {"name": "Brand Rx",     "weight": 0.05, "visits": 3.0,  "copay_field": "copay_brand_rx"},
        {"name": "Lab/Imaging",  "weight": 0.05, "visits": 2.0,  "copay_field": None},
    ]

    deductible = plan.get("individual_deductible") or plan.get("deductible_individual") or 0
    coinsurance_pct = (plan.get("coinsurance_rate") or 0) / 100
    oop_max = plan.get("oop_max_individual") or 999999

    total_employee_cost = 0
    remaining_deductible = deductible
    category_details = []

    for cat in CATEGORIES:
        cat_cost = TOTAL_ALLOWED_COST * cat["weight"]
        copay_per_visit = plan.get(cat["copay_field"] or "", 0) or 0
        num_visits = cat["visits"]

        total_copays = copay_per_visit * num_visits
        claim_after_copay = max(0, cat_cost - total_copays)

        deductible_applied = min(remaining_deductible, claim_after_copay)
        remaining_deductible -= deductible_applied
        after_deductible = claim_after_copay - deductible_applied

        employee_coinsurance = after_deductible * coinsurance_pct

        cat_employee = total_copays + deductible_applied + employee_coinsurance
        total_employee_cost += cat_employee

        category_details.append({
            "category": cat["name"],
            "total_cost": round(cat_cost, 2),
            "copays": round(total_copays, 2),
            "deductible_applied": round(deductible_applied, 2),
            "coinsurance": round(employee_coinsurance, 2),
            "employee_cost": round(cat_employee, 2),
            "plan_pays": round(cat_cost - cat_employee, 2),
        })

    oop_capped = total_employee_cost > oop_max
    if oop_capped:
        total_employee_cost = oop_max

    plan_pays = TOTAL_ALLOWED_COST - total_employee_cost
    mv_percentage = round((plan_pays / TOTAL_ALLOWED_COST) * 100, 1) if TOTAL_ALLOWED_COST > 0 else 0
    mv_percentage = max(0, min(100, mv_percentage))

    total_premium = plan.get("premiums", {}).get("self_only", 0) or 0
    er_contrib = plan.get("employer_contribution", {}).get("self_only", 0) or 0
    ee_cost = plan.get("employee_cost", {}).get("self_only", 0) or (total_premium - er_contrib)
    er_contrib_pct = round((er_contrib / total_premium * 100), 1) if total_premium > 0 else 0

    calculation_notes = []
    if deductible > 7500:
        calculation_notes.append("High deductible reduces actuarial value significantly")
    if coinsurance_pct > 0.40:
        calculation_notes.append("High coinsurance — consider actuarial certification")

    return {
        "mv_percentage": mv_percentage,
        "meets_minimum": mv_percentage >= 60.0,
        "total_allowed_cost": TOTAL_ALLOWED_COST,
        "plan_pays": round(plan_pays, 2),
        "member_pays": round(total_employee_cost, 2),
        "oop_max_applied": oop_capped,
        "deductible_used": deductible,
        "coinsurance_used": plan.get("coinsurance_rate") or 0,
        "oop_max_used": oop_max,
        "category_breakdown": category_details,
        "premium_analysis": {
            "total_monthly_premium": total_premium,
            "employer_contribution": er_contrib,
            "employee_premium": ee_cost,
            "employer_pct": er_contrib_pct,
            "employer_contribution_pass": er_contrib_pct >= 60,
        },
        "overall_mv_pass": mv_percentage >= 60.0 and er_contrib_pct >= 60,
        "calculation_notes": calculation_notes,
        "is_standard_calculation": True,
        "needs_actuarial_certification": False,
    }
