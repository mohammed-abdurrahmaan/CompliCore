"""
Test: Affordability Assignment Block Feature
Tests that POST /api/enrollment/plans/{plan_id}/assign-employees returns 422 
when plan is unaffordable for target employee(s).

Key test cases:
1. Backend returns 422 with unaffordable_employees array when plan is unaffordable
2. 422 response contains: message, unaffordable_employees (with name, annual_salary, 
   employee_monthly_cost, max_affordable_monthly, pct_of_income, threshold), and plan_cost
3. Assignment succeeds (200) when plan is affordable for the employee
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"

# Plan IDs from the review request
PLATINUM_PPO_ID = "16739425-5a63-45d9-9fde-418724747016"  # $744/mo EE cost, MV fail
GOLD_HMO_ID = "bc701f0b-29c4-4f37-ab42-ebb4f5fad085"  # $115/mo EE cost, MV pass
SILVER_PPO_ID = "ac820c3c-4409-4818-82c5-55c8ba523ce9"  # $100/mo EE cost, MV pass

# Employee ID
ADAM_MURPHY_ID = "87040c15-6773-43d8-89f0-eb96ec402e46"  # salary $49,782


class TestAffordabilityAssignmentBlock:
    """Test affordability check when assigning employees to plans"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        token = login_response.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        yield
        
        # Cleanup: unassign test employee from any plans we assigned
        try:
            for plan_id in [PLATINUM_PPO_ID, GOLD_HMO_ID, SILVER_PPO_ID]:
                self.session.post(
                    f"{BASE_URL}/api/enrollment/plans/{plan_id}/unassign-employees",
                    json={"employee_ids": [ADAM_MURPHY_ID]}
                )
        except:
            pass

    def test_platinum_ppo_returns_422_for_adam_murphy(self):
        """
        Platinum PPO ($744/mo) should return 422 for Adam Murphy ($49,782 salary)
        because $744/mo exceeds 9.96% of his income ($413.19/mo max affordable)
        """
        response = self.session.post(
            f"{BASE_URL}/api/enrollment/plans/{PLATINUM_PPO_ID}/assign-employees",
            json={"employee_ids": [ADAM_MURPHY_ID]}
        )
        
        # Should return 422 Unprocessable Entity
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        
        data = response.json()
        detail = data.get("detail", {})
        
        # Verify response structure
        assert "message" in detail, "Response should contain 'message'"
        assert "unaffordable_employees" in detail, "Response should contain 'unaffordable_employees'"
        assert "plan_cost" in detail, "Response should contain 'plan_cost'"
        
        # Verify plan_cost
        assert detail["plan_cost"] == 744, f"Expected plan_cost 744, got {detail['plan_cost']}"
        
        # Verify unaffordable_employees array
        unaffordable = detail["unaffordable_employees"]
        assert len(unaffordable) >= 1, "Should have at least 1 unaffordable employee"
        
        # Find Adam Murphy in the list
        adam = next((e for e in unaffordable if e.get("employee_id") == ADAM_MURPHY_ID), None)
        assert adam is not None, "Adam Murphy should be in unaffordable_employees list"
        
        # Verify Adam's data structure
        assert "name" in adam, "Employee should have 'name'"
        assert "annual_salary" in adam, "Employee should have 'annual_salary'"
        assert "employee_monthly_cost" in adam, "Employee should have 'employee_monthly_cost'"
        assert "max_affordable_monthly" in adam, "Employee should have 'max_affordable_monthly'"
        assert "pct_of_income" in adam, "Employee should have 'pct_of_income'"
        assert "threshold" in adam, "Employee should have 'threshold'"
        
        # Verify Adam's values
        assert adam["employee_monthly_cost"] == 744, f"Expected EE cost 744, got {adam['employee_monthly_cost']}"
        assert adam["threshold"] == 9.96, f"Expected threshold 9.96, got {adam['threshold']}"
        
        # Verify pct_of_income > threshold (unaffordable)
        assert adam["pct_of_income"] > adam["threshold"], \
            f"pct_of_income ({adam['pct_of_income']}) should be > threshold ({adam['threshold']})"
        
        print(f"✓ Platinum PPO correctly returns 422 for Adam Murphy")
        print(f"  - Plan cost: ${detail['plan_cost']}/mo")
        print(f"  - Adam's salary: ${adam['annual_salary']}")
        print(f"  - Max affordable: ${adam['max_affordable_monthly']}/mo")
        print(f"  - % of income: {adam['pct_of_income']}% (threshold: {adam['threshold']}%)")

    def test_silver_ppo_succeeds_for_adam_murphy(self):
        """
        Silver PPO ($100/mo) should succeed (200) for Adam Murphy ($49,782 salary)
        because $100/mo is within 9.96% of his income ($413.19/mo max affordable)
        """
        response = self.session.post(
            f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/assign-employees",
            json={"employee_ids": [ADAM_MURPHY_ID]}
        )
        
        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "assigned" in data, "Response should contain 'assigned' count"
        assert data["assigned"] >= 1, f"Expected at least 1 assigned, got {data['assigned']}"
        
        print(f"✓ Silver PPO correctly succeeds for Adam Murphy")
        print(f"  - Assigned: {data['assigned']} employee(s)")

    def test_gold_hmo_succeeds_for_adam_murphy(self):
        """
        Gold HMO ($115/mo) should succeed (200) for Adam Murphy ($49,782 salary)
        because $115/mo is within 9.96% of his income ($413.19/mo max affordable)
        """
        response = self.session.post(
            f"{BASE_URL}/api/enrollment/plans/{GOLD_HMO_ID}/assign-employees",
            json={"employee_ids": [ADAM_MURPHY_ID]}
        )
        
        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "assigned" in data, "Response should contain 'assigned' count"
        assert data["assigned"] >= 1, f"Expected at least 1 assigned, got {data['assigned']}"
        
        print(f"✓ Gold HMO correctly succeeds for Adam Murphy")
        print(f"  - Assigned: {data['assigned']} employee(s)")

    def test_422_response_message_format(self):
        """Verify the 422 error message is user-friendly and informative"""
        response = self.session.post(
            f"{BASE_URL}/api/enrollment/plans/{PLATINUM_PPO_ID}/assign-employees",
            json={"employee_ids": [ADAM_MURPHY_ID]}
        )
        
        assert response.status_code == 422
        
        detail = response.json().get("detail", {})
        message = detail.get("message", "")
        
        # Message should mention:
        # - Number of unaffordable employees
        # - Employee name(s)
        # - Plan cost
        # - ACA threshold
        assert "unaffordable" in message.lower(), "Message should mention 'unaffordable'"
        assert "$744" in message or "744" in message, "Message should mention plan cost"
        assert "9.96%" in message or "ACA" in message.upper(), "Message should mention ACA threshold"
        
        print(f"✓ 422 error message is informative: {message[:100]}...")

    def test_get_assigned_employees_endpoint(self):
        """Verify GET /api/enrollment/plans/{plan_id}/assigned-employees works"""
        response = self.session.get(
            f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/assigned-employees"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        
        print(f"✓ GET assigned-employees returns {len(data)} assignments")

    def test_employees_list_endpoint(self):
        """Verify GET /api/enrollment/employees-list/{employer_id} works"""
        response = self.session.get(
            f"{BASE_URL}/api/enrollment/employees-list/{EMPLOYER_ID}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Should have at least 1 employee"
        
        # Find Adam Murphy
        adam = next((e for e in data if e.get("id") == ADAM_MURPHY_ID), None)
        assert adam is not None, "Adam Murphy should be in employees list"
        
        print(f"✓ GET employees-list returns {len(data)} employees")
        print(f"  - Adam Murphy found: {adam.get('name')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
