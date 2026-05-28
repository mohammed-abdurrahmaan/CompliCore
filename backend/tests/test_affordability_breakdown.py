"""
Test: Per-Employee Affordability Breakdown in Compliance Check
Tests the new affordability.employees array with per-employee data
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"

# Plan IDs from context
SILVER_PPO_ID = "ac820c3c-4409-4818-82c5-55c8ba523ce9"  # $100/mo employee cost - should be 100% affordable
PLATINUM_PPO_ID = "16739425-5a63-45d9-9fde-418724747016"  # $744/mo employee cost - should have ~42.6% pass rate


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYER_EMAIL,
        "password": EMPLOYER_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Shared requests session with auth"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestAffordabilityEmployeeBreakdown:
    """Test per-employee affordability breakdown in compliance check"""

    def test_silver_ppo_compliance_check_returns_employees_array(self, api_client):
        """Silver PPO compliance check should return affordability.employees array"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200, f"Compliance check failed: {response.text}"
        
        data = response.json()
        assert "affordability" in data, "Response missing affordability object"
        affordability = data["affordability"]
        
        # Check employees array exists
        assert "employees" in affordability, "Affordability missing employees array"
        employees = affordability["employees"]
        assert isinstance(employees, list), "employees should be a list"
        assert len(employees) > 0, "employees array should not be empty"
        print(f"Silver PPO: Found {len(employees)} employees in affordability breakdown")

    def test_silver_ppo_employee_data_structure(self, api_client):
        """Each employee entry should have required fields"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        employees = data["affordability"]["employees"]
        
        # Check first employee has all required fields
        emp = employees[0]
        required_fields = ["employee_id", "name", "annual_salary", "monthly_threshold", 
                          "employee_monthly_cost", "pct_of_income", "affordable"]
        
        for field in required_fields:
            assert field in emp, f"Employee missing required field: {field}"
        
        # Validate data types
        assert isinstance(emp["annual_salary"], (int, float)), "annual_salary should be numeric"
        assert isinstance(emp["monthly_threshold"], (int, float)), "monthly_threshold should be numeric"
        assert isinstance(emp["employee_monthly_cost"], (int, float)), "employee_monthly_cost should be numeric"
        assert isinstance(emp["pct_of_income"], (int, float)), "pct_of_income should be numeric"
        assert isinstance(emp["affordable"], bool), "affordable should be boolean"
        
        print(f"Employee data structure validated: {emp['name']}, salary=${emp['annual_salary']}, affordable={emp['affordable']}")

    def test_silver_ppo_100_percent_affordable(self, api_client):
        """Silver PPO ($100/mo) should have 100% pass rate - all employees affordable"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        affordability = data["affordability"]
        
        # Check pass rate is 100%
        pass_rate = affordability.get("pass_rate", 0)
        affordable_count = affordability.get("affordable_for", 0)
        unaffordable_count = affordability.get("unaffordable_for", 0)
        total_checked = affordability.get("total_employees_checked", 0)
        
        print(f"Silver PPO: Pass rate={pass_rate}%, Affordable={affordable_count}, Unaffordable={unaffordable_count}")
        
        # Silver PPO at $100/mo should be affordable for all employees
        assert pass_rate == 100.0, f"Expected 100% pass rate for Silver PPO, got {pass_rate}%"
        assert unaffordable_count == 0, f"Expected 0 unaffordable employees, got {unaffordable_count}"
        assert affordable_count == total_checked, "All checked employees should be affordable"

    def test_silver_ppo_all_employees_marked_affordable(self, api_client):
        """All employees in Silver PPO breakdown should have affordable=True"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        employees = data["affordability"]["employees"]
        
        unaffordable = [e for e in employees if not e["affordable"]]
        assert len(unaffordable) == 0, f"Found {len(unaffordable)} unaffordable employees in Silver PPO"
        
        # Verify all have pct_of_income <= 9.96%
        for emp in employees:
            assert emp["pct_of_income"] <= 9.96, f"Employee {emp['name']} has pct_of_income {emp['pct_of_income']}% > 9.96%"
        
        print(f"All {len(employees)} employees are affordable for Silver PPO")

    def test_platinum_ppo_has_unaffordable_employees(self, api_client):
        """Platinum PPO ($744/mo) should have some unaffordable employees"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{PLATINUM_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        affordability = data["affordability"]
        
        unaffordable_count = affordability.get("unaffordable_for", 0)
        affordable_count = affordability.get("affordable_for", 0)
        pass_rate = affordability.get("pass_rate", 0)
        
        print(f"Platinum PPO: Pass rate={pass_rate}%, Affordable={affordable_count}, Unaffordable={unaffordable_count}")
        
        # Platinum PPO at $744/mo should have some unaffordable employees
        assert unaffordable_count > 0, "Expected some unaffordable employees for Platinum PPO"
        # Expected ~42.6% pass rate (27 unaffordable, 20 affordable)
        assert pass_rate < 100, f"Expected pass rate < 100% for Platinum PPO, got {pass_rate}%"

    def test_platinum_ppo_expected_pass_rate(self, api_client):
        """Platinum PPO should have approximately 42.6% pass rate"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{PLATINUM_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        affordability = data["affordability"]
        
        pass_rate = affordability.get("pass_rate", 0)
        unaffordable_count = affordability.get("unaffordable_for", 0)
        affordable_count = affordability.get("affordable_for", 0)
        
        # Expected: ~27 unaffordable, ~20 affordable (42.6% pass rate)
        # Allow some tolerance since employee data may vary
        print(f"Platinum PPO: {affordable_count} affordable, {unaffordable_count} unaffordable, {pass_rate}% pass rate")
        
        # Pass rate should be between 30% and 60% (allowing for data variation)
        assert 30 <= pass_rate <= 60, f"Expected pass rate between 30-60% for Platinum PPO, got {pass_rate}%"

    def test_employees_sorted_unaffordable_first(self, api_client):
        """Employees should be sorted: unaffordable first, then by pct_of_income descending"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{PLATINUM_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        employees = data["affordability"]["employees"]
        
        # Find first affordable employee
        first_affordable_idx = None
        for i, emp in enumerate(employees):
            if emp["affordable"]:
                first_affordable_idx = i
                break
        
        if first_affordable_idx is not None:
            # All employees before first affordable should be unaffordable
            for i in range(first_affordable_idx):
                assert not employees[i]["affordable"], f"Employee at index {i} should be unaffordable"
            
            # All employees after first affordable should be affordable
            for i in range(first_affordable_idx, len(employees)):
                assert employees[i]["affordable"], f"Employee at index {i} should be affordable"
        
        print(f"Employees correctly sorted: unaffordable first (first affordable at index {first_affordable_idx})")

    def test_pct_of_income_calculation(self, api_client):
        """Verify pct_of_income is calculated correctly"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        employees = data["affordability"]["employees"]
        ee_cost = data["affordability"]["employee_monthly_cost"]
        
        # Verify calculation for first employee
        emp = employees[0]
        annual_salary = emp["annual_salary"]
        annual_ee_cost = ee_cost * 12
        expected_pct = round((annual_ee_cost / annual_salary) * 100, 2)
        
        # Allow small rounding difference
        assert abs(emp["pct_of_income"] - expected_pct) < 0.1, \
            f"pct_of_income mismatch: expected {expected_pct}, got {emp['pct_of_income']}"
        
        print(f"pct_of_income calculation verified: {emp['pct_of_income']}% (expected {expected_pct}%)")

    def test_monthly_threshold_calculation(self, api_client):
        """Verify monthly_threshold is calculated correctly (9.96% of annual salary / 12)"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        employees = data["affordability"]["employees"]
        
        # Verify calculation for first employee
        emp = employees[0]
        annual_salary = emp["annual_salary"]
        expected_threshold = round((annual_salary * 0.0996) / 12, 2)
        
        # Allow small rounding difference
        assert abs(emp["monthly_threshold"] - expected_threshold) < 0.1, \
            f"monthly_threshold mismatch: expected {expected_threshold}, got {emp['monthly_threshold']}"
        
        print(f"monthly_threshold calculation verified: ${emp['monthly_threshold']}/mo (expected ${expected_threshold}/mo)")

    def test_affordable_flag_matches_threshold(self, api_client):
        """Verify affordable flag matches whether employee_monthly_cost <= monthly_threshold"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{PLATINUM_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        employees = data["affordability"]["employees"]
        ee_cost = data["affordability"]["employee_monthly_cost"]
        
        for emp in employees:
            expected_affordable = ee_cost <= emp["monthly_threshold"]
            assert emp["affordable"] == expected_affordable, \
                f"Employee {emp['name']}: affordable={emp['affordable']} but cost ${ee_cost} vs threshold ${emp['monthly_threshold']}"
        
        print(f"Affordable flag correctly matches threshold comparison for all {len(employees)} employees")


class TestAtRiskEmployeeLogic:
    """Test at-risk employee logic with compliant plans available"""

    def test_at_risk_returns_zero_with_compliant_plans(self, api_client):
        """At-risk employees should be 0 when employer has compliant MEC+MV plans"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        risk_alerts = data.get("risk_alerts", {})
        at_risk_count = risk_alerts.get("at_risk_employees", -1)
        
        print(f"At-risk employees: {at_risk_count}")
        
        # With compliant plans available (Silver PPO passes MEC+MV), at-risk should be 0
        # because offer is implicit via open enrollment
        assert at_risk_count == 0, f"Expected 0 at-risk employees with compliant plans, got {at_risk_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
