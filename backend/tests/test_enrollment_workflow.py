"""
ACA Enrollment Workflow Tests - 5-Step Pipeline
Step 1: Plan Library Setup (HR Admin)
Step 2: Auto-Eligibility Engine
Step 3: Employee Self-Service Portal
Step 4: HR Compliance Review
Step 5: Carrier Census Export
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
HR_EMAIL = "test@demo.com"
HR_PASSWORD = "test123"
EMPLOYER_CODE = "H9G9PW"

# Test plan data
TEST_PLAN = {
    "carrier_name": "TEST_Carrier",
    "plan_name": f"TEST_Plan_{uuid.uuid4().hex[:6]}",
    "plan_type": "PPO",
    "category": "medical",
    "premiums_self_only": 500,
    "premiums_employee_spouse": 900,
    "premiums_employee_children": 800,
    "premiums_family": 1200,
    "employer_contribution_self_only": 400,
    "employer_contribution_employee_spouse": 700,
    "employer_contribution_employee_children": 600,
    "employer_contribution_family": 900,
    "individual_deductible": 2000,
    "family_deductible": 4000,
    "coinsurance_rate": 20,
    "oop_max_individual": 7000,
    "oop_max_family": 14000,
    "copay_primary": 30,
    "copay_specialist": 50,
    "copay_er": 300,
    "copay_generic_rx": 10,
    "copay_brand_rx": 40,
    "mv_percentage": 62,
    "mv_certified": True,
    "mec_qualified": True,
}


class TestStep1PlanLibrary:
    """Step 1: Plan Library Setup - CRUD operations for plans"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get HR admin authentication headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        """Get Demo Corp employer ID"""
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        assert response.status_code == 200
        employers = response.json()
        demo = next((e for e in employers if "Demo" in e.get("name", "")), None)
        assert demo is not None, "Demo Corp employer not found"
        return demo["id"]
    
    def test_create_plan(self, auth_headers, employer_id):
        """POST /api/enrollment/plans - Create a plan in library"""
        payload = {**TEST_PLAN, "employer_id": employer_id}
        response = requests.post(f"{BASE_URL}/api/enrollment/plans", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Create plan failed: {response.text}"
        
        data = response.json()
        assert "id" in data, "Plan should have an ID"
        assert data["plan_name"] == TEST_PLAN["plan_name"]
        assert data["carrier_name"] == TEST_PLAN["carrier_name"]
        assert data["category"] == "medical"
        assert data["mec_qualified"] == True
        assert "premiums" in data
        assert data["premiums"]["self_only"] == 500
        assert "employee_cost" in data
        assert data["employee_cost"]["self_only"] == 100  # 500 - 400
        print(f"Created plan: {data['plan_name']} (ID: {data['id']})")
        
        # Store for later tests
        TestStep1PlanLibrary.created_plan_id = data["id"]
    
    def test_get_plans_by_employer(self, auth_headers, employer_id):
        """GET /api/enrollment/plans/{employer_id} - List all plans"""
        response = requests.get(f"{BASE_URL}/api/enrollment/plans/{employer_id}", headers=auth_headers)
        assert response.status_code == 200, f"Get plans failed: {response.text}"
        
        plans = response.json()
        assert isinstance(plans, list)
        print(f"Found {len(plans)} plans for employer")
        
        # Verify our test plan exists
        test_plan = next((p for p in plans if p.get("plan_name") == TEST_PLAN["plan_name"]), None)
        assert test_plan is not None, "Created test plan not found in list"
    
    def test_update_plan(self, auth_headers):
        """PUT /api/enrollment/plans/{plan_id} - Update a plan"""
        plan_id = getattr(TestStep1PlanLibrary, 'created_plan_id', None)
        if not plan_id:
            pytest.skip("No plan created to update")
        
        update_data = {
            "plan_name": f"TEST_Updated_{uuid.uuid4().hex[:4]}",
            "premiums_self_only": 550,
            "employer_contribution_self_only": 450,
        }
        response = requests.put(f"{BASE_URL}/api/enrollment/plans/{plan_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200, f"Update plan failed: {response.text}"
        
        data = response.json()
        assert data["premiums"]["self_only"] == 550
        assert data["employer_contribution"]["self_only"] == 450
        assert data["employee_cost"]["self_only"] == 100  # 550 - 450
        print(f"Updated plan: {data['plan_name']}")
    
    def test_delete_plan(self, auth_headers):
        """DELETE /api/enrollment/plans/{plan_id} - Delete a plan"""
        plan_id = getattr(TestStep1PlanLibrary, 'created_plan_id', None)
        if not plan_id:
            pytest.skip("No plan created to delete")
        
        response = requests.delete(f"{BASE_URL}/api/enrollment/plans/{plan_id}", headers=auth_headers)
        assert response.status_code == 200, f"Delete plan failed: {response.text}"
        
        data = response.json()
        assert data["message"] == "Plan deleted"
        print(f"Deleted plan: {plan_id}")
    
    def test_delete_nonexistent_plan(self, auth_headers):
        """DELETE /api/enrollment/plans/{plan_id} - 404 for nonexistent plan"""
        response = requests.delete(f"{BASE_URL}/api/enrollment/plans/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404


class TestStep2EligibilityEngine:
    """Step 2: Auto-Eligibility Engine"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        employers = response.json()
        demo = next((e for e in employers if "Demo" in e.get("name", "")), None)
        return demo["id"] if demo else None
    
    def test_run_eligibility_engine(self, auth_headers, employer_id):
        """POST /api/enrollment/eligibility/run/{employer_id} - Run eligibility calculation"""
        response = requests.post(f"{BASE_URL}/api/enrollment/eligibility/run/{employer_id}", json={}, headers=auth_headers)
        assert response.status_code == 200, f"Run eligibility failed: {response.text}"
        
        data = response.json()
        assert "total_employees" in data
        assert "eligible" in data
        assert "ineligible" in data
        assert "results" in data
        
        print(f"Eligibility: {data['eligible']} eligible, {data['ineligible']} ineligible out of {data['total_employees']}")
        
        # Verify result structure
        if data["results"]:
            result = data["results"][0]
            assert "employee_id" in result
            assert "employee_name" in result
            assert "is_full_time" in result
            assert "eligible" in result
            assert "offer_code" in result
            assert "affordable" in result
    
    def test_get_eligibility_results(self, auth_headers, employer_id):
        """GET /api/enrollment/eligibility/{employer_id} - Get cached results"""
        response = requests.get(f"{BASE_URL}/api/enrollment/eligibility/{employer_id}", headers=auth_headers)
        assert response.status_code == 200, f"Get eligibility failed: {response.text}"
        
        data = response.json()
        assert "total" in data
        assert "eligible" in data
        assert "ineligible" in data
        assert "results" in data
        print(f"Cached eligibility: {data['total']} total, {data['eligible']} eligible")


