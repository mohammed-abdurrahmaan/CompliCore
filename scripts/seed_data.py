"""
Seed script to populate CompliCore database with realistic ACA compliance data.
Recreates the data that was present during testing iterations.
"""
import pymongo
import bcrypt
import uuid
import random
from datetime import datetime, timezone, timedelta

client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["complicore"]

EMPLOYER_USER_ID = "f90cebe2-eda5-4651-8f1d-0e5a6abfc005"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"
NOW = datetime.now(timezone.utc).isoformat()

# ============================
# PLAN LIBRARY (8 plans: 5 medical, 2 dental, 1 vision)
# ============================
PLANS = [
    {
        "id": "bc701f0b-29c4-4f37-ab42-ebb4f5fad085",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "Aetna",
        "plan_name": "Gold HMO",
        "plan_type": "HMO",
        "category": "medical",
        "premiums": {"self_only": 650, "employee_spouse": 1200, "employee_children": 1050, "family": 1700},
        "employer_contribution": {"self_only": 535, "employee_spouse": 900, "employee_children": 800, "family": 1300},
        "employee_cost": {"self_only": 115, "employee_spouse": 300, "employee_children": 250, "family": 400},
        "individual_deductible": 1500,
        "family_deductible": 3000,
        "coinsurance_rate": 20,
        "oop_max_individual": 6000,
        "oop_max_family": 12000,
        "copay_primary": 25,
        "copay_specialist": 50,
        "copay_er": 250,
        "copay_generic_rx": 10,
        "copay_brand_rx": 35,
        "mv_percentage": 78.4,
        "mv_certified": True,
        "mec_qualified": True,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "coverage_levels": {"self_only": True, "employee_spouse": True, "employee_children": True, "family": True},
        "created_at": NOW,
    },
    {
        "id": "ac820c3c-4409-4818-82c5-55c8ba523ce9",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "Blue Cross Blue Shield",
        "plan_name": "Silver PPO",
        "plan_type": "PPO",
        "category": "medical",
        "premiums": {"self_only": 550, "employee_spouse": 1000, "employee_children": 900, "family": 1450},
        "employer_contribution": {"self_only": 450, "employee_spouse": 750, "employee_children": 680, "family": 1100},
        "employee_cost": {"self_only": 100, "employee_spouse": 250, "employee_children": 220, "family": 350},
        "individual_deductible": 2500,
        "family_deductible": 5000,
        "coinsurance_rate": 25,
        "oop_max_individual": 7500,
        "oop_max_family": 15000,
        "copay_primary": 30,
        "copay_specialist": 60,
        "copay_er": 300,
        "copay_generic_rx": 15,
        "copay_brand_rx": 45,
        "mv_percentage": 62.1,
        "mv_certified": True,
        "mec_qualified": True,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "coverage_levels": {"self_only": True, "employee_spouse": True, "employee_children": True, "family": True},
        "created_at": NOW,
    },
    {
        "id": "46ef441c-ab24-4a2d-a583-79f29ada5dcf",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "UnitedHealthcare",
        "plan_name": "Bronze HDHP",
        "plan_type": "HDHP",
        "category": "medical",
        "premiums": {"self_only": 380, "employee_spouse": 700, "employee_children": 620, "family": 1000},
        "employer_contribution": {"self_only": 300, "employee_spouse": 520, "employee_children": 460, "family": 750},
        "employee_cost": {"self_only": 80, "employee_spouse": 180, "employee_children": 160, "family": 250},
        "individual_deductible": 3500,
        "family_deductible": 7000,
        "coinsurance_rate": 30,
        "oop_max_individual": 8700,
        "oop_max_family": 17400,
        "copay_primary": 40,
        "copay_specialist": 75,
        "copay_er": 350,
        "copay_generic_rx": 20,
        "copay_brand_rx": 55,
        "mv_percentage": 58.2,
        "mv_certified": True,
        "mec_qualified": True,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "coverage_levels": {"self_only": True, "employee_spouse": True, "employee_children": True, "family": True},
        "created_at": NOW,
    },
    {
        "id": "16739425-5a63-45d9-9fde-418724747016",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "Cigna",
        "plan_name": "Platinum PPO",
        "plan_type": "PPO",
        "category": "medical",
        "premiums": {"self_only": 950, "employee_spouse": 1800, "employee_children": 1550, "family": 2500},
        "employer_contribution": {"self_only": 206, "employee_spouse": 400, "employee_children": 350, "family": 550},
        "employee_cost": {"self_only": 744, "employee_spouse": 1400, "employee_children": 1200, "family": 1950},
        "individual_deductible": 500,
        "family_deductible": 1000,
        "coinsurance_rate": 10,
        "oop_max_individual": 3000,
        "oop_max_family": 6000,
        "copay_primary": 15,
        "copay_specialist": 30,
        "copay_er": 150,
        "copay_generic_rx": 5,
        "copay_brand_rx": 25,
        "mv_percentage": 55.0,
        "mv_certified": False,
        "mec_qualified": True,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "coverage_levels": {"self_only": True, "employee_spouse": True, "employee_children": True, "family": True},
        "created_at": NOW,
    },
    {
        "id": "d8f23a91-7b12-4c5e-9a3d-1e8f6b2c4d7a",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "Kaiser Permanente",
        "plan_name": "Standard EPO",
        "plan_type": "EPO",
        "category": "medical",
        "premiums": {"self_only": 480, "employee_spouse": 880, "employee_children": 780, "family": 1250},
        "employer_contribution": {"self_only": 385, "employee_spouse": 660, "employee_children": 590, "family": 940},
        "employee_cost": {"self_only": 95, "employee_spouse": 220, "employee_children": 190, "family": 310},
        "individual_deductible": 2000,
        "family_deductible": 4000,
        "coinsurance_rate": 20,
        "oop_max_individual": 7000,
        "oop_max_family": 14000,
        "copay_primary": 30,
        "copay_specialist": 55,
        "copay_er": 275,
        "copay_generic_rx": 12,
        "copay_brand_rx": 40,
        "mv_percentage": 65.3,
        "mv_certified": True,
        "mec_qualified": True,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "coverage_levels": {"self_only": True, "employee_spouse": True, "employee_children": True, "family": True},
        "created_at": NOW,
    },
    {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "Delta Dental",
        "plan_name": "Dental PPO Basic",
        "plan_type": "PPO",
        "category": "dental",
        "premiums": {"self_only": 45, "employee_spouse": 85, "employee_children": 75, "family": 120},
        "employer_contribution": {"self_only": 35, "employee_spouse": 60, "employee_children": 55, "family": 85},
        "employee_cost": {"self_only": 10, "employee_spouse": 25, "employee_children": 20, "family": 35},
        "individual_deductible": 50,
        "family_deductible": 150,
        "coinsurance_rate": 20,
        "oop_max_individual": 1500,
        "oop_max_family": 3000,
        "copay_primary": 0,
        "copay_specialist": 0,
        "copay_er": 0,
        "copay_generic_rx": 0,
        "copay_brand_rx": 0,
        "mv_percentage": None,
        "mv_certified": False,
        "mec_qualified": False,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "created_at": NOW,
    },
    {
        "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "Delta Dental",
        "plan_name": "Dental PPO Premium",
        "plan_type": "PPO",
        "category": "dental",
        "premiums": {"self_only": 75, "employee_spouse": 140, "employee_children": 125, "family": 200},
        "employer_contribution": {"self_only": 60, "employee_spouse": 100, "employee_children": 90, "family": 145},
        "employee_cost": {"self_only": 15, "employee_spouse": 40, "employee_children": 35, "family": 55},
        "individual_deductible": 0,
        "family_deductible": 0,
        "coinsurance_rate": 10,
        "oop_max_individual": 2000,
        "oop_max_family": 4000,
        "copay_primary": 0,
        "copay_specialist": 0,
        "copay_er": 0,
        "copay_generic_rx": 0,
        "copay_brand_rx": 0,
        "mv_percentage": None,
        "mv_certified": False,
        "mec_qualified": False,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "created_at": NOW,
    },
    {
        "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
        "employer_id": EMPLOYER_ID,
        "carrier_name": "VSP Vision",
        "plan_name": "Vision Basic",
        "plan_type": "PPO",
        "category": "vision",
        "premiums": {"self_only": 20, "employee_spouse": 38, "employee_children": 35, "family": 55},
        "employer_contribution": {"self_only": 15, "employee_spouse": 28, "employee_children": 25, "family": 40},
        "employee_cost": {"self_only": 5, "employee_spouse": 10, "employee_children": 10, "family": 15},
        "individual_deductible": 10,
        "family_deductible": 25,
        "coinsurance_rate": 0,
        "oop_max_individual": 500,
        "oop_max_family": 1000,
        "copay_primary": 10,
        "copay_specialist": 10,
        "copay_er": 0,
        "copay_generic_rx": 0,
        "copay_brand_rx": 0,
        "mv_percentage": None,
        "mv_certified": False,
        "mec_qualified": False,
        "plan_year_start": "2026-01-01",
        "plan_year_end": "2026-12-31",
        "sbc_url": "",
        "status": "active",
        "created_at": NOW,
    },
]

