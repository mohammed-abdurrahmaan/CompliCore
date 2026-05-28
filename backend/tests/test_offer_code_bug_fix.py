"""
Test suite for Offer Code Bug Fix
Bug: Employees without plan assignments were incorrectly getting 1B instead of 1H
Fix: No explicit plan assignment = 1H (no offer made)
Only employees with actual plan_assignments entries should get non-1H offer codes
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "fajju2001@gmail.com"
TEST_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Create authenticated session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    })
    return session


class TestPlanAssignments:
    """Test plan assignments endpoint"""
    
    def test_get_plan_assignments_returns_only_two(self, api_client):
        """Verify only 2 employees have plan assignments (David Chen, Chase Cooper)"""
        response = api_client.get(f"{BASE_URL}/api/enrollment/assignments/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        assignments = response.json()
        assert isinstance(assignments, list)
        assert len(assignments) == 2, f"Expected 2 assignments, got {len(assignments)}"
        
        # Verify the assigned employees
        employee_names = [a["employee_name"] for a in assignments]
        assert "David Chen" in employee_names, "David Chen should have plan assignment"
        assert "Chase Cooper" in employee_names, "Chase Cooper should have plan assignment"
        
        # Verify plan is Standard EPO
        for assignment in assignments:
            assert assignment["plan_name"] == "Standard EPO"
            assert assignment["plan_category"] == "medical"


class TestEligibilityEngine:
    """Test eligibility engine and offer code calculation"""
    
    def test_run_eligibility_engine(self, api_client):
        """Re-run eligibility and verify only 2 employees get non-1H codes"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/eligibility/run/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_employees"] == 60
        assert data["eligible"] == 47  # FT employees
        assert data["ineligible"] == 13  # PT employees
        
        # Count offer codes
        results = data["results"]
        offer_codes = {}
        for r in results:
            code = r.get("offer_code", "unknown")
            offer_codes[code] = offer_codes.get(code, 0) + 1
        
        # Verify offer code distribution: 1B(2), 1H(58)
        assert offer_codes.get("1B", 0) == 2, f"Expected 2 employees with 1B, got {offer_codes.get('1B', 0)}"
        assert offer_codes.get("1H", 0) == 58, f"Expected 58 employees with 1H, got {offer_codes.get('1H', 0)}"
        
        # Verify only David Chen and Chase Cooper have non-1H codes
        non_1h = [r for r in results if r.get("offer_code") != "1H"]
        assert len(non_1h) == 2
        non_1h_names = [r["employee_name"] for r in non_1h]
        assert "David Chen" in non_1h_names
        assert "Chase Cooper" in non_1h_names
    
    def test_get_eligibility_results(self, api_client):
        """Verify eligibility results show correct offer code distribution"""
        response = api_client.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 60
        assert data["eligible"] == 47
        assert data["ineligible"] == 13
        
        # Count offer codes
        results = data["results"]
        offer_codes = {}
        for r in results:
            code = r.get("offer_code", "unknown")
            offer_codes[code] = offer_codes.get(code, 0) + 1
        
        # Verify: 1B(2), 1H(58)
        assert offer_codes.get("1B", 0) == 2
        assert offer_codes.get("1H", 0) == 58


class TestIRSForms:
    """Test IRS form generation with bug fix"""
    
    def test_1095c_forms_only_two_generated(self, api_client):
        """Verify only 2 1095-C forms generated (not 47)"""
        response = api_client.get(f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/2026")
        assert response.status_code == 200
        
        data = response.json()
        forms = data.get("forms", [])
        count = data.get("count", len(forms))
        
        assert count == 2, f"Expected 2 1095-C forms, got {count}"
        
        # Verify the forms are for David Chen and Chase Cooper
        employee_names = [f["part1"]["employee_name"] for f in forms]
        assert "David Chen" in employee_names
        assert "Chase Cooper" in employee_names
        
        # Verify Line 14 codes are 1B
        for form in forms:
            line14 = form["part2"]["line14_all_year"]
            assert line14 == "1B", f"Expected 1B, got {line14}"
    
    def test_1094c_form_still_works(self, api_client):
        """Verify 1094-C form generation still works"""
        response = api_client.get(f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/2026")
        assert response.status_code == 200
        
        data = response.json()
        assert data["form_type"] == "1094-C"
        assert data["tax_year"] == 2026
        
        # Verify employer info
        part1 = data["part1"]
        assert part1["employer_name"] == "acme Corp"
        assert part1["employer_ein"] == "246542654333"
        
        # Verify Part II has FTE data
        part2 = data["part2"]
        assert part2["total_fte"] == 57.25
    
    def test_irs_summary(self, api_client):
        """Verify IRS summary shows correct data"""
        response = api_client.get(f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/2026")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_employees"] == 60
        assert data["full_time_employees"] == 47
        assert data["total_fte"] == 57.25
        assert data["is_ale"] == True
        
        # Key assertion: forms_1095c_count should be 2 (not 47)
        assert data["forms_1095c_count"] == 2, f"Expected 2 1095-C forms, got {data['forms_1095c_count']}"


class TestOfferCodeLogic:
    """Test the core offer code logic"""
    
    def test_ft_employee_without_assignment_gets_1h(self, api_client):
        """Full-time employee without plan assignment should get 1H"""
        response = api_client.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        results = response.json()["results"]
        
        # Find a FT employee who is NOT David Chen or Chase Cooper
        ft_without_assignment = None
        for r in results:
            if r.get("is_full_time") and r["employee_name"] not in ["David Chen", "Chase Cooper"]:
                ft_without_assignment = r
                break
        
        assert ft_without_assignment is not None, "Should find FT employee without assignment"
        assert ft_without_assignment["offer_code"] == "1H", \
            f"FT employee without assignment should have 1H, got {ft_without_assignment['offer_code']}"
    
    def test_pt_employee_gets_1h(self, api_client):
        """Part-time employee should always get 1H"""
        response = api_client.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        results = response.json()["results"]
        
        # Find PT employees
        pt_employees = [r for r in results if not r.get("is_full_time")]
        assert len(pt_employees) == 13, f"Expected 13 PT employees, got {len(pt_employees)}"
        
        # All PT employees should have 1H
        for emp in pt_employees:
            assert emp["offer_code"] == "1H", \
                f"PT employee {emp['employee_name']} should have 1H, got {emp['offer_code']}"
    
    def test_employee_with_assignment_gets_non_1h(self, api_client):
        """Employee with plan assignment should get non-1H code"""
        response = api_client.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        results = response.json()["results"]
        
        # Find David Chen and Chase Cooper
        david = next((r for r in results if r["employee_name"] == "David Chen"), None)
        chase = next((r for r in results if r["employee_name"] == "Chase Cooper"), None)
        
        assert david is not None, "David Chen should be in results"
        assert chase is not None, "Chase Cooper should be in results"
        
        assert david["offer_code"] == "1B", f"David Chen should have 1B, got {david['offer_code']}"
        assert chase["offer_code"] == "1B", f"Chase Cooper should have 1B, got {chase['offer_code']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
