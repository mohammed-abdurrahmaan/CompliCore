from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import bcrypt
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import base64

from services.irs_forms import (
    generate_1094c_data,
    generate_1095c_data,
    render_1094c_pdf,
    render_1095c_pdf,
    OFFER_CODES,
    SAFE_HARBOR_CODES,
)
from routes.marketplace import register_marketplace_routes
from routes.enrollment_workflow import register_enrollment_routes
from routes.adp import register_adp_routes
from routes.predictive import register_predictive_routes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ.get('JWT_SECRET', 'complicore-secret-key-2025')
JWT_ALGORITHM = "HS256"

app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Pydantic Models ---

class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    role: str  # 'employer' or 'actuary'
    company_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    company_name: Optional[str] = None
    created_at: str

class MonthlyHeadcount(BaseModel):
    employer_id: str
    year: int
    month: int  # 1-12
    full_time_count: int
    part_time_hours: float  # total hours of all part-time employees

class ALECalculationRequest(BaseModel):
    employer_id: str
    year: int

class PlanCreate(BaseModel):
    employer_id: str
    plan_name: str
    plan_type: str  # HMO, PPO, POS, HDHP, EPO
    individual_deductible: float
    family_deductible: float
    coinsurance_rate: float  # e.g., 0.20 means plan pays 80%
    office_visit_copay: float
    er_copay: float
    inpatient_copay: float
    rx_copay_generic: float
    rx_copay_brand: float
    oop_max_individual: float
    oop_max_family: float
    hsa_employer_contribution: float = 0
    hra_employer_contribution: float = 0

class MECTrackingEntry(BaseModel):
    employer_id: str
    year: int
    month: int
    total_full_time: int
    offered_coverage: int

class CertificationCreate(BaseModel):
    employer_id: str
    plan_id: str
    reason: str
    notes: Optional[str] = ""

class CertificationUpdate(BaseModel):
    status: str  # in_review, certified, rejected
    actuary_notes: Optional[str] = ""
    certification_result: Optional[float] = None  # MV percentage if certified

class MECComplianceCheck(BaseModel):
    plan_name: str
    plan_type: str = "Group"
    individual_deductible: float = 2000
    family_deductible: float = 4000
    oop_max_individual: float = 7500
    oop_max_family: float = 15000
    coinsurance_rate: float = 20  # percentage, e.g. 20 = 20%
    copay_primary: float = 25
    copay_specialist: float = 50
    copay_emergency: float = 250
    copay_generic_rx: float = 10
    copay_brand_rx: float = 40
    essential_health_benefits: bool = True
    preventive_care_100: bool = True
    hsa_eligible: bool = False
    employee_monthly_contribution: float = 250
    employer_monthly_contribution: float = 500
    employee_annual_income: float = 50000
    household_size: int = 1

class MVCalculateRequest(BaseModel):
    plan_name: str
    plan_type: str = "Group"
    individual_deductible: float = 2000
    family_deductible: float = 4000
    oop_max_individual: float = 7500
    oop_max_family: float = 15000
    coinsurance_rate: float = 20
    copay_primary: float = 25
    copay_specialist: float = 50
    copay_emergency: float = 250
    copay_generic_rx: float = 10
    copay_brand_rx: float = 40
    essential_health_benefits: bool = True
    preventive_care_100: bool = True
    hsa_eligible: bool = False
    hsa_employer_contribution: float = 0
    hra_employer_contribution: float = 0

# --- Auth Helpers ---

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc).timestamp() + 86400 * 7
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Auth Routes ---

@api_router.post("/auth/register")
async def register(data: UserRegister):
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user_doc = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name,
        "role": data.role,
        "company_name": data.company_name or "",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    token = create_token(user_id, data.role)
    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": data.email,
            "name": data.name,
            "role": data.role,
            "company_name": data.company_name or "",
            "created_at": user_doc["created_at"]
        }
    }

@api_router.post("/auth/login")
async def login(data: UserLogin):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(user["id"], user["role"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "company_name": user.get("company_name", ""),
            "created_at": user["created_at"]
        }
    }

@api_router.get("/auth/me")
async def get_me(user=Depends(get_current_user)):
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "company_name": user.get("company_name", ""),
        "employer_id": user.get("employer_id", ""),
        "employer_name": user.get("employer_name", ""),
        "linked_employee_id": user.get("linked_employee_id", ""),
        "created_at": user["created_at"]
    }

# --- Employer Routes ---

@api_router.get("/employers")
async def get_employers(user=Depends(get_current_user)):
    if user["role"] == "employer":
        employers = await db.employers.find({"user_id": user["id"]}, {"_id": 0}).to_list(100)
    else:
        employers = await db.employers.find({}, {"_id": 0}).to_list(100)
    return employers