# ============================
# EMPLOYEE PROFILES (60 employees: 47 FT, 13 PT)
# ============================
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
    "Zara Bell", "Adam Murphy", "Beth Bailey", "Chase Cooper", "Diana Richardson",
    "Eric Foster", "Fiona Hayes", "George Palmer", "Hannah Brooks", "Ivan Ward"
]

DEPARTMENTS = ["Engineering", "Sales", "Marketing", "HR", "Finance", "Operations", "Support"]
JOB_TITLES_FT = ["Software Engineer", "Sales Manager", "Marketing Specialist", "HR Coordinator",
                  "Financial Analyst", "Operations Manager", "Support Lead", "Product Manager",
                  "Data Analyst", "Business Development", "Account Executive", "Senior Developer"]
JOB_TITLES_PT = ["Part-Time Assistant", "Contract Worker", "Seasonal Worker", "Intern", "Temp Staff"]

COVERAGE_TIERS = ["individual", "employee_spouse", "employee_children", "family"]

random.seed(42)  # For reproducibility

employees = []
payroll_employees = []
eligibility_results = []

for i in range(60):
    emp_id = str(uuid.uuid4())
    name = MOCK_EMPLOYEE_NAMES[i]
    
    # First 47 are full-time, last 13 are part-time
    is_full_time = i < 47
    
    if is_full_time:
        weekly_hours = random.randint(35, 45)
        annual_salary = random.randint(38000, 120000)
        job_title = random.choice(JOB_TITLES_FT)
    else:
        weekly_hours = random.randint(12, 28)
        annual_salary = random.randint(15000, 30000)
        job_title = random.choice(JOB_TITLES_PT)
    
    monthly_hours = round(weekly_hours * 4.33, 1)
    hourly_rate = round(annual_salary / (weekly_hours * 52), 2)
    department = DEPARTMENTS[i % len(DEPARTMENTS)]
    hire_year = random.randint(2018, 2025)
    hire_month = random.randint(1, 12)
    hire_day = random.randint(1, 28)
    hire_date = f"{hire_year}-{hire_month:02d}-{hire_day:02d}"
    
    coverage_tier = random.choice(COVERAGE_TIERS) if is_full_time else "individual"
    num_dependents = random.randint(0, 3) if is_full_time else 0
    
    email_name = name.lower().replace(" ", ".") 
    email = f"{email_name}@acmecorp.com"
    
    # Eligibility
    if is_full_time:
        eligibility_status = "eligible"
        offered_mec = True
    else:
        eligibility_status = "not_eligible"
        offered_mec = False
    
    profile = {
        "id": emp_id,
        "employer_id": EMPLOYER_ID,
        "name": name,
        "ssn_last4": f"{random.randint(1000, 9999)}",
        "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Pine', 'Maple', 'Cedar'])} {random.choice(['St', 'Ave', 'Blvd', 'Dr', 'Ln'])}, {random.choice(['Springfield', 'Chicago', 'Houston', 'Phoenix', 'Dallas'])}, {random.choice(['IL', 'TX', 'AZ', 'CA', 'NY'])} {random.randint(10000, 99999)}",
        "email": email,
        "phone": f"({random.randint(200,999)}) {random.randint(100,999)}-{random.randint(1000,9999)}",
        "hire_date": hire_date,
        "job_title": job_title,
        "department": department,
        "employment_type": "full_time" if is_full_time else "part_time",
        "weekly_hours": weekly_hours,
        "monthly_hours": monthly_hours,
        "annual_salary": annual_salary,
        "hourly_rate": hourly_rate,
        "w2_wages": annual_salary,
        "spouse_name": f"{random.choice(['Sarah', 'Mike', 'Lisa', 'Tom', 'Anna'])} {name.split()[-1]}" if num_dependents > 0 and is_full_time else "",
        "num_dependents": num_dependents,
        "dependents": [],
        "plan_id": "",
        "plan_name": "",
        "coverage_start_date": "2026-01-01" if is_full_time else "",
        "coverage_tier": coverage_tier,
        "employee_monthly_premium": 0,
        "employer_monthly_premium": 0,
        "is_full_time": is_full_time,
        "eligibility_status": eligibility_status,
        "offered_mec": offered_mec,
        "enrolled": False,
        "created_at": NOW,
        "updated_at": NOW,
    }
    employees.append(profile)
    
    # Payroll record
    payroll_emp = {
        "id": emp_id,
        "employer_id": EMPLOYER_ID,
        "name": name,
        "employee_id": f"EMP-{1000 + i}",
        "department": department,
        "employment_type": "full_time" if is_full_time else "part_time",
        "weekly_hours": weekly_hours,
        "monthly_hours": monthly_hours,
        "annual_salary": annual_salary,
        "hourly_rate": hourly_rate,
        "hire_date": hire_date,
        "offered_mec": offered_mec,
        "enrolled": False,
        "created_at": NOW,
    }
    payroll_employees.append(payroll_emp)
    
    # Medical plans for eligibility
    medical_plan_ids = [p["id"] for p in PLANS if p["category"] == "medical" and p["mec_qualified"]]
    addon_plan_ids = [p["id"] for p in PLANS if p["category"] in ("dental", "vision")]
    
    # Offer code logic
    if is_full_time:
        offer_code = "1B"  # Default for FT with medical offer
        eligible = True
    else:
        offer_code = "1H"
        eligible = False
    
    # Lowest cost self-only
    lowest_ee_cost = min(p["employee_cost"]["self_only"] for p in PLANS if p["category"] == "medical" and p["mec_qualified"])
    annual_ee_cost = lowest_ee_cost * 12
    affordable = (annual_ee_cost <= annual_salary * 0.0996) if annual_salary > 0 else False
    
    eligibility = {
        "id": str(uuid.uuid4()),
        "employer_id": EMPLOYER_ID,
        "employee_id": emp_id,
        "employee_name": name,
        "is_full_time": is_full_time,
        "weekly_hours": weekly_hours,
        "monthly_hours": monthly_hours,
        "annual_salary": annual_salary,
        "eligible": eligible,
        "eligible_plan_ids": medical_plan_ids if eligible else [],
        "addon_plan_ids": addon_plan_ids if eligible else [],
        "offer_code": offer_code,
        "safe_harbor_method": "W-2",
        "affordable": affordable,
        "lowest_cost_contribution": lowest_ee_cost if eligible else 0,
        "calculated_at": NOW,
    }
    eligibility_results.append(eligibility)

