"""
ACA Compliance Workflow Engine Tests
Testing: GET/POST /api/workflow/{employer_id}/* endpoints
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials provided in the review request
TEST_EMAIL = "test_wf@test.com"
TEST_PASSWORD = "test123"
TEST_EMPLOYER_NAME = "Acme Corp"


class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    def test_login_success(self, session):
        """Test login with valid credentials"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["role"] == "employer"
        print(f"Login successful for user: {data['user']['name']}")


class TestWorkflowAPI:
    """Workflow API endpoint tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authentication headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        """Get employer ID (Acme Corp should already exist)"""
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get employers: {response.text}"
        employers = response.json()
        
        # Find Acme Corp
        acme = next((e for e in employers if e["name"] == TEST_EMPLOYER_NAME), None)
        if acme:
            print(f"Found employer: {acme['name']} (ID: {acme['id']})")
            return acme["id"]
        
        # If not found, create it
        print(f"Employer '{TEST_EMPLOYER_NAME}' not found, creating...")
        response = requests.post(f"{BASE_URL}/api/employers", 
                                json={"name": TEST_EMPLOYER_NAME, "ein": "12-3456789"},
                                headers=auth_headers)
        assert response.status_code == 200, f"Failed to create employer: {response.text}"
        return response.json()["id"]
    
    # --- GET /api/workflow/{employer_id} ---
    def test_get_workflow_initial_state(self, auth_headers, employer_id):
        """Test retrieving initial workflow state"""
        response = requests.get(f"{BASE_URL}/api/workflow/{employer_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get workflow: {response.text}"
        
        data = response.json()
        assert "employer_id" in data, "Missing employer_id in workflow"
        assert data["employer_id"] == employer_id
        assert "status" in data
        assert "steps" in data
        print(f"Workflow state: status={data['status']}, steps={len(data.get('steps', {}))}")
    
    # --- POST /api/workflow/{employer_id}/execute/{step_id} ---
    def test_execute_step_onboarding(self, auth_headers, employer_id):
        """Test executing onboarding step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/onboarding",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute onboarding: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "onboarding"
        assert "status" in data
        assert "data" in data
        
        # Onboarding should show employer name
        if data["status"] == "complete":
            assert "employer_name" in data["data"]
            print(f"Onboarding complete: {data['data'].get('employer_name', 'N/A')}")
        else:
            print(f"Onboarding status: {data['status']}")
    
    def test_execute_step_employee_profiles(self, auth_headers, employer_id):
        """Test executing employee_profiles step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/employee_profiles",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute employee_profiles: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "employee_profiles"
        assert "status" in data
        assert "data" in data
        
        # Should show employee counts
        if "total_employees" in data["data"]:
            print(f"Employee Profiles: {data['data']['total_employees']} total employees")
    
    def test_execute_step_fte_calculation(self, auth_headers, employer_id):
        """Test executing FTE calculation step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/fte_calculation",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute fte_calculation: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "fte_calculation"
        assert "status" in data
        
        if "total_fte" in data.get("data", {}):
            print(f"FTE Calculation: total_fte={data['data']['total_fte']}")
    
    def test_execute_step_ale_status(self, auth_headers, employer_id):
        """Test executing ALE status determination step (decision step)"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/ale_status",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute ale_status: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "ale_status"
        assert data["status"] == "complete"  # ALE status always completes
        
        # Check for decision data
        assert "decision" in data["data"], "ALE status should have a decision"
        print(f"ALE Status: is_ale={data['data'].get('is_ale', 'N/A')}, decision={data['data'].get('decision')}")
    
    def test_execute_step_eligibility(self, auth_headers, employer_id):
        """Test executing eligibility determination step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/eligibility",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute eligibility: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "eligibility"
        print(f"Eligibility: status={data['status']}, eligible={data['data'].get('eligible', 0)}")
    
    def test_execute_step_mec_validation(self, auth_headers, employer_id):
        """Test executing MEC validation step (decision step)"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/mec_validation",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute mec_validation: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "mec_validation"
        assert "decision" in data["data"], "MEC validation should have a decision"
        print(f"MEC Validation: coverage_pct={data['data'].get('coverage_pct', 0)}%, decision={data['data'].get('decision')}")
    
    def test_execute_step_mv_calculation(self, auth_headers, employer_id):
        """Test executing MV calculation step (decision step)"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/mv_calculation",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute mv_calculation: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "mv_calculation"
        print(f"MV Calculation: status={data['status']}, message={data['data'].get('message', 'N/A')}")
    
    def test_execute_step_affordability(self, auth_headers, employer_id):
        """Test executing affordability testing step (decision step)"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/affordability",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute affordability: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "affordability"
        print(f"Affordability: status={data['status']}, tested={data['data'].get('tested', 0)}")
    
    def test_execute_step_subsidy_check(self, auth_headers, employer_id):
        """Test executing subsidy eligibility check step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/subsidy_check",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute subsidy_check: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "subsidy_check"
        print(f"Subsidy Check: mec_pass={data['data'].get('mec_pass')}, mv_pass={data['data'].get('mv_pass')}")
    
    def test_execute_step_plan_approval(self, auth_headers, employer_id):
        """Test executing plan approval step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/plan_approval",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute plan_approval: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "plan_approval"
        assert data["status"] == "complete"
        print(f"Plan Approval: approved={data['data'].get('approved')}")
    
    def test_execute_step_irs_reporting(self, auth_headers, employer_id):
        """Test executing IRS reporting step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/irs_reporting",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute irs_reporting: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "irs_reporting"
        print(f"IRS Reporting: 1095-C count={data['data'].get('form_1095c_count', 0)}")
    
    def test_execute_step_compliance_complete(self, auth_headers, employer_id):
        """Test executing compliance complete step"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/execute/compliance_complete",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to execute compliance_complete: {response.text}"
        
        data = response.json()
        assert data["step_id"] == "compliance_complete"
        assert data["status"] == "complete"
        print(f"Compliance Complete: {data['data'].get('message')}")
    
    # --- POST /api/workflow/{employer_id}/run-all ---
    def test_run_full_workflow(self, auth_headers, employer_id):
        """Test running all workflow steps at once"""
        response = requests.post(
            f"{BASE_URL}/api/workflow/{employer_id}/run-all",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed to run full workflow: {response.text}"
        
        data = response.json()
        assert "steps" in data, "Response should contain steps"
        assert "status" in data, "Response should contain overall status"
        
        steps = data["steps"]
        completed = sum(1 for s in steps.values() if s.get("status") == "complete")
        total = len(steps)
        
        print(f"Full Workflow: {completed}/{total} steps completed, overall status={data['status']}")
        
        # Verify expected steps are present
        expected_steps = ["onboarding", "employee_profiles", "fte_calculation", "ale_status"]
        for step_id in expected_steps:
            assert step_id in steps, f"Missing step: {step_id}"
    
    # --- Verify workflow state after run-all ---
    def test_get_workflow_after_run_all(self, auth_headers, employer_id):
        """Test that workflow state persists after run-all"""
        response = requests.get(f"{BASE_URL}/api/workflow/{employer_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed to get workflow: {response.text}"
        
        data = response.json()
        steps = data.get("steps", {})
        
        # Count completed steps
        completed = sum(1 for s in steps.values() if s.get("status") == "complete")
        print(f"Workflow state persisted: {completed} completed steps")
        
        # Verify at least some steps were saved
        assert len(steps) > 0, "Workflow should have some steps saved"


class TestEmployerEndpoints:
    """Test employer-related endpoints used in workflow"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    def test_get_employers_list(self, auth_headers):
        """Test getting list of employers"""
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        assert response.status_code == 200
        
        employers = response.json()
        assert isinstance(employers, list)
        print(f"Found {len(employers)} employer(s)")
        
        # Check for Acme Corp
        acme = next((e for e in employers if e["name"] == TEST_EMPLOYER_NAME), None)
        if acme:
            print(f"Acme Corp found with ID: {acme['id']}")


class TestDashboardEndpoints:
    """Test dashboard endpoints that show workflow CTA"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['token']}"}
    
    @pytest.fixture(scope="class")
    def employer_id(self, auth_headers):
        response = requests.get(f"{BASE_URL}/api/employers", headers=auth_headers)
        employers = response.json()
        acme = next((e for e in employers if e["name"] == TEST_EMPLOYER_NAME), None)
        return acme["id"] if acme else None
    
    def test_enhanced_dashboard(self, auth_headers, employer_id):
        """Test enhanced dashboard endpoint (used by Dashboard page)"""
        if not employer_id:
            pytest.skip("No employer found")
        
        response = requests.get(f"{BASE_URL}/api/dashboard/enhanced/{employer_id}", headers=auth_headers)
        
        # Enhanced dashboard may return 200 or 404 (fallback to basic)
        if response.status_code == 200:
            data = response.json()
            print(f"Enhanced dashboard: workforce={data.get('workforce', {})}")
        else:
            # Try basic dashboard
            response = requests.get(f"{BASE_URL}/api/dashboard/{employer_id}", headers=auth_headers)
            assert response.status_code == 200, f"Dashboard failed: {response.text}"
            print("Using basic dashboard endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