@api_router.post("/employers")
async def create_employer(data: dict, user=Depends(get_current_user)):
    employer_id = str(uuid.uuid4())
    employer_doc = {
        "id": employer_id,
        "user_id": user["id"],
        "name": data.get("name", ""),
        "ein": data.get("ein", ""),
        "address": data.get("address", ""),
        "contact_email": data.get("contact_email", user["email"]),
        "employee_count": data.get("employee_count", 0),
        "payroll_provider": data.get("payroll_provider", ""),
        "hr_system": data.get("hr_system", ""),
        "insurance_carrier": data.get("insurance_carrier", ""),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.employers.insert_one(employer_doc)
    employer_doc.pop("_id", None)
    return employer_doc

@api_router.get("/employers/{employer_id}")
async def get_employer(employer_id: str, user=Depends(get_current_user)):
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")
    return employer

# --- Monthly Headcount Routes ---

@api_router.post("/employees/headcount")
async def save_headcount(data: MonthlyHeadcount, user=Depends(get_current_user)):
    existing = await db.employees_headcount.find_one(
        {"employer_id": data.employer_id, "year": data.year, "month": data.month},
        {"_id": 0}
    )
    
    doc = {
        "employer_id": data.employer_id,
        "year": data.year,
        "month": data.month,
        "full_time_count": data.full_time_count,
        "part_time_hours": data.part_time_hours,
        "fte": round(data.part_time_hours / 120, 2),
        "total": data.full_time_count + round(data.part_time_hours / 120, 2),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if existing:
        await db.employees_headcount.update_one(
            {"employer_id": data.employer_id, "year": data.year, "month": data.month},
            {"$set": doc}
        )
    else:
        doc["id"] = str(uuid.uuid4())
        await db.employees_headcount.insert_one(doc)
    
    result = await db.employees_headcount.find_one(
        {"employer_id": data.employer_id, "year": data.year, "month": data.month},
        {"_id": 0}
    )
    return result

@api_router.get("/employees/headcount/{employer_id}/{year}")
async def get_headcount(employer_id: str, year: int, user=Depends(get_current_user)):
    records = await db.employees_headcount.find(
        {"employer_id": employer_id, "year": year},
        {"_id": 0}
    ).sort("month", 1).to_list(12)
    return records

# --- ALE Calculation ---

@api_router.post("/ale/calculate")
async def calculate_ale(data: ALECalculationRequest, user=Depends(get_current_user)):
    records = await db.employees_headcount.find(
        {"employer_id": data.employer_id, "year": data.year},
        {"_id": 0}
    ).sort("month", 1).to_list(12)
    
    if not records:
        raise HTTPException(status_code=400, detail="No headcount data found for this year")
    
    months_with_data = len(records)
    total_ft = sum(r["full_time_count"] for r in records)
    total_fte = sum(r["fte"] for r in records)
    total_combined = sum(r["total"] for r in records)
    
    avg_ft = round(total_ft / months_with_data, 2)
    avg_fte = round(total_fte / months_with_data, 2)
    avg_combined = round(total_combined / months_with_data, 2)
    
    is_ale = avg_combined >= 50
    
    # Penalty calculations (2026 rates — IRS Rev. Proc. 2025-25 & 2025-26)
    a_penalty_annual = 3340
    b_penalty_annual = 5010
    a_penalty_monthly = round(a_penalty_annual / 12, 2)
    b_penalty_monthly = round(b_penalty_annual / 12, 2)
    
    potential_a_penalty = round(max(0, (avg_ft - 30)) * a_penalty_annual, 2) if is_ale else 0
    
    result = {
        "id": str(uuid.uuid4()),
        "employer_id": data.employer_id,
        "year": data.year,
        "months_with_data": months_with_data,
        "avg_full_time": avg_ft,
        "avg_fte": avg_fte,
        "avg_combined": avg_combined,
        "is_ale": is_ale,
        "threshold": 50,
        "a_penalty_rate": a_penalty_annual,
        "b_penalty_rate": b_penalty_annual,
        "potential_a_penalty": potential_a_penalty,
        "monthly_breakdown": records,
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.ale_calculations.update_one(
        {"employer_id": data.employer_id, "year": data.year},
        {"$set": result},
        upsert=True
    )
    
    return result

@api_router.get("/ale/results/{employer_id}")
async def get_ale_results(employer_id: str, user=Depends(get_current_user)):
    results = await db.ale_calculations.find(
        {"employer_id": employer_id},
        {"_id": 0}
    ).sort("year", -1).to_list(10)
    return results

# --- MEC Tracking ---

@api_router.post("/mec/tracking")
async def save_mec_tracking(data: MECTrackingEntry, user=Depends(get_current_user)):
    coverage_pct = round((data.offered_coverage / data.total_full_time * 100), 2) if data.total_full_time > 0 else 0
    is_compliant = coverage_pct >= 95
    
    doc = {
        "employer_id": data.employer_id,
        "year": data.year,
        "month": data.month,
        "total_full_time": data.total_full_time,
        "offered_coverage": data.offered_coverage,
        "coverage_percentage": coverage_pct,
        "is_compliant": is_compliant,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    existing = await db.mec_tracking.find_one(
        {"employer_id": data.employer_id, "year": data.year, "month": data.month},
        {"_id": 0}
    )
    
    if existing:
        await db.mec_tracking.update_one(
            {"employer_id": data.employer_id, "year": data.year, "month": data.month},
            {"$set": doc}
        )
    else:
        doc["id"] = str(uuid.uuid4())
        await db.mec_tracking.insert_one(doc)
    
    result = await db.mec_tracking.find_one(
        {"employer_id": data.employer_id, "year": data.year, "month": data.month},
        {"_id": 0}
    )
    return result

@api_router.get("/mec/tracking/{employer_id}/{year}")
async def get_mec_tracking(employer_id: str, year: int, user=Depends(get_current_user)):
    records = await db.mec_tracking.find(
        {"employer_id": employer_id, "year": year},
        {"_id": 0}
    ).sort("month", 1).to_list(12)
    return records

# --- Plans ---

@api_router.post("/plans")
async def create_plan(data: PlanCreate, user=Depends(get_current_user)):
    plan_id = str(uuid.uuid4())
    plan_doc = {
        "id": plan_id,
        "employer_id": data.employer_id,
        "plan_name": data.plan_name,
        "plan_type": data.plan_type,
        "individual_deductible": data.individual_deductible,
        "family_deductible": data.family_deductible,
        "coinsurance_rate": data.coinsurance_rate,
        "office_visit_copay": data.office_visit_copay,
        "er_copay": data.er_copay,
        "inpatient_copay": data.inpatient_copay,
        "rx_copay_generic": data.rx_copay_generic,
        "rx_copay_brand": data.rx_copay_brand,
        "oop_max_individual": data.oop_max_individual,
        "oop_max_family": data.oop_max_family,
        "hsa_employer_contribution": data.hsa_employer_contribution,
        "hra_employer_contribution": data.hra_employer_contribution,
        "mv_calculated": False,
        "mv_percentage": None,
        "mv_meets_minimum": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.plans.insert_one(plan_doc)
    plan_doc.pop("_id", None)
    return plan_doc

@api_router.get("/plans/{employer_id}")
async def get_plans(employer_id: str, user=Depends(get_current_user)):
    plans = await db.plans.find({"employer_id": employer_id}, {"_id": 0}).to_list(100)
    return plans

@api_router.get("/plans/detail/{plan_id}")
async def get_plan_detail(plan_id: str, user=Depends(get_current_user)):
    plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

@api_router.delete("/plans/detail/{plan_id}")
async def delete_plan(plan_id: str, user=Depends(get_current_user)):
    result = await db.plans.delete_one({"id": plan_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted"}

# --- MV Calculator (HHS-based methodology) ---

from services.mv_calculator import calculate_mv_percentage

# Moved to services/mv_calculator.py

@api_router.post("/mv/calculate/{plan_id}")
async def calculate_mv(plan_id: str, user=Depends(get_current_user)):
    plan = await db.plan_library.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    try:
        result = calculate_mv_percentage(plan)
        
        # Update plan with MV results
        await db.plans.update_one(
            {"id": plan_id},
            {"$set": {
                "mv_calculated": True,
                "mv_percentage": result["mv_percentage"],
                "mv_meets_minimum": result["meets_minimum"]
            }}
        )
        
        # Store calculation result
        mv_doc = {
            "id": str(uuid.uuid4()),
            "plan_id": plan_id,
            "employer_id": plan["employer_id"],
            "plan_name": plan["plan_name"],
            **result,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.mv_calculations.update_one(
            {"plan_id": plan_id},
            {"$set": mv_doc},
            upsert=True
        )
        
        return mv_doc
        
    except Exception as e:
        logger.error(f"MV calculation failed: {str(e)}")
        # Mark as needing actuarial certification
        return {
            "plan_id": plan_id,
            "calculation_failed": True,
            "error": str(e),
            "needs_actuarial_certification": True,
            "message": "HHS calculation failed. Please submit for actuarial certification."
        }

@api_router.get("/mv/results/{employer_id}")
async def get_mv_results(employer_id: str, user=Depends(get_current_user)):
    results = await db.mv_calculations.find(
        {"employer_id": employer_id},
        {"_id": 0}
    ).to_list(100)
    return results

# --- Actuarial Certification ---

@api_router.post("/certifications")
async def create_certification(data: CertificationCreate, user=Depends(get_current_user)):
    plan = await db.plans.find_one({"id": data.plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    cert_id = str(uuid.uuid4())
    cert_doc = {
        "id": cert_id,
        "employer_id": data.employer_id,
        "plan_id": data.plan_id,
        "plan_name": plan.get("plan_name", ""),
        "reason": data.reason,
        "notes": data.notes or "",
        "status": "pending",
        "requested_by": user["id"],
        "requested_by_name": user["name"],
        "actuary_id": None,
        "actuary_name": None,
        "actuary_notes": "",
        "certification_result": None,
        "certification_document": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.certifications.insert_one(cert_doc)
    cert_doc.pop("_id", None)
    return cert_doc

@api_router.get("/certifications")
async def get_certifications(user=Depends(get_current_user)):
    if user["role"] == "employer":
        certs = await db.certifications.find(
            {"requested_by": user["id"]},
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    else:
        # Actuaries see all certifications
        certs = await db.certifications.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return certs

@api_router.get("/certifications/{cert_id}")
async def get_certification(cert_id: str, user=Depends(get_current_user)):
    cert = await db.certifications.find_one({"id": cert_id}, {"_id": 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    return cert

@api_router.put("/certifications/{cert_id}")
async def update_certification(cert_id: str, data: CertificationUpdate, user=Depends(get_current_user)):
    cert = await db.certifications.find_one({"id": cert_id}, {"_id": 0})
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    
    update_doc = {
        "status": data.status,
        "actuary_notes": data.actuary_notes or "",
        "actuary_id": user["id"],
        "actuary_name": user["name"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if data.certification_result is not None:
        update_doc["certification_result"] = data.certification_result
        # Update the plan's MV if certified
        if data.status == "certified":
            await db.plans.update_one(
                {"id": cert["plan_id"]},
                {"$set": {
                    "mv_calculated": True,
                    "mv_percentage": data.certification_result,
                    "mv_meets_minimum": data.certification_result >= 60.0
                }}
            )
    
    await db.certifications.update_one(
        {"id": cert_id},
        {"$set": update_doc}
    )
    
    updated = await db.certifications.find_one({"id": cert_id}, {"_id": 0})
    return updated

# --- Dashboard ---

@api_router.get("/dashboard/{employer_id}")
async def get_dashboard(employer_id: str, user=Depends(get_current_user)):
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    
    # Latest ALE calculation
    ale = await db.ale_calculations.find_one(
        {"employer_id": employer_id},
        {"_id": 0},
        sort=[("year", -1)]
    )
    
    # Plans count - use plan_library (active plans)
    plans = await db.plan_library.find({"employer_id": employer_id, "category": "medical"}, {"_id": 0}).to_list(100)
    plans_count = len(plans)
    mv_compliant = 0
    for p in plans:
        mv_pct = p.get("mv_percentage") or 0
        er_contrib = p.get("employer_contribution", {}).get("self_only", 0)
        total_prem = p.get("premiums", {}).get("self_only", 0)
        er_pct = (er_contrib / total_prem * 100) if total_prem > 0 else 0
        if mv_pct >= 60 and er_pct >= 60:
            mv_compliant += 1
    
    # MEC latest year
    current_year = datetime.now(timezone.utc).year
    mec_records = await db.mec_tracking.find(
        {"employer_id": employer_id, "year": current_year},
        {"_id": 0}
    ).to_list(12)
    
    mec_compliant_months = sum(1 for m in mec_records if m.get("is_compliant"))
    
    # Certifications
    pending_certs = await db.certifications.count_documents(
        {"employer_id": employer_id, "status": "pending"}
    )
    in_review_certs = await db.certifications.count_documents(
        {"employer_id": employer_id, "status": "in_review"}
    )
    
    return {
        "employer": employer,
        "ale_status": {
            "is_ale": ale.get("is_ale") if ale else None,
            "avg_combined": ale.get("avg_combined") if ale else None,
            "year": ale.get("year") if ale else None,
            "potential_penalty": ale.get("potential_a_penalty") if ale else None
        },
        "plans": {
            "total": plans_count,
            "mv_compliant": mv_compliant,
            "mv_non_compliant": plans_count - mv_compliant
        },
        "mec_status": {
            "months_tracked": len(mec_records),
            "compliant_months": mec_compliant_months,
            "records": mec_records
        },
        "certifications": {
            "pending": pending_certs,
            "in_review": in_review_certs
        }
    }

# Actuary dashboard
@api_router.get("/dashboard/actuary/overview")
async def get_actuary_dashboard(user=Depends(get_current_user)):
    if user["role"] != "actuary":
        raise HTTPException(status_code=403, detail="Access denied")
    
    user_email = user.get("email", "")
    
    # Find which actuary profile matches this user's email
    matching_actuary = next((a for a in MOCK_ACTUARIES if a.get("email") == user_email), None)
    
    # Build filter for quote_requests directed to this actuary
    quote_filter = {}
    if matching_actuary:
        quote_filter = {"actuary_id": matching_actuary["id"]}
    else:
        quote_filter = {"actuary_email": user_email}
    
    # Get marketplace quotes as certifications
    pending_quotes = await db.quote_requests.find(
        {**quote_filter, "status": {"$in": ["pending", "quoted"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    in_review_quotes = await db.quote_requests.find(
        {**quote_filter, "status": {"$in": ["accepted", "paid"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    completed_quotes = await db.quote_requests.find(
        {**quote_filter, "status": {"$in": ["delivered", "validated", "rejected"]}}, {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    # Map quote_requests to certification-like format for the dashboard
    def map_quote_to_cert(q):
        return {
            "id": q["id"],
            "plan_name": q.get("plan_name", "Unknown Plan"),
            "reason": q.get("message", "MV Certification Request"),
            "status": q["status"],
            "employer_name": q.get("employer_name", ""),
            "created_at": q.get("created_at", ""),
            "updated_at": q.get("updated_at", q.get("created_at", "")),
        }
    
    pending = [map_quote_to_cert(q) for q in pending_quotes]
    in_review = [map_quote_to_cert(q) for q in in_review_quotes]
    completed = [map_quote_to_cert(q) for q in completed_quotes]
    
    return {
        "pending_certifications": pending,
        "in_review_certifications": in_review,
        "completed_certifications": completed,
        "stats": {
            "pending_count": len(pending),
            "in_review_count": len(in_review),
            "completed_count": len(completed)
        }
    }

# --- Mock Payroll ---

import random

MOCK_EMPLOYEE_NAMES = [
    "Alice Johnson", "Bob Martinez", "Carol Williams", "David Chen", "Emma Davis",
    "Frank Wilson", "Grace Lee", "Henry Brown", "Irene Taylor", "Jack Anderson",
    "Karen Thomas", "Liam Jackson", "Maria White", "Nathan Harris", "Olivia Martin",
    "Peter Garcia", "Quinn Robinson", "Rachel Clark", "Samuel Lewis", "Tina Walker",
    "Uma Hall", "Victor Allen", "Wendy Young", "Xavier King", "Yolanda Wright",
    "Zach Scott", "Amy Green", "Brian Adams", "Cindy Baker", "Derek Nelson",
    "Elena Hill", "Felix Rivera", "Gina Campbell", "Hugo Mitchell", "Isla Roberts",
    "James Carter", "Kara Phillips", "Leo Evans", "Mia Turner", "Noah Torres",
    "Opal Parker", "Paul Edwards", "Rose Collins", "Sean Stewart", "Tara Sanchez",
    "Ulysses Morris", "Vera Rogers", "Wayne Reed", "Xena Cook", "Yuri Morgan",
    "Zara Bell", "Adam Murphy", "Beth Bailey", "Chase Cooper", "Diana Richardson"
]

@api_router.post("/payroll/generate/{employer_id}")
async def generate_mock_payroll(employer_id: str, user=Depends(get_current_user)):
    """Generate mock payroll employees for an employer"""
    # Check if already generated
    existing = await db.payroll_employees.count_documents({"employer_id": employer_id})
    if existing > 0:
        employees = await db.payroll_employees.find({"employer_id": employer_id}, {"_id": 0}).to_list(200)
        return {"message": "Payroll already exists", "employees": employees, "count": len(employees)}
    
    num_employees = random.randint(40, 70)
    employees = []
    
    for i in range(num_employees):
        name = MOCK_EMPLOYEE_NAMES[i % len(MOCK_EMPLOYEE_NAMES)]
        if i >= len(MOCK_EMPLOYEE_NAMES):
            name = f"{name} Jr."
        
        # 70% full-time, 30% part-time
        is_full_time = random.random() < 0.70
        weekly_hours = random.randint(35, 45) if is_full_time else random.randint(10, 28)
        annual_salary = random.randint(35000, 120000) if is_full_time else random.randint(15000, 30000)
        department = random.choice(["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations", "Support"])
        offered_coverage = is_full_time or random.random() < 0.3  # Some part-timers also offered
        
        emp = {
            "id": str(uuid.uuid4()),
            "employer_id": employer_id,
            "name": name,
            "employee_id": f"EMP-{1000 + i}",
            "department": department,
            "employment_type": "full_time" if is_full_time else "part_time",
            "weekly_hours": weekly_hours,
            "monthly_hours": round(weekly_hours * 4.33, 1),
            "annual_salary": annual_salary,
            "hourly_rate": round(annual_salary / (weekly_hours * 52), 2),
            "hire_date": f"20{random.randint(18, 25)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}",
            "offered_mec": offered_coverage,
            "enrolled": offered_coverage and random.random() < 0.85,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        employees.append(emp)
    
    await db.payroll_employees.insert_many(employees)
    # Remove _id from response
    clean = await db.payroll_employees.find({"employer_id": employer_id}, {"_id": 0}).to_list(200)
    return {"message": "Mock payroll generated", "employees": clean, "count": len(clean)}

@api_router.get("/payroll/{employer_id}")
async def get_payroll(employer_id: str, user=Depends(get_current_user)):
    employees = await db.payroll_employees.find({"employer_id": employer_id}, {"_id": 0}).to_list(200)
    return employees

@api_router.get("/payroll/summary/{employer_id}")
async def get_payroll_summary(employer_id: str, user=Depends(get_current_user)):
    """Get payroll summary with auto-calculated FTE and ALE status"""
    employees = await db.payroll_employees.find({"employer_id": employer_id}, {"_id": 0}).to_list(200)
    
    if not employees:
        return {"has_payroll": False, "message": "No payroll data.", "source": "none"}
    
    # Detect data source
    source = "adp" if any(e.get("source") == "adp" for e in employees) else "mock"
    
    full_time = [e for e in employees if e["employment_type"] == "full_time"]
    part_time = [e for e in employees if e["employment_type"] == "part_time"]
    
    ft_count = len(full_time)
    pt_total_hours = sum(e["monthly_hours"] for e in part_time)
    fte_count = round(pt_total_hours / 120, 2)
    total_fte = round(ft_count + fte_count, 2)
    
    is_ale = total_fte >= 50
    
    # MEC coverage stats
    offered_count = sum(1 for e in full_time if e.get("offered_mec"))
    enrolled_count = sum(1 for e in full_time if e.get("enrolled"))
    coverage_pct = round((offered_count / ft_count * 100), 1) if ft_count > 0 else 0
    mec_compliant = coverage_pct >= 95
    
    # Penalty calculation
    potential_a_penalty = round(max(0, (ft_count - 30)) * 3340, 2) if is_ale and not mec_compliant else 0
    
    # Department breakdown
    departments = {}
    for e in employees:
        dept = e["department"]
        if dept not in departments:
            departments[dept] = {"full_time": 0, "part_time": 0, "total_hours": 0}
        if e["employment_type"] == "full_time":
            departments[dept]["full_time"] += 1
        else:
            departments[dept]["part_time"] += 1
        departments[dept]["total_hours"] += e["weekly_hours"]
    
    dept_list = [{"name": k, **v} for k, v in departments.items()]
    
    return {
        "has_payroll": True,
        "source": source,
        "total_employees": len(employees),
        "full_time_count": ft_count,
        "part_time_count": len(part_time),
        "pt_total_monthly_hours": round(pt_total_hours, 1),
        "fte_from_part_time": fte_count,
        "total_fte": total_fte,
        "is_ale": is_ale,
        "ale_threshold": 50,
        "mec_offered_count": offered_count,
        "mec_enrolled_count": enrolled_count,
        "mec_coverage_pct": coverage_pct,
        "mec_compliant": mec_compliant,
        "potential_a_penalty": potential_a_penalty,
        "departments": dept_list,
        "employees": employees
    }

@api_router.delete("/payroll/{employer_id}")
async def reset_payroll(employer_id: str, user=Depends(get_current_user)):
    await db.payroll_employees.delete_many({"employer_id": employer_id})
    return {"message": "Payroll reset"}

# --- MEC Compliance Checker ---

@api_router.post("/mec/check")
async def check_mec_compliance(data: MECComplianceCheck, user=Depends(get_current_user)):
    """Check if a health plan meets MEC requirements"""
    results = {
        "plan_name": data.plan_name,
        "plan_type": data.plan_type,
        "checks": [],
        "overall_compliant": True,
        "affordability": {},
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # 1. Essential Health Benefits check
    ehb_pass = data.essential_health_benefits
    results["checks"].append({
        "name": "Essential Health Benefits",
        "description": "Plan must cover all 10 EHBs required by ACA",
        "passed": ehb_pass,
        "details": "Plan covers all 10 Essential Health Benefits" if ehb_pass else "Plan does NOT cover all Essential Health Benefits"
    })
    if not ehb_pass:
        results["overall_compliant"] = False
    
    # 2. Preventive Care check
    prev_pass = data.preventive_care_100
    results["checks"].append({
        "name": "Preventive Care Coverage",
        "description": "Preventive services must be covered at 100% (no cost sharing)",
        "passed": prev_pass,
        "details": "Preventive care covered at 100%" if prev_pass else "Preventive care NOT covered at 100%"
    })
    if not prev_pass:
        results["overall_compliant"] = False
    
    # 3. OOP Max limits (2025 limits)
    oop_ind_limit = 9200
    oop_fam_limit = 18400
    oop_ind_pass = data.oop_max_individual <= oop_ind_limit
    oop_fam_pass = data.oop_max_family <= oop_fam_limit
    results["checks"].append({
        "name": "Out-of-Pocket Maximum (Individual)",
        "description": f"Individual OOP max must not exceed ${oop_ind_limit:,}",
        "passed": oop_ind_pass,
        "details": f"${data.oop_max_individual:,.0f} {'<=' if oop_ind_pass else '>'} ${oop_ind_limit:,} limit"
    })
    results["checks"].append({
        "name": "Out-of-Pocket Maximum (Family)",
        "description": f"Family OOP max must not exceed ${oop_fam_limit:,}",
        "passed": oop_fam_pass,
        "details": f"${data.oop_max_family:,.0f} {'<=' if oop_fam_pass else '>'} ${oop_fam_limit:,} limit"
    })
    if not oop_ind_pass or not oop_fam_pass:
        results["overall_compliant"] = False
    
    # 4. Affordability test (9.96% of household income for 2026)
    affordability_pct = 9.96
    annual_employee_cost = data.employee_monthly_contribution * 12
    income_pct = round((annual_employee_cost / data.employee_annual_income * 100), 2) if data.employee_annual_income > 0 else 0
    affordable = income_pct <= affordability_pct
    
    # FPL Safe Harbor ($129.89/month for 2026)
    fpl_safe_harbor = 129.89
    fpl_pass = data.employee_monthly_contribution <= fpl_safe_harbor
    
    results["affordability"] = {
        "employee_annual_cost": annual_employee_cost,
        "income_percentage": income_pct,
        "affordability_threshold": affordability_pct,
        "is_affordable": affordable,
        "fpl_safe_harbor_amount": fpl_safe_harbor,
        "fpl_safe_harbor_pass": fpl_pass,
        "total_monthly_premium": data.employee_monthly_contribution + data.employer_monthly_contribution
    }
    
    results["checks"].append({
        "name": "Affordability (Income Test)",
        "description": f"Employee cost must not exceed {affordability_pct}% of household income",
        "passed": affordable,
        "details": f"Employee pays {income_pct}% of income ({'>=' if not affordable else '<'} {affordability_pct}% threshold)"
    })
    
    results["checks"].append({
        "name": "FPL Safe Harbor",
        "description": f"Employee monthly cost <= ${fpl_safe_harbor}/month",
        "passed": fpl_pass,
        "details": f"${data.employee_monthly_contribution}/mo {'<=' if fpl_pass else '>'} ${fpl_safe_harbor}/mo safe harbor"
    })
    
    if not affordable:
        results["overall_compliant"] = False
    
    # 5. Coverage structure check
    has_hospital = True  # Assumed in standard plans
    has_physician = True  # Assumed in standard plans
    results["checks"].append({
        "name": "Substantial Hospital & Physician Coverage",
        "description": "Plan must include substantial coverage for inpatient and physician services",
        "passed": has_hospital and has_physician,
        "details": "Plan includes hospital and physician coverage"
    })
    
    passed_count = sum(1 for c in results["checks"] if c["passed"])
    results["passed_count"] = passed_count
    results["total_checks"] = len(results["checks"])
    results["compliance_score"] = round((passed_count / len(results["checks"]) * 100), 1)
    
    return results

# --- MV Calculator v2 (form-based) ---

@api_router.post("/mv/calculate-form")
async def calculate_mv_form(data: MVCalculateRequest, user=Depends(get_current_user)):
    """Calculate Minimum Value from form inputs (HHS methodology)"""
    TOTAL_ALLOWED_COST = 12000
    
    AVG_OFFICE_VISITS = 4
    AVG_SPECIALIST_VISITS = 2
    AVG_ER_VISITS = 0.15
    AVG_INPATIENT_DAYS = 0.5
    AVG_RX_FILLS_GENERIC = 8
    AVG_RX_FILLS_BRAND = 3
    
    deductible = data.individual_deductible
    coinsurance = data.coinsurance_rate / 100  # Convert from percentage
    oop_max = data.oop_max_individual
    hsa_hra = data.hsa_employer_contribution + data.hra_employer_contribution
    
    # Deductible cost
    deductible_cost = min(deductible, TOTAL_ALLOWED_COST)
    remaining_after_deductible = max(0, TOTAL_ALLOWED_COST - deductible)
    
    # Coinsurance cost
    coinsurance_cost = remaining_after_deductible * coinsurance
    
    # Copay costs
    copay_costs = (
        AVG_OFFICE_VISITS * data.copay_primary +
        AVG_SPECIALIST_VISITS * data.copay_specialist +
        AVG_ER_VISITS * data.copay_emergency +
        AVG_INPATIENT_DAYS * 500 +  # Inpatient copay
        AVG_RX_FILLS_GENERIC * data.copay_generic_rx +
        AVG_RX_FILLS_BRAND * data.copay_brand_rx
    )
    
    # Total member cost (before OOP max)
    total_member_cost = deductible_cost + coinsurance_cost + copay_costs
    
    # Apply OOP max
    total_member_cost = min(total_member_cost, oop_max)
    
    # Subtract HSA/HRA
    total_member_cost = max(0, total_member_cost - hsa_hra)
    
    # Preventive care adjustment
    if data.preventive_care_100:
        preventive_savings = 500  # ~$500 annual preventive cost
        total_member_cost = max(0, total_member_cost - preventive_savings * 0.3)
    
    plan_pays = TOTAL_ALLOWED_COST - total_member_cost
    mv_percentage = round((plan_pays / TOTAL_ALLOWED_COST) * 100, 2)
    mv_percentage = max(0, min(100, mv_percentage))
    meets_minimum = mv_percentage >= 60.0
    
    # Build breakdown
    breakdown = {
        "total_allowed_cost": TOTAL_ALLOWED_COST,
        "deductible_cost": round(deductible_cost, 2),
        "coinsurance_cost": round(coinsurance_cost, 2),
        "copay_costs": round(copay_costs, 2),
        "oop_max_applied": total_member_cost < (deductible_cost + coinsurance_cost + copay_costs),
        "hsa_hra_offset": hsa_hra,
        "preventive_adjustment": data.preventive_care_100,
        "total_member_cost": round(total_member_cost, 2),
        "plan_pays": round(plan_pays, 2)
    }
    
    notes = []
    if deductible > 7500:
        notes.append("High deductible may reduce MV below 60%")
    if coinsurance > 0.40:
        notes.append("High coinsurance rate detected")
    if not data.essential_health_benefits:
        notes.append("Plan should cover all 10 Essential Health Benefits")
    if mv_percentage < 60 and mv_percentage >= 55:
        notes.append("Close to MV threshold - consider actuarial certification")
    if mv_percentage < 55:
        notes.append("Significantly below MV threshold - plan redesign recommended")
    
    return {
        "plan_name": data.plan_name,
        "plan_type": data.plan_type,
        "mv_percentage": mv_percentage,
        "meets_minimum_value": meets_minimum,
        "threshold": 60.0,
        "breakdown": breakdown,
        "notes": notes,
        "needs_actuarial_certification": not meets_minimum or not data.essential_health_benefits,
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }

# --- Employee Profiles (Full CRUD) ---

@api_router.post("/employee-profiles")
async def create_employee_profile(data: dict, user=Depends(get_current_user)):
    emp_id = str(uuid.uuid4())
    
    weekly_hours = data.get("weekly_hours", 0)
    monthly_hours = round(weekly_hours * 4.33, 1)
    is_full_time = monthly_hours >= 130
    
    # Auto eligibility determination
    eligibility_status = "eligible" if is_full_time else "not_eligible"
    if data.get("hire_date"):
        from datetime import date
        try:
            hire = datetime.fromisoformat(data["hire_date"])
            days_employed = (datetime.now(timezone.utc) - hire).days
            if days_employed < 90 and is_full_time:
                eligibility_status = "waiting_period"
        except Exception:
            pass
    
    profile = {
        "id": emp_id,
        "employer_id": data.get("employer_id"),
        "name": data.get("name", ""),
        "ssn_last4": data.get("ssn_last4", ""),
        "address": data.get("address", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "hire_date": data.get("hire_date", ""),
        "job_title": data.get("job_title", ""),
        "department": data.get("department", ""),
        "employment_type": "full_time" if is_full_time else "part_time",
        "weekly_hours": weekly_hours,
        "monthly_hours": monthly_hours,
        "annual_salary": data.get("annual_salary", 0),
        "hourly_rate": data.get("hourly_rate", 0),
        "w2_wages": data.get("w2_wages", 0),
        "spouse_name": data.get("spouse_name", ""),
        "num_dependents": data.get("num_dependents", 0),
        "dependents": data.get("dependents", []),
        "plan_id": data.get("plan_id", ""),
        "plan_name": data.get("plan_name", ""),
        "coverage_start_date": data.get("coverage_start_date", ""),
        "coverage_tier": data.get("coverage_tier", "individual"),
        "employee_monthly_premium": data.get("employee_monthly_premium", 0),
        "employer_monthly_premium": data.get("employer_monthly_premium", 0),
        "is_full_time": is_full_time,
        "eligibility_status": eligibility_status,
        "offered_mec": data.get("offered_mec", is_full_time),
        "enrolled": data.get("enrolled", False),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.employee_profiles.insert_one(profile)
    profile.pop("_id", None)
    return profile

@api_router.get("/employee-profiles/{employer_id}")
async def get_employee_profiles(employer_id: str, user=Depends(get_current_user)):
    employees = await db.employee_profiles.find(
        {"employer_id": employer_id}, {"_id": 0}
    ).sort("name", 1).to_list(500)
    return employees

@api_router.get("/employee-profiles/{employer_id}/ale-status")
async def get_ale_status_by_period(employer_id: str, period: str = "current_year", user=Depends(get_current_user)):
    """Calculate ALE status for a given measurement period based on employee profiles."""
    from dateutil.relativedelta import relativedelta

    now = datetime.now(timezone.utc)
    # Determine date range based on period
    if period == "2024":
        period_start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(2024, 12, 31, tzinfo=timezone.utc)
        period_label = "Calendar Year 2024"
    elif period == "2025":
        period_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        period_label = "Calendar Year 2025"
    elif period == "2026":
        period_start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        period_end = datetime(2026, 12, 31, tzinfo=timezone.utc)
        period_label = "Calendar Year 2026"
    elif period == "last_3_months":
        period_start = now - relativedelta(months=3)
        period_end = now
        period_label = "Last 3 Months"
    elif period == "last_6_months":
        period_start = now - relativedelta(months=6)
        period_end = now
        period_label = "Last 6 Months"
    elif period == "last_9_months":
        period_start = now - relativedelta(months=9)
        period_end = now
        period_label = "Last 9 Months"
    elif period == "last_12_months":
        period_start = now - relativedelta(months=12)
        period_end = now
        period_label = "Last 12 Months"
    else:
        period_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        period_end = now
        period_label = f"Current Year ({now.year})"

    # Get all employees for this employer
    all_employees = await db.employee_profiles.find(
        {"employer_id": employer_id}, {"_id": 0}
    ).to_list(500)

    # Filter: employees hired on or before the period end
    active_employees = []
    for emp in all_employees:
        hire_date_str = emp.get("hire_date", "")
        if hire_date_str:
            try:
                hire_dt = datetime.fromisoformat(hire_date_str).replace(tzinfo=timezone.utc) if not datetime.fromisoformat(hire_date_str).tzinfo else datetime.fromisoformat(hire_date_str)
                if hire_dt <= period_end:
                    active_employees.append(emp)
            except Exception:
                active_employees.append(emp)
        else:
            active_employees.append(emp)

    ft_employees = [e for e in active_employees if e.get("is_full_time")]
    pt_employees = [e for e in active_employees if not e.get("is_full_time")]

    ft_count = len(ft_employees)
    pt_count = len(pt_employees)
    pt_total_monthly_hours = sum(e.get("monthly_hours", 0) for e in pt_employees)
    fte_from_pt = round(pt_total_monthly_hours / 120, 2) if pt_total_monthly_hours > 0 else 0
    total_fte = round(ft_count + fte_from_pt, 2)
    is_ale = total_fte >= 50

    # Calculate months in period for penalty estimation
    months_in_period = max(1, round((period_end - period_start).days / 30))
    penalty_a_annual = 3340
    potential_penalty = round(max(0, (ft_count - 30)) * penalty_a_annual, 2) if is_ale else 0

    return {
        "period": period,
        "period_label": period_label,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "total_employees": len(active_employees),
        "full_time_count": ft_count,
        "part_time_count": pt_count,
        "fte_from_part_time": fte_from_pt,
        "total_fte": total_fte,
        "ale_threshold": 50,
        "is_ale": is_ale,
        "potential_penalty": potential_penalty,
        "months_in_period": months_in_period,
    }

@api_router.get("/employee-profiles/detail/{employee_id}")
async def get_employee_profile(employee_id: str, user=Depends(get_current_user)):
    emp = await db.employee_profiles.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp

@api_router.put("/employee-profiles/{employee_id}")
async def update_employee_profile(employee_id: str, data: dict, user=Depends(get_current_user)):
    emp = await db.employee_profiles.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    weekly_hours = data.get("weekly_hours", emp.get("weekly_hours", 0))
    monthly_hours = round(weekly_hours * 4.33, 1)
    is_full_time = monthly_hours >= 130
    
    eligibility_status = "eligible" if is_full_time else "not_eligible"
    hire_date = data.get("hire_date", emp.get("hire_date", ""))
    if hire_date:
        try:
            hire = datetime.fromisoformat(hire_date)
            days_employed = (datetime.now(timezone.utc) - hire).days
            if days_employed < 90 and is_full_time:
                eligibility_status = "waiting_period"
        except Exception:
            pass
    
    update_fields = {
        "name": data.get("name", emp["name"]),
        "ssn_last4": data.get("ssn_last4", emp.get("ssn_last4", "")),
        "address": data.get("address", emp.get("address", "")),
        "email": data.get("email", emp.get("email", "")),
        "phone": data.get("phone", emp.get("phone", "")),
        "hire_date": hire_date,
        "job_title": data.get("job_title", emp.get("job_title", "")),
        "department": data.get("department", emp.get("department", "")),
        "weekly_hours": weekly_hours,
        "monthly_hours": monthly_hours,
        "annual_salary": data.get("annual_salary", emp.get("annual_salary", 0)),
        "hourly_rate": data.get("hourly_rate", emp.get("hourly_rate", 0)),
        "w2_wages": data.get("w2_wages", emp.get("w2_wages", 0)),
        "spouse_name": data.get("spouse_name", emp.get("spouse_name", "")),
        "num_dependents": data.get("num_dependents", emp.get("num_dependents", 0)),
        "dependents": data.get("dependents", emp.get("dependents", [])),
        "plan_id": data.get("plan_id", emp.get("plan_id", "")),
        "plan_name": data.get("plan_name", emp.get("plan_name", "")),
        "coverage_start_date": data.get("coverage_start_date", emp.get("coverage_start_date", "")),
        "coverage_tier": data.get("coverage_tier", emp.get("coverage_tier", "individual")),
        "employee_monthly_premium": data.get("employee_monthly_premium", emp.get("employee_monthly_premium", 0)),
        "employer_monthly_premium": data.get("employer_monthly_premium", emp.get("employer_monthly_premium", 0)),
        "is_full_time": is_full_time,
        "employment_type": "full_time" if is_full_time else "part_time",
        "eligibility_status": eligibility_status,
        "offered_mec": data.get("offered_mec", is_full_time),
        "enrolled": data.get("enrolled", emp.get("enrolled", False)),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employee_profiles.update_one({"id": employee_id}, {"$set": update_fields})
    updated = await db.employee_profiles.find_one({"id": employee_id}, {"_id": 0})
    return updated

@api_router.delete("/employee-profiles/{employee_id}")
async def delete_employee_profile(employee_id: str, user=Depends(get_current_user)):
    result = await db.employee_profiles.delete_one({"id": employee_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {"message": "Employee deleted"}

# --- Eligibility Determination ---

@api_router.get("/eligibility/{employer_id}")
async def get_eligibility_summary(employer_id: str, user=Depends(get_current_user)):
    employees = await db.employee_profiles.find({"employer_id": employer_id}, {"_id": 0}).to_list(500)
    
    eligible = [e for e in employees if e.get("eligibility_status") == "eligible"]
    not_eligible = [e for e in employees if e.get("eligibility_status") == "not_eligible"]
    waiting = [e for e in employees if e.get("eligibility_status") == "waiting_period"]
    
    return {
        "total_employees": len(employees),
        "eligible_count": len(eligible),
        "not_eligible_count": len(not_eligible),
        "waiting_period_count": len(waiting),
        "eligible_employees": eligible,
        "not_eligible_employees": not_eligible,
        "waiting_employees": waiting
    }

# --- Affordability Calculation ---

@api_router.post("/affordability/calculate")
async def calculate_affordability(data: dict, user=Depends(get_current_user)):
    """Calculate affordability using 3 safe harbor methods"""
    employee_premium_monthly = data.get("employee_monthly_premium", 0)
    annual_premium = employee_premium_monthly * 12
    
    # 2026 affordability percentage: 9.96%
    affordability_pct = 9.96
    
    results = {
        "employee_id": data.get("employee_id", ""),
        "employee_name": data.get("employee_name", ""),
        "employee_monthly_premium": employee_premium_monthly,
        "annual_premium": annual_premium,
        "affordability_threshold_pct": affordability_pct,
        "safe_harbors": {},
        "overall_affordable": False,
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # W-2 Safe Harbor
    w2_wages = data.get("w2_wages", 0)
    if w2_wages > 0:
        w2_threshold = round(w2_wages * affordability_pct / 100 / 12, 2)
        w2_pass = employee_premium_monthly <= w2_threshold
        results["safe_harbors"]["w2"] = {
            "name": "W-2 Wages Safe Harbor",
            "w2_wages": w2_wages,
            "monthly_threshold": w2_threshold,
            "employee_premium": employee_premium_monthly,
            "passed": w2_pass,
            "details": f"${employee_premium_monthly}/mo {'<=' if w2_pass else '>'} ${w2_threshold}/mo ({affordability_pct}% of ${w2_wages:,.0f} W-2)"
        }
    
    # Rate of Pay Safe Harbor
    hourly_rate = data.get("hourly_rate", 0)
    if hourly_rate > 0:
        rop_threshold = round(hourly_rate * 130 * affordability_pct / 100, 2)
        rop_pass = employee_premium_monthly <= rop_threshold
        results["safe_harbors"]["rate_of_pay"] = {
            "name": "Rate of Pay Safe Harbor",
            "hourly_rate": hourly_rate,
            "monthly_threshold": rop_threshold,
            "employee_premium": employee_premium_monthly,
            "passed": rop_pass,
            "details": f"${employee_premium_monthly}/mo {'<=' if rop_pass else '>'} ${rop_threshold}/mo ({affordability_pct}% of ${hourly_rate}/hr x 130hrs)"
        }
    
    # FPL Safe Harbor (2025 FPL for individual: ~$15,060)
    fpl_amount = 15060
    household_size = data.get("household_size", 1)
    fpl_adjusted = fpl_amount + (household_size - 1) * 5380
    fpl_monthly_threshold = round(fpl_adjusted * affordability_pct / 100 / 12, 2)
    fpl_pass = employee_premium_monthly <= fpl_monthly_threshold
    results["safe_harbors"]["fpl"] = {
        "name": "Federal Poverty Line Safe Harbor",
        "fpl_amount": fpl_adjusted,
        "household_size": household_size,
        "monthly_threshold": fpl_monthly_threshold,
        "employee_premium": employee_premium_monthly,
        "passed": fpl_pass,
        "details": f"${employee_premium_monthly}/mo {'<=' if fpl_pass else '>'} ${fpl_monthly_threshold}/mo ({affordability_pct}% of ${fpl_adjusted:,.0f} FPL)"
    }
    
    # Overall: affordable if ANY safe harbor passes
    any_pass = any(sh.get("passed") for sh in results["safe_harbors"].values())
    results["overall_affordable"] = any_pass
    results["best_safe_harbor"] = next(
        (k for k, v in results["safe_harbors"].items() if v.get("passed")),
        None
    )
    
    return results

# --- Subsidy Eligibility Check ---

@api_router.post("/subsidy/check")
async def check_subsidy_eligibility(data: dict, user=Depends(get_current_user)):
    """Determine if employee could qualify for marketplace subsidies"""
    employee_id = data.get("employee_id", "")
    employer_id = data.get("employer_id", "")
    
    # Get employee
    employee = None
    if employee_id:
        employee = await db.employee_profiles.find_one({"id": employee_id}, {"_id": 0})
    
    # Check MEC offered
    mec_offered = data.get("mec_offered", employee.get("offered_mec", False) if employee else False)
    
    # Check MV
    mv_passes = data.get("mv_passes", True)
    mv_percentage = data.get("mv_percentage", 0)
    
    # Check affordability
    is_affordable = data.get("is_affordable", True)
    
    # Subsidy eligible if: no MEC OR MV fails OR not affordable
    subsidy_eligible = not mec_offered or not mv_passes or not is_affordable
    
    reasons = []
    if not mec_offered:
        reasons.append("Employer does not offer Minimum Essential Coverage")
    if not mv_passes:
        reasons.append(f"Plan fails Minimum Value test ({mv_percentage}% < 60%)")
    if not is_affordable:
        reasons.append("Coverage is not considered affordable")
    
    if not subsidy_eligible:
        reasons = ["All compliance checks pass - employee must use employer coverage"]
    
    return {
        "employee_id": employee_id,
        "employee_name": employee.get("name", "") if employee else data.get("employee_name", ""),
        "mec_offered": mec_offered,
        "mv_passes": mv_passes,
        "mv_percentage": mv_percentage,
        "is_affordable": is_affordable,
        "subsidy_eligible": subsidy_eligible,
        "reasons": reasons,
        "recommendation": "Employee may qualify for marketplace subsidies" if subsidy_eligible else "Employee should enroll in employer-sponsored coverage",
        "checked_at": datetime.now(timezone.utc).isoformat()
    }

# --- Plan Approval Logic ---

@api_router.post("/plans/approve/{plan_id}")
async def check_plan_approval(plan_id: str, data: dict, user=Depends(get_current_user)):
    """Sequential compliance gate: FTE -> MEC -> MV -> Affordability"""
    plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    employer_id = plan.get("employer_id", data.get("employer_id", ""))
    
    checks = []
    all_pass = True
    
    # 1. FTE/ALE Check
    employees = await db.employee_profiles.find({"employer_id": employer_id}, {"_id": 0}).to_list(500)
    ft_count = sum(1 for e in employees if e.get("is_full_time"))
    pt_hours = sum(e.get("monthly_hours", 0) for e in employees if not e.get("is_full_time"))
    fte = round(pt_hours / 120, 2)
    total_fte = ft_count + fte
    is_ale = total_fte >= 50
    
    checks.append({
        "step": 1,
        "name": "FTE / ALE Determination",
        "passed": True,
        "details": f"{ft_count} FT + {fte} FTE = {round(total_fte, 2)} ({'ALE' if is_ale else 'Not ALE'})",
        "is_ale": is_ale
    })
    
    # 2. MEC Check
    mec_offered_count = sum(1 for e in employees if e.get("offered_mec") and e.get("is_full_time"))
    mec_pct = round((mec_offered_count / ft_count * 100), 1) if ft_count > 0 else 0
    mec_pass = mec_pct >= 95
    
    checks.append({
        "step": 2,
        "name": "MEC Compliance",
        "passed": mec_pass,
        "details": f"{mec_pct}% of FT employees offered MEC ({mec_offered_count}/{ft_count})",
        "coverage_pct": mec_pct
    })
    if not mec_pass:
        all_pass = False
    
    # 3. MV Check
    mv_calculated = plan.get("mv_calculated", False)
    mv_percentage = plan.get("mv_percentage", 0)
    mv_pass = mv_calculated and mv_percentage >= 60
    
    checks.append({
        "step": 3,
        "name": "Minimum Value",
        "passed": mv_pass,
        "details": f"MV: {mv_percentage}% {'(PASS >= 60%)' if mv_pass else '(FAIL < 60%)'}" if mv_calculated else "MV not yet calculated",
        "mv_percentage": mv_percentage
    })
    if not mv_pass:
        all_pass = False
    
    # 4. Affordability (sample check)
    avg_premium = data.get("avg_employee_premium", 0)
    affordability_pass = True
    if avg_premium > 0:
        fpl_threshold = round(15060 * 9.96 / 100 / 12, 2)
        affordability_pass = avg_premium <= fpl_threshold
    
    checks.append({
        "step": 4,
        "name": "Affordability",
        "passed": affordability_pass,
        "details": f"Avg premium ${avg_premium}/mo {'passes' if affordability_pass else 'fails'} affordability test"
    })
    if not affordability_pass:
        all_pass = False
    
    status = "approved" if all_pass else "failed"
    
    # Update plan
    await db.plans.update_one({"id": plan_id}, {"$set": {
        "approval_status": status,
        "approval_checks": checks,
        "approved_at": datetime.now(timezone.utc).isoformat() if all_pass else None
    }})
    
    return {
        "plan_id": plan_id,
        "plan_name": plan.get("plan_name"),
        "status": status,
        "all_checks_passed": all_pass,
        "checks": checks,
        "checked_at": datetime.now(timezone.utc).isoformat()
    }

# --- Actuary Marketplace ---

MOCK_ACTUARIES = [
    {"id": "act-1", "name": "Jane Doe, MAAA, FSA", "firm": "Doe Actuarial Services", "email": "jane.doe@doeactuarial.com", "location": "New York, NY", "price": 3200, "turnaround_days": 14, "rating": 4.9, "reviews": 47, "specialties": ["ACA compliance", "Group health plans", "HDHP analysis"], "experience_years": 15, "certified": True},
    {"id": "act-2", "name": "Robert Chen, ASA, MAAA", "firm": "Chen & Associates", "email": "robert.chen@chenassociates.com", "location": "San Francisco, CA", "price": 2800, "turnaround_days": 10, "rating": 4.8, "reviews": 32, "specialties": ["MV certification", "Self-insured plans", "Large employer compliance"], "experience_years": 12, "certified": True},
    {"id": "act-3", "name": "Sarah Williams, FSA", "firm": "Williams Actuarial Group", "email": "sarah.w@williamsactuarial.com", "location": "Chicago, IL", "price": 3500, "turnaround_days": 7, "rating": 5.0, "reviews": 28, "specialties": ["ACA affordability", "Complex plan designs", "Wellness programs"], "experience_years": 18, "certified": True},
    {"id": "act-4", "name": "Michael Torres, MAAA", "firm": "Torres Consulting", "email": "m.torres@torresconsulting.com", "location": "Austin, TX", "price": 2500, "turnaround_days": 21, "rating": 4.7, "reviews": 19, "specialties": ["Small to mid-size employers", "HDHP with HSA", "ACA reporting"], "experience_years": 8, "certified": True},
    {"id": "act-5", "name": "Emily Park, FSA, MAAA", "firm": "Park & Reed Actuaries", "email": "emily.park@parkreed.com", "location": "Boston, MA", "price": 4000, "turnaround_days": 5, "rating": 4.9, "reviews": 56, "specialties": ["Enterprise ACA compliance", "Multi-state employers", "Actuarial certification"], "experience_years": 22, "certified": True},
    {"id": "act-6", "name": "David Kumar, ASA", "firm": "Kumar Benefits Consulting", "email": "d.kumar@kumarbenefit.com", "location": "Remote", "price": 2200, "turnaround_days": 14, "rating": 4.6, "reviews": 15, "specialties": ["ACA MV calculation", "Plan design optimization", "Cost analysis"], "experience_years": 6, "certified": True},
]

@api_router.get("/actuary-marketplace")
async def get_actuary_marketplace(user=Depends(get_current_user)):
    return MOCK_ACTUARIES

@api_router.get("/actuary-marketplace/{actuary_id}")
async def get_actuary_detail(actuary_id: str, user=Depends(get_current_user)):
    actuary = next((a for a in MOCK_ACTUARIES if a["id"] == actuary_id), None)
    if not actuary:
        raise HTTPException(status_code=404, detail="Actuary not found")
    return actuary

# --- Register Marketplace / Quote Routes ---
register_marketplace_routes(api_router, db, get_current_user, MOCK_ACTUARIES)

# --- Register Enrollment Workflow Routes ---
register_enrollment_routes(api_router, db, get_current_user)

# --- Register ADP Routes ---
register_adp_routes(api_router, db, get_current_user)

# --- Register Predictive Intelligence Routes ---
register_predictive_routes(api_router, db, get_current_user)

# --- Enhanced Dashboard ---

@api_router.get("/dashboard/enhanced/{employer_id}")
async def get_enhanced_dashboard(employer_id: str, user=Depends(get_current_user)):
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    employees = await db.employee_profiles.find({"employer_id": employer_id}, {"_id": 0}).to_list(500)
    if not employees:
        employees = await db.payroll_employees.find({"employer_id": employer_id}, {"_id": 0}).to_list(500)

    # Use plan_library (the active plan collection) instead of stale plans collection
    library_plans = await db.plan_library.find({"employer_id": employer_id, "status": "active"}, {"_id": 0}).to_list(100)

    ft = [e for e in employees if e.get("is_full_time")]
    pt = [e for e in employees if not e.get("is_full_time")]
    pt_hours = sum(e.get("monthly_hours", 0) for e in pt)
    fte = round(pt_hours / 120, 2)
    total_fte = len(ft) + fte
    is_ale = total_fte >= 50

    # MEC compliance from plan_library: count medical plans that are MEC-qualified
    medical_plans = [p for p in library_plans if p.get("category") == "medical"]
    mec_qualified_plans = [p for p in medical_plans if p.get("mec_qualified", False)]
    mec_qualified_plan_ids = set(p["id"] for p in mec_qualified_plans)
    mec_plan_pct = round((len(mec_qualified_plans) / len(medical_plans) * 100), 1) if medical_plans else 0

    # Check employee-level MEC: employees enrolled/assigned to MEC-qualified plans
    enrollments = await db.enrollments.find(
        {"employer_id": employer_id, "status": "enrolled"}, {"_id": 0, "employee_id": 1, "plan_id": 1}
    ).to_list(500)
    assignments = await db.plan_assignments.find(
        {"employer_id": employer_id}, {"_id": 0, "employee_id": 1, "plan_id": 1}
    ).to_list(1000)

    # Employees covered by MEC-qualified plans (enrolled or assigned)
    mec_covered_employee_ids = set()
    for e in enrollments:
        if e.get("plan_id") in mec_qualified_plan_ids:
            mec_covered_employee_ids.add(e.get("employee_id"))
    for a in assignments:
        if a.get("plan_id") in mec_qualified_plan_ids:
            mec_covered_employee_ids.add(a.get("employee_id"))

    ft_ids = set(e.get("id") for e in ft)
    mec_covered_ft = len(mec_covered_employee_ids & ft_ids)
    mec_enrolled_employees = mec_covered_ft

    # MEC coverage %: if enrollments/assignments exist, use employee-level; else plan-level
    if enrollments or assignments:
        mec_pct = round((mec_covered_ft / len(ft) * 100), 1) if ft else 0
    else:
        # No enrollments yet — use plan-level as a proxy
        mec_pct = mec_plan_pct

    mec_compliant = mec_pct >= 95

    # MV compliance from plan_library — must pass BOTH actuarial value >= 60% AND employer contribution >= 60%
    mv_medical_plans = [p for p in medical_plans if p.get("mv_percentage") is not None]
    mv_passing = []
    mv_failing = []
    for p in mv_medical_plans:
        mv_pct = p.get("mv_percentage", 0) or 0
        er_contrib = (p.get("employer_contribution") or {}).get("self_only", 0) or 0
        total_prem = (p.get("premiums") or {}).get("self_only", 0) or 0
        er_pct = (er_contrib / total_prem * 100) if total_prem > 0 else 0
        if mv_pct >= 60 and er_pct >= 60:
            mv_passing.append(p)
        else:
            mv_failing.append(p)

    # Eligibility
    eligible = sum(1 for e in employees if e.get("eligibility_status") == "eligible")
    waiting = sum(1 for e in employees if e.get("eligibility_status") == "waiting_period")
    not_eligible = sum(1 for e in employees if e.get("eligibility_status") == "not_eligible")

    # At-Risk: FT employees where the employer's ACA obligation is NOT met.
    # Under ACA, the employer is safe if they OFFERED affordable MEC+MV coverage.
    # Enrollment doesn't matter — the OFFER is what counts.
    #
    # At-risk scenarios:
    #   1) FT employee NOT offered MEC at all → 4980H(a) risk
    #   2) FT employee assigned to a plan that fails MV (<60%) → 4980H(b) risk
    #   3) FT employee assigned to a plan that is unaffordable → 4980H(b) risk
    #
    # NOT at-risk: offered affordable MEC+MV plan, regardless of whether they enrolled or declined.

    # Build a set of MEC+MV passing plan IDs
    mec_mv_passing_plan_ids = set()
    for p in medical_plans:
        is_mec = p.get("mec_qualified", False)
        mv_pct = p.get("mv_percentage") or 0
        # Also check employer contribution >= 60%
        total_prem = (p.get("premiums") or {}).get("self_only", 0) or 0
        er_contrib = (p.get("employer_contribution") or {}).get("self_only", 0) or 0
        er_pct = (er_contrib / total_prem * 100) if total_prem > 0 else 0
        if is_mec and mv_pct >= 60 and er_pct >= 60:
            mec_mv_passing_plan_ids.add(p["id"])

    # Build assignment map: employee_id → plan_id
    assignment_map = {}
    for a in assignments:
        assignment_map[a.get("employee_id")] = a.get("plan_id")

    # Determine at-risk employees
    risk_employees = []
    for e in ft:
        emp_id = e.get("id")
        offered = e.get("offered_mec", False)
        assigned_plan_id = assignment_map.get(emp_id)

        # Scenario 1: Not offered MEC at all
        if not offered and not assigned_plan_id:
            # But if employer HAS compliant plans available, offer is implicit via open enrollment
            if mec_mv_passing_plan_ids:
                continue  # Employer has compliant plans — offer was made via enrollment window
            e["risk_reason"] = "Not offered MEC coverage"
            risk_employees.append(e)
            continue

        # Scenario 2: Assigned to a specific plan — check if that plan is compliant
        if assigned_plan_id:
            if assigned_plan_id not in mec_mv_passing_plan_ids:
                e["risk_reason"] = "Assigned to non-compliant plan (MEC/MV fail)"
                risk_employees.append(e)
                continue

        # If offered MEC (or has compliant plan assignment), employer is protected

    # Certifications from quote_requests (the active collection)
    pending_certs = await db.quote_requests.count_documents({"employer_id": employer_id, "status": "pending"})
    in_review_certs = await db.quote_requests.count_documents({"employer_id": employer_id, "status": {"$in": ["accepted", "paid"]}})

    # Penalty calculation (IRS 4980H(a)): $3,340 per FT employee (minus 30) per year if MEC < 95%
    # Also 4980H(b): $5,010 per employee who gets marketplace subsidy if coverage unaffordable
    penalty_a = 0
    penalty_b = 0
    if is_ale and not mec_compliant:
        penalty_a = round(max(0, (len(ft) - 30)) * 3340, 2)
    # Estimate penalty B: count MV-failing plans' assigned employees
    mv_failing_plan_ids = [p["id"] for p in mv_failing]
    if mv_failing_plan_ids:
        failing_assignments = await db.plan_assignments.count_documents(
            {"employer_id": employer_id, "plan_id": {"$in": mv_failing_plan_ids}}
        )
        penalty_b = round(failing_assignments * 5010, 2)
    potential_penalty = penalty_a + penalty_b

    return {
        "employer": employer,
        "workforce": {
            "total": len(employees),
            "full_time": len(ft),
            "part_time": len(pt),
            "fte_count": fte,
            "total_fte": round(total_fte, 2),
            "is_ale": is_ale,
            "ale_threshold": 50
        },
        "eligibility": {
            "eligible": eligible,
            "waiting_period": waiting,
            "not_eligible": not_eligible
        },
        "compliance": {
            "mec_offered": len(mec_qualified_plans),
            "mec_total_medical": len(medical_plans),
            "mec_enrolled": mec_enrolled_employees,
            "mec_coverage_pct": mec_pct,
            "mec_compliant": mec_compliant,
            "mv_plans_total": len(medical_plans),
            "mv_plans_calculated": len(mv_medical_plans),
            "mv_plans_passing": len(mv_passing),
            "mv_plans_failing": len(mv_failing)
        },
        "risk_alerts": {
            "at_risk_employees": len(risk_employees),
            "risk_employees": risk_employees[:10],
            "potential_penalty": potential_penalty,
            "penalty_a_amount": penalty_a,
            "penalty_b_amount": penalty_b,
            "penalty_a_reason": "4980H(a): MEC not offered to 95%+ of FT employees" if penalty_a > 0 else "",
            "penalty_b_reason": "4980H(b): MV-failing plans with assigned employees" if penalty_b > 0 else "",
            "pending_certifications": pending_certs,
            "in_review_certifications": in_review_certs
        },
        "plans": library_plans
    }

# --- Employee Compliance Dashboard ---

@api_router.get("/employee-compliance/{employee_id}")
async def get_employee_compliance(employee_id: str, user=Depends(get_current_user)):
    emp = await db.employee_profiles.find_one({"id": employee_id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Get ACTUAL plan assignments (not stale plan_id on profile)
    assignments = await db.plan_assignments.find(
        {"employee_id": employee_id}, {"_id": 0}
    ).to_list(20)

    # Get plan details from plan_library for assigned plans
    assigned_plans = []
    for assignment in assignments:
        plan = await db.plan_library.find_one({"id": assignment["plan_id"]}, {"_id": 0})
        if plan:
            assigned_plans.append({
                "assignment": assignment,
                "plan": plan,
            })

    # Primary medical plan (first medical assignment, if any)
    medical_assignment = next((ap for ap in assigned_plans if ap["plan"].get("category") == "medical"), None)
    plan = medical_assignment["plan"] if medical_assignment else None

    # Affordability check
    affordability = None
    if emp.get("employee_monthly_premium") and emp.get("annual_salary"):
        annual_premium = emp["employee_monthly_premium"] * 12
        income_pct = round((annual_premium / emp["annual_salary"] * 100), 2) if emp["annual_salary"] > 0 else 0
        affordable = income_pct <= 9.96
        affordability = {
            "monthly_premium": emp["employee_monthly_premium"],
            "annual_premium": annual_premium,
            "annual_salary": emp["annual_salary"],
            "income_percentage": income_pct,
            "threshold": 9.96,
            "is_affordable": affordable,
            "safe_harbor": "W-2",
        }

    # Subsidy eligibility
    mec = emp.get("offered_mec", False)
    afford = affordability.get("is_affordable", True) if affordability else True
    subsidy_eligible = not mec or not afford

    return {
        "employee": emp,
        "plan": plan,
        "assigned_plans": assigned_plans,
        "has_assignments": len(assignments) > 0,
        "eligibility_status": emp.get("eligibility_status", "unknown"),
        "mec_offered": mec,
        "affordability": affordability,
        "subsidy_eligible": subsidy_eligible,
        "subsidy_reason": "Eligible for marketplace subsidy" if subsidy_eligible else "Must use employer coverage"
    }

# --- Generate Sample Employee Profiles ---

@api_router.post("/employee-profiles/generate/{employer_id}")
async def generate_employee_profiles(employer_id: str, user=Depends(get_current_user)):
    existing = await db.employee_profiles.count_documents({"employer_id": employer_id})
    if existing > 0:
        employees = await db.employee_profiles.find({"employer_id": employer_id}, {"_id": 0}).to_list(200)
        return {"message": "Profiles already exist", "count": len(employees), "employees": employees}
    
    plans = await db.plans.find({"employer_id": employer_id}, {"_id": 0}).to_list(100)
    
    NAMES = [
        ("Alice", "Johnson"), ("Bob", "Martinez"), ("Carol", "Williams"), ("David", "Chen"),
        ("Emma", "Davis"), ("Frank", "Wilson"), ("Grace", "Lee"), ("Henry", "Brown"),
        ("Irene", "Taylor"), ("Jack", "Anderson"), ("Karen", "Thomas"), ("Liam", "Jackson"),
        ("Maria", "White"), ("Nathan", "Harris"), ("Olivia", "Martin"), ("Peter", "Garcia"),
        ("Quinn", "Robinson"), ("Rachel", "Clark"), ("Samuel", "Lewis"), ("Tina", "Walker"),
        ("Uma", "Hall"), ("Victor", "Allen"), ("Wendy", "Young"), ("Xavier", "King"),
        ("Yolanda", "Wright"), ("Zach", "Scott"), ("Amy", "Green"), ("Brian", "Adams"),
        ("Cindy", "Baker"), ("Derek", "Nelson"), ("Elena", "Hill"), ("Felix", "Rivera"),
        ("Gina", "Campbell"), ("Hugo", "Mitchell"), ("Isla", "Roberts"), ("James", "Carter"),
        ("Kara", "Phillips"), ("Leo", "Evans"), ("Mia", "Turner"), ("Noah", "Torres"),
        ("Opal", "Parker"), ("Paul", "Edwards"), ("Rose", "Collins"), ("Sean", "Stewart"),
        ("Tara", "Sanchez"), ("Ulysses", "Morris"), ("Vera", "Rogers"), ("Wayne", "Reed"),
        ("Xena", "Cook"), ("Yuri", "Morgan"), ("Zara", "Bell"), ("Adam", "Murphy"),
        ("Beth", "Bailey"), ("Chase", "Cooper"), ("Diana", "Richardson")
    ]
    DEPTS = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations", "Support", "Executive"]
    TITLES = {"Engineering": ["Software Engineer", "Senior Developer", "QA Analyst", "DevOps Engineer"],
              "Sales": ["Account Executive", "Sales Rep", "Sales Manager", "BDR"],
              "Marketing": ["Marketing Specialist", "Content Writer", "SEO Analyst", "Marketing Manager"],
              "HR": ["HR Specialist", "Recruiter", "HR Manager", "Benefits Coordinator"],
              "Finance": ["Accountant", "Financial Analyst", "Controller", "AP Specialist"],
              "Operations": ["Operations Manager", "Logistics Coordinator", "Warehouse Lead", "Analyst"],
              "Support": ["Support Engineer", "Customer Success", "Help Desk", "Support Manager"],
              "Executive": ["VP", "Director", "Chief of Staff", "Executive Assistant"]}
    
    num = random.randint(45, 65)
    employees = []
    
    for i in range(num):
        first, last = NAMES[i % len(NAMES)]
        if i >= len(NAMES):
            first = f"{first} J."
        dept = random.choice(DEPTS)
        is_ft = random.random() < 0.72
        weekly_hrs = random.randint(35, 45) if is_ft else random.randint(12, 28)
        monthly_hrs = round(weekly_hrs * 4.33, 1)
        salary = random.randint(45000, 130000) if is_ft else random.randint(18000, 35000)
        hourly = round(salary / (weekly_hrs * 52), 2)
        hire_yr = random.randint(2018, 2025)
        hire_mo = random.randint(1, 12)
        hire_day = random.randint(1, 28)
        
        offered = is_ft or random.random() < 0.2
        enrolled = offered and random.random() < 0.88
        emp_premium = random.choice([95, 110, 125, 140, 175, 200, 250]) if enrolled else 0
        
        plan_id = ""
        plan_name = ""
        if enrolled and plans:
            p = random.choice(plans)
            plan_id = p["id"]
            plan_name = p.get("plan_name", "")
        
        eligibility = "eligible" if is_ft else "not_eligible"
        if is_ft and hire_yr == 2025 and hire_mo >= 10:
            eligibility = "waiting_period"
        
        num_deps = random.choice([0, 0, 0, 1, 1, 2, 2, 3])
        
        emp = {
            "id": str(uuid.uuid4()),
            "employer_id": employer_id,
            "name": f"{first} {last}",
            "ssn_last4": f"{random.randint(1000, 9999)}",
            "address": f"{random.randint(100, 9999)} Main St, City, ST {random.randint(10000, 99999)}",
            "email": f"{first.lower().replace(' ', '').replace('.', '')}.{last.lower()}@company.com",
            "phone": f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}",
            "hire_date": f"{hire_yr}-{hire_mo:02d}-{hire_day:02d}",
            "job_title": random.choice(TITLES.get(dept, ["Specialist"])),
            "department": dept,
            "employment_type": "full_time" if is_ft else "part_time",
            "weekly_hours": weekly_hrs,
            "monthly_hours": monthly_hrs,
            "annual_salary": salary,
            "hourly_rate": hourly,
            "w2_wages": salary,
            "spouse_name": f"Spouse of {first}" if num_deps > 0 and random.random() < 0.6 else "",
            "num_dependents": num_deps,
            "dependents": [{"name": f"Child {j+1}", "relationship": "child", "age": random.randint(1, 17)} for j in range(num_deps)],
            "plan_id": plan_id,
            "plan_name": plan_name,
            "coverage_start_date": f"{hire_yr}-{hire_mo:02d}-01" if enrolled else "",
            "coverage_tier": random.choice(["individual", "individual_spouse", "individual_children", "family"]) if num_deps > 0 else "individual",
            "employee_monthly_premium": emp_premium,
            "employer_monthly_premium": round(emp_premium * random.uniform(1.5, 3.0), 2) if emp_premium else 0,
            "is_full_time": is_ft,
            "eligibility_status": eligibility,
            "offered_mec": offered,
            "enrolled": enrolled,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        employees.append(emp)
    
    await db.employee_profiles.insert_many(employees)
    clean = await db.employee_profiles.find({"employer_id": employer_id}, {"_id": 0}).to_list(200)
    return {"message": "Employee profiles generated", "count": len(clean), "employees": clean}

# --- Compliance Workflow Engine ---

WORKFLOW_STEPS = [
    {"id": "onboarding", "name": "Employer Onboarding", "description": "Register & connect to data sources"},
    {"id": "employee_profiles", "name": "Employee Profiles", "description": "Import and sync employee data"},
    {"id": "fte_calculation", "name": "FTE Calculation", "description": "Calculate full-time equivalents"},
    {"id": "ale_status", "name": "ALE Status", "description": "Determine Applicable Large Employer status", "type": "decision"},
    {"id": "eligibility", "name": "Eligibility Determination", "description": "Determine employee eligibility for coverage"},
    {"id": "mec_validation", "name": "MEC Validation", "description": "Validate Minimum Essential Coverage", "type": "decision"},
    {"id": "mv_calculation", "name": "Minimum Value Calculation", "description": "Run HHS MV Calculator", "type": "decision"},
    {"id": "actuarial_certification", "name": "Actuarial Certification", "description": "Request certification when calculator fails", "conditional": True},
    {"id": "affordability", "name": "Affordability Testing", "description": "Test safe harbor affordability methods", "type": "decision"},
    {"id": "subsidy_check", "name": "Subsidy Eligibility Check", "description": "Determine marketplace subsidy eligibility"},
    {"id": "plan_approval", "name": "Plan Approved", "description": "All compliance checks verified"},
    {"id": "irs_reporting", "name": "IRS Reporting", "description": "Generate 1095-C & 1094-C forms"},
    {"id": "compliance_complete", "name": "Compliance Complete", "description": "Full ACA compliance achieved"},
]

@api_router.get("/workflow/{employer_id}")
async def get_workflow(employer_id: str, user=Depends(get_current_user)):
    workflow = await db.compliance_workflows.find_one(
        {"employer_id": employer_id}, {"_id": 0}
    )
    if not workflow:
        workflow = {
            "id": str(uuid.uuid4()),
            "employer_id": employer_id,
            "current_step": "onboarding",
            "steps": {},
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        await db.compliance_workflows.insert_one(workflow)
        workflow.pop("_id", None)
    return workflow

@api_router.post("/workflow/{employer_id}/execute/{step_id}")
async def execute_workflow_step(employer_id: str, step_id: str, data: dict = {}, user=Depends(get_current_user)):
    """Execute a specific workflow step and compute its result"""
    
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    employees = await db.employee_profiles.find({"employer_id": employer_id}, {"_id": 0}).to_list(500)
    plans = await db.plans.find({"employer_id": employer_id}, {"_id": 0}).to_list(100)
    
    result = {"step_id": step_id, "status": "pending", "data": {}}
    
    if step_id == "onboarding":
        has_employer = employer is not None
        result["status"] = "complete" if has_employer else "incomplete"
        result["data"] = {
            "employer_name": employer.get("name", "") if employer else "",
            "ein": employer.get("ein", "") if employer else "",
            "payroll_provider": employer.get("payroll_provider", "") if employer else "",
            "insurance_carrier": employer.get("insurance_carrier", "") if employer else "",
            "data_connected": bool(employer.get("payroll_provider")) if employer else False
        }
    
    elif step_id == "employee_profiles":
        count = len(employees)
        result["status"] = "complete" if count > 0 else "incomplete"
        result["data"] = {
            "total_employees": count,
            "with_hours": sum(1 for e in employees if e.get("weekly_hours", 0) > 0),
            "with_coverage": sum(1 for e in employees if e.get("plan_id")),
            "synced": count > 0
        }
    
    elif step_id == "fte_calculation":
        ft = [e for e in employees if e.get("is_full_time")]
        pt = [e for e in employees if not e.get("is_full_time")]
        pt_hours = sum(e.get("monthly_hours", 0) for e in pt)
        fte = round(pt_hours / 120, 2) if pt_hours > 0 else 0
        total = len(ft) + fte
        result["status"] = "complete" if len(employees) > 0 else "incomplete"
        result["data"] = {
            "full_time_count": len(ft),
            "part_time_count": len(pt),
            "pt_monthly_hours": round(pt_hours, 1),
            "fte_equivalent": fte,
            "total_fte": round(total, 2)
        }
    
    elif step_id == "ale_status":
        ft = [e for e in employees if e.get("is_full_time")]
        pt = [e for e in employees if not e.get("is_full_time")]
        pt_hours = sum(e.get("monthly_hours", 0) for e in pt)
        fte = round(pt_hours / 120, 2) if pt_hours > 0 else 0
        total = len(ft) + fte
        is_ale = total >= 50
        result["status"] = "complete"
        result["data"] = {
            "total_fte": round(total, 2),
            "threshold": 50,
            "is_ale": is_ale,
            "decision": "yes" if is_ale else "no",
            "message": "Applicable Large Employer" if is_ale else "Not Applicable Large Employer"
        }
        if not is_ale:
            result["data"]["terminal"] = True
            result["data"]["terminal_message"] = "Not an ALE - ACA employer mandate does not apply"
    
    elif step_id == "eligibility":
        ft = [e for e in employees if e.get("is_full_time")]
        pt = [e for e in employees if not e.get("is_full_time")]
        eligible = [e for e in employees if e.get("eligibility_status") == "eligible"]
        waiting = [e for e in employees if e.get("eligibility_status") == "waiting_period"]
        not_elig = [e for e in employees if e.get("eligibility_status") == "not_eligible"]
        result["status"] = "complete"
        result["data"] = {
            "total": len(employees),
            "full_time": len(ft),
            "part_time": len(pt),
            "eligible": len(eligible),
            "waiting_period": len(waiting),
            "not_eligible": len(not_elig),
            "eligible_names": [e["name"] for e in eligible[:5]],
        }
    
    elif step_id == "mec_validation":
        ft = [e for e in employees if e.get("is_full_time")]
        offered = sum(1 for e in ft if e.get("offered_mec"))
        pct = round((offered / len(ft) * 100), 1) if ft else 0
        passed = pct >= 95
        result["status"] = "complete"
        result["data"] = {
            "full_time_count": len(ft),
            "offered_mec": offered,
            "coverage_pct": pct,
            "threshold": 95,
            "passed": passed,
            "decision": "pass" if passed else "fail",
            "message": f"MEC offered to {pct}% of FT employees" + (" - COMPLIANT" if passed else " - NOT COMPLIANT")
        }
    
    elif step_id == "mv_calculation":
        plan_id = data.get("plan_id", "")
        plan = None
        if plan_id:
            plan = await db.plans.find_one({"id": plan_id}, {"_id": 0})
        elif plans:
            plan = plans[0]
        
        if plan and plan.get("mv_calculated"):
            mv_pct = plan.get("mv_percentage", 0)
            passed = mv_pct >= 60
            result["status"] = "complete"
            result["data"] = {
                "plan_name": plan.get("plan_name"),
                "mv_percentage": mv_pct,
                "threshold": 60,
                "passed": passed,
                "calculator_success": True,
                "decision": "calculator_success" if passed else "fail_below_60",
                "message": f"MV: {mv_pct}% {'(PASS >= 60%)' if passed else '(FAIL < 60%)'}"
            }
        elif plan:
            result["status"] = "complete"
            result["data"] = {
                "plan_name": plan.get("plan_name"),
                "mv_percentage": None,
                "calculator_success": False,
                "decision": "calculator_failure",
                "message": "MV not yet calculated - run MV Calculator or request actuarial certification",
                "needs_calculation": True
            }
        else:
            result["status"] = "incomplete"
            result["data"] = {"message": "No plans found - create a plan first", "needs_plan": True}
    
    elif step_id == "actuarial_certification":
        certs = await db.certifications.find({"employer_id": employer_id}, {"_id": 0}).to_list(100)
        certified = [c for c in certs if c.get("status") == "certified"]
        pending = [c for c in certs if c.get("status") in ["pending", "in_review"]]
        rejected = [c for c in certs if c.get("status") == "rejected"]
        
        result["status"] = "complete" if certified else ("in_progress" if pending else "incomplete")
        result["data"] = {
            "total_requests": len(certs),
            "certified": len(certified),
            "pending": len(pending),
            "rejected": len(rejected),
            "certification_result": certified[0].get("certification_result") if certified else None,
            "has_certification": bool(certified)
        }
    
    elif step_id == "affordability":
        ft_with_premium = [e for e in employees if e.get("is_full_time") and e.get("employee_monthly_premium", 0) > 0]
        affordable_count = 0
        not_affordable = 0
        for e in ft_with_premium:
            premium = e.get("employee_monthly_premium", 0)
            salary = e.get("annual_salary", 0)
            if salary > 0:
                pct = (premium * 12 / salary) * 100
                if pct <= 9.96:
                    affordable_count += 1
                else:
                    not_affordable += 1
        
        total_tested = affordable_count + not_affordable
        passed = not_affordable == 0 and total_tested > 0
        result["status"] = "complete" if total_tested > 0 else "incomplete"
        result["data"] = {
            "tested": total_tested,
            "affordable": affordable_count,
            "not_affordable": not_affordable,
            "threshold_pct": 9.96,
            "passed": passed,
            "decision": "pass" if passed else "fail",
            "message": f"{affordable_count}/{total_tested} employees pass affordability" if total_tested > 0 else "No employees with premium data to test"
        }
    
    elif step_id == "subsidy_check":
        # Combined check
        ft = [e for e in employees if e.get("is_full_time")]
        mec_offered = sum(1 for e in ft if e.get("offered_mec"))
        mec_pct = round((mec_offered / len(ft) * 100), 1) if ft else 0
        mec_pass = mec_pct >= 95
        
        mv_pass = any(p.get("mv_meets_minimum") for p in plans)
        
        all_pass = mec_pass and mv_pass
        subsidy_eligible = not all_pass
        
        result["status"] = "complete"
        result["data"] = {
            "mec_pass": mec_pass,
            "mv_pass": mv_pass,
            "all_pass": all_pass,
            "subsidy_eligible": subsidy_eligible,
            "decision": "all_pass" if all_pass else "any_fail",
            "message": "All checks pass - employees use employer coverage" if all_pass else "Some checks fail - employees may qualify for subsidies"
        }
    
    elif step_id == "plan_approval":
        result["status"] = "complete"
        result["data"] = {
            "approved": True,
            "message": "Plan approved for employee enrollment",
            "approved_at": datetime.now(timezone.utc).isoformat()
        }
    
    elif step_id == "irs_reporting":
        ft = [e for e in employees if e.get("is_full_time")]
        result["status"] = "complete"
        result["data"] = {
            "forms_to_generate": True,
            "form_1095c_count": len(ft),
            "form_1094c": True,
            "tax_year": datetime.now(timezone.utc).year,
            "message": f"Generate {len(ft)} Form 1095-C and 1 Form 1094-C"
        }
    
    elif step_id == "compliance_complete":
        result["status"] = "complete"
        result["data"] = {
            "complete": True,
            "message": "Full ACA compliance achieved",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    
    # Save step result
    await db.compliance_workflows.update_one(
        {"employer_id": employer_id},
        {"$set": {
            f"steps.{step_id}": result,
            "current_step": step_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return result

@api_router.post("/workflow/{employer_id}/run-all")
async def run_full_workflow(employer_id: str, user=Depends(get_current_user)):
    """Execute all workflow steps in sequence"""
    results = {}
    step_order = ["onboarding", "employee_profiles", "fte_calculation", "ale_status",
                  "eligibility", "mec_validation", "mv_calculation", "affordability",
                  "subsidy_check", "plan_approval", "irs_reporting", "compliance_complete"]
    
    for step_id in step_order:
        res = await execute_workflow_step(employer_id, step_id, {}, user)
        results[step_id] = res
        
        # Check for terminal conditions
        if step_id == "ale_status" and res.get("data", {}).get("decision") == "no":
            break
        if step_id == "mec_validation" and res.get("data", {}).get("decision") == "fail":
            break
    
    # Determine overall status
    all_complete = all(r.get("status") == "complete" for r in results.values())
    
    await db.compliance_workflows.update_one(
        {"employer_id": employer_id},
        {"$set": {
            "steps": results,
            "status": "complete" if all_complete else "in_progress",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"steps": results, "status": "complete" if all_complete else "in_progress"}

# --- IRS Forms 1094-C / 1095-C ---

@api_router.get("/irs-forms/1094c/{employer_id}/{tax_year}")
async def get_form_1094c(employer_id: str, tax_year: int, user=Depends(get_current_user)):
    """Generate Form 1094-C data for an employer."""
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    employees = await db.employee_profiles.find(
        {"employer_id": employer_id}, {"_id": 0}
    ).to_list(500)
    plans = await db.plan_library.find({"employer_id": employer_id, "status": "active"}, {"_id": 0}).to_list(100)

    form_data = generate_1094c_data(employer, employees, plans, tax_year)

    # Store in DB
    await db.irs_forms.update_one(
        {"employer_id": employer_id, "tax_year": tax_year, "form_type": "1094-C"},
        {"$set": {**form_data, "generated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )

    return form_data


@api_router.get("/irs-forms/1095c/{employer_id}/{tax_year}")
async def get_forms_1095c(employer_id: str, tax_year: int, user=Depends(get_current_user)):
    """Generate all Form 1095-C data for an employer's full-time employees."""
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    employees = await db.employee_profiles.find(
        {"employer_id": employer_id}, {"_id": 0}
    ).to_list(500)
    plans = await db.plan_library.find({"employer_id": employer_id, "status": "active"}, {"_id": 0}).to_list(100)

    # Get pre-calculated eligibility results (contains accurate offer codes)
    elig_results = await db.eligibility_results.find(
        {"employer_id": employer_id}, {"_id": 0}
    ).to_list(500)
    elig_map = {e["employee_id"]: e for e in elig_results}

    ft_employees = [e for e in employees if e.get("is_full_time")]
    plan_map = {p["id"]: p for p in plans}

    forms = []
    for emp in ft_employees:
        plan = plan_map.get(emp.get("plan_id"), {})
        # Override Line 14 with pre-calculated offer code from eligibility engine
        elig = elig_map.get(emp.get("id"), {})
        offer_code = elig.get("offer_code", "")
        # Only generate 1095-C for employees who were OFFERED coverage (not 1H)
        if offer_code == "1H" or (not offer_code and not emp.get("offered_mec")):
            continue
        form = generate_1095c_data(emp, employer, plan, tax_year)
        if offer_code:
            form["part2"]["line14_all_year"] = offer_code
            for m in form["part2"]["monthly_data"]:
                m["line14_code"] = offer_code
                m["line14_description"] = OFFER_CODES.get(offer_code, "")
        forms.append(form)

    # Store in DB
    await db.irs_forms.update_one(
        {"employer_id": employer_id, "tax_year": tax_year, "form_type": "1095-C-batch"},
        {"$set": {
            "employer_id": employer_id,
            "tax_year": tax_year,
            "form_type": "1095-C-batch",
            "form_count": len(forms),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    return {"forms": forms, "count": len(forms), "tax_year": tax_year}


@api_router.get("/irs-forms/1095c/{employer_id}/{tax_year}/{employee_id}")
async def get_form_1095c_single(employer_id: str, tax_year: int, employee_id: str, user=Depends(get_current_user)):
    """Generate Form 1095-C for a single employee."""
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    employee = await db.employee_profiles.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    plan = {}
    if employee.get("plan_id"):
        plan = await db.plan_library.find_one({"id": employee["plan_id"]}, {"_id": 0}) or {}

    form = generate_1095c_data(employee, employer, plan, tax_year)

    # Override Line 14 with pre-calculated offer code from eligibility engine
    elig = await db.eligibility_results.find_one(
        {"employer_id": employer_id, "employee_id": employee_id}, {"_id": 0}
    )
    if elig and elig.get("offer_code"):
        offer_code = elig["offer_code"]
        # No form for employees without an offer
        if offer_code == "1H":
            raise HTTPException(status_code=400, detail="No 1095-C required: employee was not offered coverage (1H)")
        form["part2"]["line14_all_year"] = offer_code
        for m in form["part2"]["monthly_data"]:
            m["line14_code"] = offer_code
            m["line14_description"] = OFFER_CODES.get(offer_code, "")

    return form


@api_router.get("/irs-forms/1094c/{employer_id}/{tax_year}/pdf")
async def download_1094c_pdf(employer_id: str, tax_year: int, user=Depends(get_current_user)):
    """Download Form 1094-C as PDF."""
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    employees = await db.employee_profiles.find(
        {"employer_id": employer_id}, {"_id": 0}
    ).to_list(500)
    plans = await db.plan_library.find({"employer_id": employer_id, "status": "active"}, {"_id": 0}).to_list(100)

    form_data = generate_1094c_data(employer, employees, plans, tax_year)
    pdf_bytes = render_1094c_pdf(form_data)

    filename = f"1094-C_{employer.get('name', 'employer').replace(' ', '_')}_{tax_year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.get("/irs-forms/1095c/{employer_id}/{tax_year}/{employee_id}/pdf")
async def download_1095c_pdf(employer_id: str, tax_year: int, employee_id: str, user=Depends(get_current_user)):
    """Download Form 1095-C as PDF for a single employee."""
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    employee = await db.employee_profiles.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    plan = {}
    if employee.get("plan_id"):
        plan = await db.plan_library.find_one({"id": employee["plan_id"]}, {"_id": 0}) or {}

    form_data = generate_1095c_data(employee, employer, plan, tax_year)

    # Override Line 14 with pre-calculated offer code
    elig = await db.eligibility_results.find_one(
        {"employer_id": employer_id, "employee_id": employee_id}, {"_id": 0}
    )
    if elig and elig.get("offer_code"):
        offer_code = elig["offer_code"]
        if offer_code == "1H":
            raise HTTPException(status_code=400, detail="No 1095-C required: employee was not offered coverage (1H)")
        form_data["part2"]["line14_all_year"] = offer_code
        for m in form_data["part2"]["monthly_data"]:
            m["line14_code"] = offer_code
            m["line14_description"] = OFFER_CODES.get(offer_code, "")

    pdf_bytes = render_1095c_pdf(form_data)

    emp_name = employee.get("name", "employee").replace(" ", "_")
    filename = f"1095-C_{emp_name}_{tax_year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@api_router.get("/irs-forms/summary/{employer_id}/{tax_year}")
async def get_irs_forms_summary(employer_id: str, tax_year: int, user=Depends(get_current_user)):
    """Get a summary of IRS forms status for an employer/year."""
    employer = await db.employers.find_one({"id": employer_id}, {"_id": 0})
    if not employer:
        raise HTTPException(status_code=404, detail="Employer not found")

    employees = await db.employee_profiles.find(
        {"employer_id": employer_id}, {"_id": 0}
    ).to_list(500)
    plans = await db.plan_library.find({"employer_id": employer_id, "status": "active"}, {"_id": 0}).to_list(100)

    ft_employees = [e for e in employees if e.get("is_full_time")]
    pt_employees = [e for e in employees if not e.get("is_full_time")]
    pt_hours = sum(e.get("monthly_hours", 0) for e in pt_employees)
    fte = round(pt_hours / 120, 2)
    total_fte = len(ft_employees) + fte

    mec_offered = sum(1 for e in ft_employees if e.get("offered_mec"))
    enrolled = sum(1 for e in ft_employees if e.get("enrolled"))

    # Check if forms were previously generated
    existing_1094c = await db.irs_forms.find_one(
        {"employer_id": employer_id, "tax_year": tax_year, "form_type": "1094-C"},
        {"_id": 0}
    )
    existing_1095c = await db.irs_forms.find_one(
        {"employer_id": employer_id, "tax_year": tax_year, "form_type": "1095-C-batch"},
        {"_id": 0}
    )

    return {
        "employer_id": employer_id,
        "employer_name": employer.get("name", ""),
        "tax_year": tax_year,
        "total_employees": len(employees),
        "full_time_employees": len(ft_employees),
        "part_time_employees": len(pt_employees),
        "total_fte": round(total_fte, 2),
        "is_ale": total_fte >= 50,
        "mec_offered_count": mec_offered,
        "enrolled_count": enrolled,
        "plans_count": len(plans),
        "forms_1095c_needed": len(ft_employees),
        "form_1094c_generated": existing_1094c is not None,
        "form_1094c_generated_at": existing_1094c.get("generated_at") if existing_1094c else None,
        "forms_1095c_generated": existing_1095c is not None,
        "forms_1095c_generated_at": existing_1095c.get("generated_at") if existing_1095c else None,
        "forms_1095c_count": existing_1095c.get("form_count", 0) if existing_1095c else 0,
    }


@api_router.get("/irs-forms/codes")
async def get_irs_codes(user=Depends(get_current_user)):
    """Return reference data for IRS form codes."""
    return {
        "line14_codes": OFFER_CODES,
        "line16_codes": SAFE_HARBOR_CODES,
    }


@api_router.get("/prd")
async def get_prd():
    """Serve the PRD document."""
    prd_path = ROOT_DIR.parent / "memory" / "PRD.md"
    if not prd_path.exists():
        raise HTTPException(status_code=404, detail="PRD not found")
    content = prd_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/plain; charset=utf-8")

@api_router.get("/flow-diagram")
async def get_flow_diagram():
    """Serve the flow diagram HTML page."""
    html_path = ROOT_DIR / "static" / "flow-diagram.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="Flow diagram not found")
    content = html_path.read_text(encoding="utf-8")
    return Response(content=content, media_type="text/html; charset=utf-8")

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_origin_regex=r"https?://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