# ============================
# PLAN ASSIGNMENTS (assign some FT employees to plans)
# ============================
plan_assignments = []
ft_employees = [e for e in employees if e["is_full_time"]]

# Assign most FT employees to Silver PPO or Gold HMO
for i, emp in enumerate(ft_employees):
    if i < 20:
        plan = PLANS[1]  # Silver PPO
    elif i < 35:
        plan = PLANS[0]  # Gold HMO
    elif i < 42:
        plan = PLANS[4]  # Standard EPO
    else:
        plan = PLANS[2]  # Bronze HDHP
    
    assignment = {
        "id": str(uuid.uuid4()),
        "employer_id": EMPLOYER_ID,
        "plan_id": plan["id"],
        "plan_name": plan["plan_name"],
        "plan_category": plan["category"],
        "employee_id": emp["id"],
        "employee_name": emp["name"],
        "assigned_at": NOW,
        "assigned_by": EMPLOYER_USER_ID,
    }
    plan_assignments.append(assignment)

# ============================
# ENROLLMENTS (some employees enrolled, some declined)
# ============================
enrollments = []
for i, emp in enumerate(ft_employees):
    if i < 20:
        plan = PLANS[1]  # Silver PPO
    elif i < 35:
        plan = PLANS[0]  # Gold HMO
    elif i < 42:
        plan = PLANS[4]  # Standard EPO
    else:
        plan = PLANS[2]  # Bronze HDHP
    
    # 85% enrolled, 15% declined
    if random.random() < 0.85:
        enrollment = {
            "id": str(uuid.uuid4()),
            "employer_id": EMPLOYER_ID,
            "employee_id": emp["id"],
            "employee_name": emp["name"],
            "plan_id": plan["id"],
            "plan_name": plan["plan_name"],
            "coverage_tier": emp["coverage_tier"],
            "status": "enrolled",
            "enrolled_at": NOW,
            "created_at": NOW,
        }
        # Update employee profile
        emp["enrolled"] = True
        emp["plan_id"] = plan["id"]
        emp["plan_name"] = plan["plan_name"]
        emp["employee_monthly_premium"] = plan["employee_cost"]["self_only"]
        emp["employer_monthly_premium"] = plan["employer_contribution"]["self_only"]
    else:
        enrollment = {
            "id": str(uuid.uuid4()),
            "employer_id": EMPLOYER_ID,
            "employee_id": emp["id"],
            "employee_name": emp["name"],
            "plan_id": "",
            "plan_name": "",
            "coverage_tier": "",
            "status": "declined",
            "decline_reason": random.choice(["spouse_coverage", "other_coverage", "too_expensive"]),
            "enrolled_at": NOW,
            "created_at": NOW,
        }
    enrollments.append(enrollment)

