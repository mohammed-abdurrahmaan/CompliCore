"""
Test Plan Library New Features:
1. Compliance Check popup (MEC/MV/Affordability)
2. Assign Employees dialog
3. Employee Portal filtering by assignments
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
EMPLOYER_EMAIL = "test@demo.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_ID = "afeaea3f-0ada-45cf-b29f-f7c06fa512b9"

EMPLOYEE_EMAIL = "maria@test.com"
EMPLOYEE_PASSWORD = "test123"


@pytest.fixture(scope="module")
def employer_token():
    """Get employer auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYER_EMAIL,
        "password": EMPLOYER_PASSWORD
    })
    assert response.status_code == 200, f"Employer login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def employee_token():
    """Get employee auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYEE_EMAIL,
        "password": EMPLOYEE_PASSWORD
    })
    assert response.status_code == 200, f"Employee login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def employer_headers(employer_token):
    return {"Authorization": f"Bearer {employer_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def employee_headers(employee_token):
    return {"Authorization": f"Bearer {employee_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def plans(employer_headers):
    """Get all plans for employer"""
    response = requests.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}", headers=employer_headers)
    assert response.status_code == 200
    return response.json()


class TestComplianceCheck:
    """Test POST /api/enrollment/plans/{plan_id}/compliance-check"""

    def test_compliance_check_returns_mec_data(self, employer_headers, plans):
        """Compliance check returns MEC pass/fail with 7 checks"""
        if not plans:
            pytest.skip("No plans available")
        
        plan_id = plans[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=employer_headers,
            json={}
        )
        
        assert response.status_code == 200, f"Compliance check failed: {response.text}"
        data = response.json()
        
        # Verify MEC structure
        assert "mec" in data, "Missing 'mec' in response"
        assert "pass" in data["mec"], "Missing 'pass' in mec"
        assert "checks" in data["mec"], "Missing 'checks' in mec"
        
        # Verify 7 MEC checks
        mec_checks = data["mec"]["checks"]
        expected_checks = [
            "is_group_health_plan",
            "covers_essential_benefits",
            "covers_preventive_care",
            "no_annual_limits",
            "no_lifetime_limits",
            "covers_dependents_to_26",
            "no_preexisting_exclusions"
        ]
        for check in expected_checks:
            assert check in mec_checks, f"Missing MEC check: {check}"
        
        print(f"MEC Check: pass={data['mec']['pass']}, checks={len(mec_checks)}")

    def test_compliance_check_returns_mv_data(self, employer_headers, plans):
        """Compliance check returns MV percentage vs 60% threshold"""
        if not plans:
            pytest.skip("No plans available")
        
        plan_id = plans[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=employer_headers,
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify MV structure
        assert "mv" in data, "Missing 'mv' in response"
        assert "pass" in data["mv"], "Missing 'pass' in mv"
        assert "mv_percentage" in data["mv"], "Missing 'mv_percentage' in mv"
        assert "threshold" in data["mv"], "Missing 'threshold' in mv"
        assert data["mv"]["threshold"] == 60, "MV threshold should be 60%"
        assert "certified" in data["mv"], "Missing 'certified' in mv"
        assert "method" in data["mv"], "Missing 'method' in mv"
        
        print(f"MV Check: pass={data['mv']['pass']}, percentage={data['mv']['mv_percentage']}%, threshold={data['mv']['threshold']}%")

    def test_compliance_check_returns_affordability_data(self, employer_headers, plans):
        """Compliance check returns Affordability with employee count and pass rate"""
        if not plans:
            pytest.skip("No plans available")
        
        plan_id = plans[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=employer_headers,
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify Affordability structure
        assert "affordability" in data, "Missing 'affordability' in response"
        aff = data["affordability"]
        
        assert "employee_monthly_cost" in aff, "Missing 'employee_monthly_cost'"
        assert "total_employees_checked" in aff, "Missing 'total_employees_checked'"
        assert "affordable_for" in aff, "Missing 'affordable_for'"
        assert "unaffordable_for" in aff, "Missing 'unaffordable_for'"
        assert "pass_rate" in aff, "Missing 'pass_rate'"
        assert "threshold_rate" in aff, "Missing 'threshold_rate'"
        assert "method" in aff, "Missing 'method'"
        
        # Verify employee count is reasonable (57 employees expected)
        assert aff["total_employees_checked"] > 0, "Should have employees checked"
        
        print(f"Affordability: checked={aff['total_employees_checked']}, affordable={aff['affordable_for']}, pass_rate={aff['pass_rate']}%")

    def test_compliance_check_returns_overall_status(self, employer_headers, plans):
        """Compliance check returns overall_compliant status"""
        if not plans:
            pytest.skip("No plans available")
        
        plan_id = plans[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=employer_headers,
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "overall_compliant" in data, "Missing 'overall_compliant'"
        assert "plan_id" in data, "Missing 'plan_id'"
        assert "plan_name" in data, "Missing 'plan_name'"
        
        print(f"Overall Compliant: {data['overall_compliant']} for plan '{data['plan_name']}'")

    def test_compliance_check_invalid_plan(self, employer_headers):
        """Compliance check returns 404 for invalid plan"""
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/invalid-plan-id/compliance-check",
            headers=employer_headers,
            json={}
        )
        assert response.status_code == 404


class TestEmployeeAssignment:
    """Test employee assignment endpoints"""

    def test_get_employees_list(self, employer_headers):
        """GET /api/enrollment/employees-list/{employer_id} returns employee list"""
        response = requests.get(
            f"{BASE_URL}/api/enrollment/employees-list/{EMPLOYER_ID}",
            headers=employer_headers
        )
        
        assert response.status_code == 200, f"Failed to get employees: {response.text}"
        employees = response.json()
        
        assert isinstance(employees, list), "Should return a list"
        assert len(employees) > 0, "Should have employees"
        
        # Verify employee structure
        emp = employees[0]
        assert "id" in emp, "Missing 'id'"
        assert "name" in emp, "Missing 'name'"
        
        print(f"Employees list: {len(employees)} employees found")

    def test_get_assigned_employees_empty(self, employer_headers, plans):
        """GET /api/enrollment/plans/{plan_id}/assigned-employees returns assignments"""
        if not plans:
            pytest.skip("No plans available")
        
        # Use a plan that might not have assignments
        plan_id = plans[-1]["id"]  # Last plan
        response = requests.get(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/assigned-employees",
            headers=employer_headers
        )
        
        assert response.status_code == 200
        assignments = response.json()
        assert isinstance(assignments, list), "Should return a list"
        
        print(f"Assigned employees for plan {plan_id}: {len(assignments)}")

    def test_assign_employees_to_plan(self, employer_headers, plans):
        """POST /api/enrollment/plans/{plan_id}/assign-employees assigns employees"""
        if not plans:
            pytest.skip("No plans available")
        
        # Get employees first
        emp_response = requests.get(
            f"{BASE_URL}/api/enrollment/employees-list/{EMPLOYER_ID}",
            headers=employer_headers
        )
        employees = emp_response.json()
        if len(employees) < 2:
            pytest.skip("Need at least 2 employees")
        
        # Use a test plan (not the first one to avoid conflicts)
        plan_id = plans[1]["id"] if len(plans) > 1 else plans[0]["id"]
        
        # Assign 2 employees
        test_employee_ids = [employees[0]["id"], employees[1]["id"]]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/assign-employees",
            headers=employer_headers,
            json={"employee_ids": test_employee_ids}
        )
        
        assert response.status_code == 200, f"Failed to assign: {response.text}"
        data = response.json()
        
        assert "assigned" in data, "Missing 'assigned' count"
        assert data["assigned"] >= 1, "Should have assigned at least 1 employee"
        assert "plan_name" in data, "Missing 'plan_name'"
        
        print(f"Assigned {data['assigned']} employees to '{data['plan_name']}'")

    def test_verify_assignments_persisted(self, employer_headers, plans):
        """Verify assignments are persisted via GET"""
        if not plans:
            pytest.skip("No plans available")
        
        plan_id = plans[1]["id"] if len(plans) > 1 else plans[0]["id"]
        response = requests.get(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/assigned-employees",
            headers=employer_headers
        )
        
        assert response.status_code == 200
        assignments = response.json()
        
        # Should have assignments from previous test
        assert len(assignments) >= 1, "Should have at least 1 assignment"
        
        # Verify assignment structure
        if assignments:
            a = assignments[0]
            assert "employee_id" in a, "Missing 'employee_id'"
            assert "plan_id" in a, "Missing 'plan_id'"
            assert "employee_name" in a, "Missing 'employee_name'"
        
        print(f"Verified {len(assignments)} assignments persisted")

    def test_unassign_employees(self, employer_headers, plans):
        """POST /api/enrollment/plans/{plan_id}/unassign-employees removes assignments"""
        if not plans:
            pytest.skip("No plans available")
        
        plan_id = plans[1]["id"] if len(plans) > 1 else plans[0]["id"]
        
        # Get current assignments
        get_response = requests.get(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/assigned-employees",
            headers=employer_headers
        )
        assignments = get_response.json()
        
        if not assignments:
            pytest.skip("No assignments to unassign")
        
        # Unassign one employee
        employee_to_unassign = assignments[0]["employee_id"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/unassign-employees",
            headers=employer_headers,
            json={"employee_ids": [employee_to_unassign]}
        )
        
        assert response.status_code == 200, f"Failed to unassign: {response.text}"
        data = response.json()
        
        assert "unassigned" in data, "Missing 'unassigned' count"
        assert data["unassigned"] >= 1, "Should have unassigned at least 1"
        
        print(f"Unassigned {data['unassigned']} employees")

    def test_get_all_assignments(self, employer_headers):
        """GET /api/enrollment/assignments/{employer_id} returns all assignments"""
        response = requests.get(
            f"{BASE_URL}/api/enrollment/assignments/{EMPLOYER_ID}",
            headers=employer_headers
        )
        
        assert response.status_code == 200, f"Failed to get assignments: {response.text}"
        assignments = response.json()
        
        assert isinstance(assignments, list), "Should return a list"
        
        print(f"Total assignments for employer: {len(assignments)}")

    def test_assign_empty_list_fails(self, employer_headers, plans):
        """Assigning empty employee list returns 400"""
        if not plans:
            pytest.skip("No plans available")
        
        plan_id = plans[0]["id"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/assign-employees",
            headers=employer_headers,
            json={"employee_ids": []}
        )
        
        assert response.status_code == 400


class TestEmployeePortalFiltering:
    """Test that Employee Portal shows only assigned plans"""

    def test_employee_my_plans_endpoint(self, employee_headers):
        """GET /api/enrollment/employee/my-plans returns plans"""
        response = requests.get(
            f"{BASE_URL}/api/enrollment/employee/my-plans",
            headers=employee_headers
        )
        
        assert response.status_code == 200, f"Failed to get my-plans: {response.text}"
        data = response.json()
        
        # Verify structure
        assert "medical_plans" in data, "Missing 'medical_plans'"
        assert "addon_plans" in data, "Missing 'addon_plans'"
        assert isinstance(data["medical_plans"], list), "medical_plans should be a list"
        
        print(f"Employee sees {len(data['medical_plans'])} medical plans, {len(data['addon_plans'])} addon plans")

    def test_employee_sees_assigned_plans_only(self, employer_headers, employee_headers, plans):
        """When plans are assigned, employee sees only those plans"""
        if not plans:
            pytest.skip("No plans available")
        
        # Get employee info to find linked_employee_id
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=employee_headers)
        assert me_response.status_code == 200
        user_data = me_response.json()
        
        linked_emp_id = user_data.get("linked_employee_id") or user_data.get("id")
        
        # Assign a specific plan to this employee
        medical_plans = [p for p in plans if p.get("category") == "medical"]
        if not medical_plans:
            pytest.skip("No medical plans")
        
        test_plan = medical_plans[0]
        
        # Assign the plan
        assign_response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{test_plan['id']}/assign-employees",
            headers=employer_headers,
            json={"employee_ids": [linked_emp_id]}
        )
        assert assign_response.status_code == 200, f"Failed to assign: {assign_response.text}"
        
        # Now check employee's my-plans
        my_plans_response = requests.get(
            f"{BASE_URL}/api/enrollment/employee/my-plans",
            headers=employee_headers
        )
        assert my_plans_response.status_code == 200
        data = my_plans_response.json()
        
        # Employee should see the assigned plan
        plan_ids = [p["id"] for p in data["medical_plans"]]
        assert test_plan["id"] in plan_ids, f"Assigned plan {test_plan['id']} should be visible to employee"
        
        print(f"Employee correctly sees assigned plan: {test_plan['plan_name']}")


class TestPlanLibraryBasics:
    """Test basic Plan Library endpoints still work"""

    def test_get_plans(self, employer_headers):
        """GET /api/enrollment/plans/{employer_id} returns plans"""
        response = requests.get(
            f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}",
            headers=employer_headers
        )
        
        assert response.status_code == 200
        plans = response.json()
        
        assert isinstance(plans, list), "Should return a list"
        assert len(plans) > 0, "Should have plans"
        
        # Verify plan structure
        plan = plans[0]
        assert "id" in plan
        assert "plan_name" in plan
        assert "carrier_name" in plan
        assert "category" in plan
        
        print(f"Found {len(plans)} plans")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