class TestStep3EmployerCode:
    """Step 3: Employer Code for Employee Registration"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        employers = response.json()
        demo = next((e for e in employers if "Demo" in e.get("name", "")), None)
        return demo["id"] if demo else None
    
    def test_get_employer_code(self, auth_headers, employer_id):
        """GET /api/enrollment/employer-code/{employer_id} - Get employer access code"""
        response = requests.get(f"{BASE_URL}/api/enrollment/employer-code/{employer_id}", headers=auth_headers)
        assert response.status_code == 200, f"Get employer code failed: {response.text}"
        
        data = response.json()
        assert "access_code" in data
        assert "employer_name" in data
        assert len(data["access_code"]) == 6
        print(f"Employer code: {data['access_code']} for {data['employer_name']}")
    
    def test_register_employee_with_code(self, auth_headers):
        """POST /api/enrollment/employee/register - Register employee with employer code"""
        unique_email = f"test_emp_{uuid.uuid4().hex[:6]}@test.com"
        response = requests.post(f"{BASE_URL}/api/enrollment/employee/register", json={
            "email": unique_email,
            "password": "test123",
            "name": "Test Employee",
            "employer_code": EMPLOYER_CODE
        })
        assert response.status_code == 200, f"Employee registration failed: {response.text}"
        
        data = response.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["role"] == "employee"
        assert data["user"]["employer_name"] is not None
        print(f"Registered employee: {data['user']['email']} linked to {data['user']['employer_name']}")
        
        # Store for cleanup
        TestStep3EmployerCode.test_employee_token = data["token"]
    
    def test_register_employee_invalid_code(self):
        """POST /api/enrollment/employee/register - Invalid employer code returns 400"""
        response = requests.post(f"{BASE_URL}/api/enrollment/employee/register", json={
            "email": f"invalid_{uuid.uuid4().hex[:6]}@test.com",
            "password": "test123",
            "name": "Invalid Employee",
            "employer_code": "INVALID"
        })
        assert response.status_code == 400
        assert "Invalid employer code" in response.json().get("detail", "")
    
    def test_register_employee_missing_fields(self):
        """POST /api/enrollment/employee/register - Missing fields returns 400"""
        response = requests.post(f"{BASE_URL}/api/enrollment/employee/register", json={
            "email": "test@test.com",
            "password": "test123"
        })
        assert response.status_code == 400


class TestStep3EmployeePortal:
    """Step 3: Employee Self-Service Portal"""
    
    @pytest.fixture(scope="class")
    def employee_headers(self):
        """Login as existing employee (Maria Garcia)"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "maria@test.com",
            "password": "test123"
        })
        if response.status_code != 200:
            pytest.skip("Employee maria@test.com not found")
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    def test_get_employee_plans(self, employee_headers):
        """GET /api/enrollment/employee/my-plans - Get eligible plans for employee"""
        response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-plans", headers=employee_headers)
        assert response.status_code == 200, f"Get my-plans failed: {response.text}"
        
        data = response.json()
        assert "medical_plans" in data
        assert "addon_plans" in data
        assert "decline_reasons" in data
        print(f"Employee plans: {len(data['medical_plans'])} medical, {len(data['addon_plans'])} add-ons")
    
    def test_employee_enroll(self, employee_headers):
        """POST /api/enrollment/employee/enroll - Enroll in a plan"""
        # First get available plans
        plans_response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-plans", headers=employee_headers)
        if plans_response.status_code != 200:
            pytest.skip("Could not get plans")
        
        plans = plans_response.json()
        if not plans.get("medical_plans"):
            pytest.skip("No medical plans available")
        
        plan = plans["medical_plans"][0]
        response = requests.post(f"{BASE_URL}/api/enrollment/employee/enroll", json={
            "plan_id": plan["id"],
            "coverage_tier": "self_only",
            "add_on_plan_ids": []
        }, headers=employee_headers)
        assert response.status_code == 200, f"Enroll failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "enrolled"
        assert data["plan_id"] == plan["id"]
        assert data["coverage_tier"] == "self_only"
        assert "employee_premium" in data
        assert "employer_contribution" in data
        print(f"Enrolled in {data['plan_name']}, EE cost: ${data['employee_premium']}/mo")
    
    def test_employee_decline(self):
        """POST /api/enrollment/employee/decline - Decline coverage"""
        # Register a new employee to test decline
        unique_email = f"decline_test_{uuid.uuid4().hex[:6]}@test.com"
        reg_response = requests.post(f"{BASE_URL}/api/enrollment/employee/register", json={
            "email": unique_email,
            "password": "test123",
            "name": "Decline Test",
            "employer_code": EMPLOYER_CODE
        })
        if reg_response.status_code != 200:
            pytest.skip("Could not register test employee")
        
        token = reg_response.json()["token"]
        decline_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        response = requests.post(f"{BASE_URL}/api/enrollment/employee/decline", json={
            "reason": "other_coverage",
            "reason_detail": "Covered by spouse"
        }, headers=decline_headers)
        assert response.status_code == 200, f"Decline failed: {response.text}"
        
        data = response.json()
        assert data["status"] == "declined"
        assert data["decline_reason"] == "other_coverage"
        print(f"Declined coverage: {data['decline_reason']}")