# Update payroll enrolled status to match
for pe in payroll_employees:
    matching_emp = next((e for e in employees if e["id"] == pe["id"]), None)
    if matching_emp:
        pe["enrolled"] = matching_emp["enrolled"]
        pe["offered_mec"] = matching_emp["offered_mec"]

# ============================
# MEC TRACKING DATA
# ============================
mec_tracking = []
for month in range(1, 7):  # Jan-Jun 2026
    ft_count = 47
    offered = ft_count
    enrolled_count = sum(1 for e in enrollments if e["status"] == "enrolled")
    coverage_pct = round(enrolled_count / ft_count * 100, 1) if ft_count > 0 else 0
    
    mec_record = {
        "id": str(uuid.uuid4()),
        "employer_id": EMPLOYER_ID,
        "year": 2026,
        "month": month,
        "full_time_count": ft_count,
        "offered_mec": offered,
        "enrolled_mec": enrolled_count,
        "coverage_percentage": coverage_pct,
        "compliant": coverage_pct >= 95,
        "created_at": NOW,
    }
    mec_tracking.append(mec_record)

# ============================
# ALE CALCULATIONS
# ============================
ft_count = 47
pt_employees_list = [e for e in employees if not e["is_full_time"]]
pt_total_hours = sum(e["monthly_hours"] for e in pt_employees_list)
fte_from_pt = round(pt_total_hours / 120, 2)
total_fte = round(ft_count + fte_from_pt, 2)

