"""
ADP Workforce Now API Integration Service
Handles OAuth 2.0 authentication, worker data fetching, and schema mapping.
"""
import httpx
import logging
import os
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

ADP_ENV = os.environ.get("ADP_ENVIRONMENT", "sandbox")
ADP_CLIENT_ID = os.environ.get("ADP_CLIENT_ID", "")
ADP_CLIENT_SECRET = os.environ.get("ADP_CLIENT_SECRET", "")
ADP_REDIRECT_URI = os.environ.get("ADP_REDIRECT_URI", "")

ADP_BASE_URLS = {
    "sandbox": "https://api.adp.com",
    "production": "https://api.adp.com",
}

ADP_AUTH_URL = "https://accounts.adp.com/auth/oauth/v2/authorize"
ADP_TOKEN_URL = "https://accounts.adp.com/auth/oauth/v2/token"
ADP_WORKERS_URL = "/hr/v2/workers"


def is_adp_configured():
    return bool(ADP_CLIENT_ID and ADP_CLIENT_SECRET)


def get_adp_base_url():
    return ADP_BASE_URLS.get(ADP_ENV, ADP_BASE_URLS["sandbox"])


def build_auth_url(state: str) -> str:
    redirect = ADP_REDIRECT_URI or f"{os.environ.get('FRONTEND_URL', '')}/adp/callback"
    return (
        f"{ADP_AUTH_URL}?"
        f"response_type=code&"
        f"client_id={ADP_CLIENT_ID}&"
        f"redirect_uri={redirect}&"
        f"scope=api&"
        f"state={state}"
    )


async def exchange_code_for_token(code: str) -> dict:
    redirect = ADP_REDIRECT_URI or f"{os.environ.get('FRONTEND_URL', '')}/adp/callback"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            ADP_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
                "client_id": ADP_CLIENT_ID,
                "client_secret": ADP_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        data["obtained_at"] = datetime.now(timezone.utc).isoformat()
        return data


async def refresh_adp_token(refresh_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            ADP_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": ADP_CLIENT_ID,
                "client_secret": ADP_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        data = resp.json()
        data["obtained_at"] = datetime.now(timezone.utc).isoformat()
        return data


async def fetch_workers(access_token: str, top: int = 200, skip: int = 0) -> list:
    base = get_adp_base_url()
    url = f"{base}{ADP_WORKERS_URL}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    params = {"$top": top, "$skip": skip}
    all_workers = []
    page = 0

    async with httpx.AsyncClient(timeout=60) as client:
        while True:
            params["$skip"] = skip + (page * top)
            try:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", "5"))
                    logger.warning(f"ADP rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                data = resp.json()
                workers = data.get("workers", [])
                if not workers:
                    break
                all_workers.extend(workers)
                if len(workers) < top:
                    break
                page += 1
            except httpx.HTTPStatusError as e:
                logger.error(f"ADP API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"ADP fetch error: {e}")
                raise

    return all_workers


def _safe_get(data: dict, path: str, default=None):
    keys = path.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        elif isinstance(val, list) and k.isdigit():
            idx = int(k)
            val = val[idx] if idx < len(val) else None
        else:
            return default
        if val is None:
            return default
    return val


def transform_adp_worker(adp_worker: dict, employer_id: str) -> dict:
    """
    Transform an ADP worker object into our internal payroll_employees schema.
    ADP worker structure can vary; this handles the common Workforce Now fields.
    """
    legal_name = _safe_get(adp_worker, "person.legalName", {}) or {}
    first_name = legal_name.get("givenName", "") or legal_name.get("firstName", "")
    last_name = legal_name.get("familyName1", "") or legal_name.get("lastName", "")
    name = f"{first_name} {last_name}".strip() or "Unknown"

    work_assignments = adp_worker.get("workAssignments", [])
    primary = work_assignments[0] if work_assignments else {}

    worker_status = _safe_get(primary, "workerStatusCode.codeValue", "A")
    dept_name = _safe_get(primary, "homeOrganizationalUnits.0.nameCode.shortName", "")
    if not dept_name:
        dept_name = _safe_get(primary, "assignedOrganizationalUnits.0.nameCode.shortName", "General")

    std_hours = float(_safe_get(primary, "standardHours.hoursQuantity", 0) or 0)
    if std_hours == 0:
        std_hours = float(primary.get("standardHoursPerWeek", 0) or 0)

    is_full_time = std_hours >= 30
    work_level = _safe_get(primary, "workerTypeCode.codeValue", "")
    if work_level:
        is_full_time = work_level.upper() in ("F", "FT", "FULL", "FULL-TIME", "FULL_TIME") or std_hours >= 30

    base_pay = _safe_get(primary, "baseRemuneration.effectiveDate", None)
    salary_amount = float(_safe_get(primary, "baseRemuneration.payPeriodRateAmount.amountValue", 0) or 0)
    rate_code = _safe_get(primary, "baseRemuneration.payPeriodRateAmount.unitCode.codeValue", "")
    annual_salary = salary_amount
    if rate_code and rate_code.upper() == "HOURLY":
        annual_salary = salary_amount * std_hours * 52
    elif rate_code and rate_code.upper() in ("MONTHLY", "MO"):
        annual_salary = salary_amount * 12
    elif rate_code and rate_code.upper() in ("BIWEEKLY", "SEMIMONTHLY"):
        annual_salary = salary_amount * 26

    hire_date_str = _safe_get(primary, "hireDate", None) or _safe_get(adp_worker, "workerDates.originalHireDate", None)
    hire_date = hire_date_str or "2023-01-01"

    email_obj = _safe_get(adp_worker, "person.communication.emails.0.emailUri", "")
    worker_id = _safe_get(adp_worker, "associateOID", "") or _safe_get(adp_worker, "workerID.idValue", "")

    offered_mec = _safe_get(adp_worker, "benefits.minimumEssentialCoverageOfferCode", None) is not None
    if not offered_mec:
        offered_mec = is_full_time

    import uuid
    return {
        "id": str(uuid.uuid4()),
        "employer_id": employer_id,
        "name": name,
        "employee_id": f"ADP-{worker_id}" if worker_id else f"ADP-{str(uuid.uuid4())[:8]}",
        "department": dept_name or "General",
        "employment_type": "full_time" if is_full_time else "part_time",
        "weekly_hours": std_hours if std_hours > 0 else (40 if is_full_time else 20),
        "monthly_hours": round((std_hours if std_hours > 0 else (40 if is_full_time else 20)) * 4.33, 1),
        "annual_salary": round(annual_salary) if annual_salary > 0 else 50000,
        "hourly_rate": round(annual_salary / (max(std_hours, 1) * 52), 2) if annual_salary > 0 else 0,
        "hire_date": hire_date,
        "offered_mec": offered_mec,
        "enrolled": offered_mec,
        "email": email_obj or "",
        "adp_worker_id": worker_id,
        "source": "adp",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