class TestStep4HRReview:
    """Step 4: HR Compliance Review"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        employers = response.json()
        demo = next((e for e in employers if "Demo" in e.get("name", "")), None)
        return demo["id"] if demo else None
    
    def test_get_enrollment_review(self, auth_headers, employer_id):
        """GET /api/enrollment/review/{employer_id} - Get all enrollments for review"""
        response = requests.get(f"{BASE_URL}/api/enrollment/review/{employer_id}", headers=auth_headers)
        assert response.status_code == 200, f"Get review failed: {response.text}"
        
        data = response.json()
        assert "total_enrollments" in data
        assert "enrolled" in data
        assert "declined" in data
        assert "pending_approval" in data
        assert "enrollments" in data
        
        print(f"Review: {data['enrolled']} enrolled, {data['declined']} declined, {data['pending_approval']} pending")
        
        # Check decline reasons breakdown
        if data.get("decline_reasons"):
            print(f"Decline reasons: {data['decline_reasons']}")
    
    def test_approve_all_enrollments(self, auth_headers, employer_id):
        """POST /api/enrollment/review/{employer_id}/approve-all - Bulk approve"""
        response = requests.post(f"{BASE_URL}/api/enrollment/review/{employer_id}/approve-all", json={}, headers=auth_headers)
        assert response.status_code == 200, f"Approve all failed: {response.text}"
        
        data = response.json()
        assert "approved_count" in data
        print(f"Approved {data['approved_count']} enrollments")


class TestStep5CensusExport:
    """Step 5: Carrier Census Export"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        employers = response.json()
        demo = next((e for e in employers if "Demo" in e.get("name", "")), None)
        return demo["id"] if demo else None
    
    def test_generate_census(self, auth_headers, employer_id):
        """POST /api/enrollment/census/{employer_id} - Generate census data"""
        response = requests.post(f"{BASE_URL}/api/enrollment/census/{employer_id}", json={}, headers=auth_headers)
        
        # May return 400 if no approved enrollments
        if response.status_code == 400:
            print(f"Census generation skipped: {response.json().get('detail')}")
            pytest.skip("No approved enrollments for census")
        
        assert response.status_code == 200, f"Generate census failed: {response.text}"
        
        data = response.json()
        assert "id" in data
        assert "total_enrolled" in data
        assert "rows" in data
        
        print(f"Census generated: {data['total_enrolled']} employees, ID: {data['id']}")
        
        # Verify row structure
        if data["rows"]:
            row = data["rows"][0]
            assert "employee_name" in row
            assert "plan_name" in row
            assert "coverage_tier" in row
            assert "employee_premium" in row
            assert "employer_contribution" in row
            assert "offer_code" in row
        
        # Store for download test
        TestStep5CensusExport.census_id = data["id"]
    
    def test_download_census_excel(self, auth_headers, employer_id):
        """GET /api/enrollment/census/{employer_id}/download/{census_id} - Download Excel"""
        census_id = getattr(TestStep5CensusExport, 'census_id', None)
        if not census_id:
            pytest.skip("No census generated to download")
        
        response = requests.get(
            f"{BASE_URL}/api/enrollment/census/{employer_id}/download/{census_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Download census failed: {response.text}"
        
        # Verify it's an Excel file
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheet" in content_type or "octet-stream" in content_type
        
        content_disp = response.headers.get("Content-Disposition", "")
        assert "census_" in content_disp
        assert ".xlsx" in content_disp
        
        print(f"Downloaded Excel file: {len(response.content)} bytes")
    
    def test_get_census_history(self, auth_headers, employer_id):
        """GET /api/enrollment/census-history/{employer_id} - Get export history"""
        response = requests.get(f"{BASE_URL}/api/enrollment/census-history/{employer_id}", headers=auth_headers)
        assert response.status_code == 200, f"Get census history failed: {response.text}"
        
        history = response.json()
        assert isinstance(history, list)
        print(f"Census history: {len(history)} exports")
        
        if history:
            item = history[0]
            assert "id" in item
            assert "total_enrolled" in item
            assert "generated_at" in item


class TestCSVUpload:
    """Test CSV upload for plans"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": HR_EMAIL,
            "password": HR_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        employers = response.json()
        demo = next((e for e in employers if "Demo" in e.get("name", "")), None)
        return demo["id"] if demo else None
    
    def test_upload_plans_csv(self, auth_headers, employer_id):
        """POST /api/enrollment/plans/upload/{employer_id} - Upload plans via CSV"""
        csv_content = """carrier_name,plan_name,plan_type,category,premiums_self_only,premiums_family,employer_contribution_self_only,employer_contribution_family,individual_deductible,family_deductible,mec_qualified
TEST_CSV_Carrier,TEST_CSV_Plan_1,PPO,medical,400,1000,300,700,2000,4000,true
TEST_CSV_Carrier,TEST_CSV_Plan_2,HMO,medical,350,900,250,600,1500,3000,true"""
        
        files = {"file": ("plans.csv", csv_content, "text/csv")}
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/upload/{employer_id}",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200, f"CSV upload failed: {response.text}"
        
        data = response.json()
        assert "created" in data
        assert data["created"] >= 2
        print(f"CSV upload: {data['created']} plans created, {len(data.get('errors', []))} errors")
        
        # Cleanup - delete test plans
        for plan in data.get("plans", []):
            requests.delete(f"{BASE_URL}/api/enrollment/plans/{plan['id']}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