ale_calc = {
    "id": str(uuid.uuid4()),
    "employer_id": EMPLOYER_ID,
    "year": 2026,
    "total_employees": 60,
    "full_time_count": ft_count,
    "part_time_count": 13,
    "fte_from_part_time": fte_from_pt,
    "total_fte": total_fte,
    "is_ale": total_fte >= 50,
    "threshold": 50,
    "created_at": NOW,
}

# ============================
# INSERT ALL DATA
# ============================
print("Clearing existing data...")
for col in ["plan_library", "employee_profiles", "payroll_employees", 
            "eligibility_results", "plan_assignments", "enrollments",
            "mec_tracking", "ale_calculations"]:
    db[col].delete_many({"employer_id": EMPLOYER_ID})

print(f"Inserting {len(PLANS)} plans...")
db.plan_library.insert_many(PLANS)

print(f"Inserting {len(employees)} employee profiles...")
db.employee_profiles.insert_many(employees)

print(f"Inserting {len(payroll_employees)} payroll employees...")
db.payroll_employees.insert_many(payroll_employees)

print(f"Inserting {len(eligibility_results)} eligibility results...")
db.eligibility_results.insert_many(eligibility_results)

print(f"Inserting {len(plan_assignments)} plan assignments...")
db.plan_assignments.insert_many(plan_assignments)

print(f"Inserting {len(enrollments)} enrollments...")
db.enrollments.insert_many(enrollments)

print(f"Inserting {len(mec_tracking)} MEC tracking records...")
db.mec_tracking.insert_many(mec_tracking)

print("Inserting ALE calculation...")
db.ale_calculations.insert_one(ale_calc)

# ============================
# SUMMARY
# ============================
enrolled_count = sum(1 for e in enrollments if e["status"] == "enrolled")
declined_count = sum(1 for e in enrollments if e["status"] == "declined")

print("\n" + "="*50)
print("SEED DATA SUMMARY")
print("="*50)
print(f"Plans (plan_library):     {len(PLANS)} (5 medical, 2 dental, 1 vision)")
print(f"Employee Profiles:        {len(employees)} (47 FT, 13 PT)")
print(f"Payroll Employees:        {len(payroll_employees)}")
print(f"Eligibility Results:      {len(eligibility_results)}")
print(f"Plan Assignments:         {len(plan_assignments)}")
print(f"Enrollments:              {len(enrollments)} ({enrolled_count} enrolled, {declined_count} declined)")
print(f"MEC Tracking:             {len(mec_tracking)} months")
print(f"ALE Status:               {'ALE' if ale_calc['is_ale'] else 'Not ALE'} (FTE: {total_fte})")
print(f"\nMedical Plans:")
for p in PLANS:
    if p["category"] == "medical":
        print(f"  - {p['plan_name']} ({p['plan_type']}) | EE Cost: ${p['employee_cost']['self_only']}/mo | MV: {p['mv_percentage']}% | MEC: {p['mec_qualified']}")
print("\nDone!")
