"""
Test HHS MV Calculator Implementation
Tests the dynamic HHS MV Calculator that calculates actuarial value from plan parameters.
Uses standard population costs ($12,500) across 8 service categories.
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"

# Plan IDs from seed data
PLAN_IDS = {
    "silver_ppo": "ac820c3c-4409-4818-82c5-55c8ba523ce9",
    "gold_hmo": "bc701f0b-29c4-4f37-ab42-ebb4f5fad085",
    "bronze_hdhp": "46ef441c-ab24-4a2d-a583-79f29ada5dcf",
    "platinum_ppo": "16739425-5a63-45d9-9fde-418724747016",
    "standard_epo": "70cb740e-d7c1-4798-8ddc-035bfe79bbd5",
}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for employer."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYER_EMAIL,
        "password": EMPLOYER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Return headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestHHSMVCalculatorBackend:
    """Test HHS MV Calculator compliance check endpoint."""

    def test_silver_ppo_mv_calculation(self, headers):
        """Silver PPO should have MV ~64% based on HHS calculation."""
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        # Check MV section exists
        assert "mv" in data, "Response missing 'mv' section"
        mv = data["mv"]
        
        # Check MV percentage is calculated (expected ~64% based on plan params)
        assert "mv_percentage" in mv, "Missing mv_percentage"
        mv_pct = mv["mv_percentage"]
        print(f"Silver PPO MV%: {mv_pct}")
        
        # Silver PPO should pass MV (>= 60%)
        assert mv_pct >= 60, f"Silver PPO MV {mv_pct}% should be >= 60%"
        
        # Check method is HHS MV Calculator
        assert mv.get("method") == "HHS MV Calculator", f"Method should be 'HHS MV Calculator', got {mv.get('method')}"
        
        # Check employer contribution pass
        assert mv.get("employer_contribution_pass") == True, "Silver PPO employer contribution should pass"
        
        # Overall MV should pass
        assert mv.get("pass") == True, "Silver PPO overall MV should pass"

    def test_gold_hmo_mv_calculation(self, headers):
        """Gold HMO should have MV ~76% based on HHS calculation."""
        plan_id = PLAN_IDS["gold_hmo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        mv = data["mv"]
        
        mv_pct = mv["mv_percentage"]
        print(f"Gold HMO MV%: {mv_pct}")
        
        # Gold HMO should have higher MV due to lower deductible/coinsurance
        assert mv_pct >= 60, f"Gold HMO MV {mv_pct}% should be >= 60%"
        
        # Check method
        assert mv.get("method") == "HHS MV Calculator"
        
        # Overall should pass
        assert mv.get("pass") == True, "Gold HMO overall MV should pass"

    def test_bronze_hdhp_mv_calculation(self, headers):
        """Bronze HDHP should have MV ~47% and FAIL due to high deductible."""
        plan_id = PLAN_IDS["bronze_hdhp"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        mv = data["mv"]
        
        mv_pct = mv["mv_percentage"]
        print(f"Bronze HDHP MV%: {mv_pct}")
        
        # Bronze HDHP with $3,500 deductible and 30% coinsurance should fail MV
        # Expected ~47% based on HHS calculation
        assert mv_pct < 60, f"Bronze HDHP MV {mv_pct}% should be < 60% (expected ~47%)"
        
        # Check actuarial_pass is False
        assert mv.get("actuarial_pass") == False, "Bronze HDHP actuarial check should fail"
        
        # Overall MV should fail
        assert mv.get("pass") == False, "Bronze HDHP overall MV should fail"

    def test_platinum_ppo_mv_calculation(self, headers):
        """Platinum PPO should have high MV (~76%) but FAIL due to low employer contribution (0.8%)."""
        plan_id = PLAN_IDS["platinum_ppo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        mv = data["mv"]
        
        mv_pct = mv["mv_percentage"]
        er_pct = mv.get("employer_contribution_pct", 0)
        print(f"Platinum PPO MV%: {mv_pct}, ER Contrib%: {er_pct}")
        
        # Platinum PPO has $50M deductible but OOP max of $3,000 caps costs
        # So actuarial value should be high (~76%)
        assert mv_pct >= 60, f"Platinum PPO MV {mv_pct}% should be >= 60%"
        
        # But employer contribution is only 0.8% (fails 60% threshold)
        assert er_pct < 60, f"Platinum PPO ER contrib {er_pct}% should be < 60%"
        
        # Actuarial passes but employer contribution fails
        assert mv.get("actuarial_pass") == True, "Platinum PPO actuarial check should pass"
        assert mv.get("employer_contribution_pass") == False, "Platinum PPO employer contribution should fail"
        
        # Overall MV should fail
        assert mv.get("pass") == False, "Platinum PPO overall MV should fail"

    def test_standard_epo_mv_calculation(self, headers):
        """Standard EPO should have MV ~68% and pass."""
        plan_id = PLAN_IDS["standard_epo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        mv = data["mv"]
        
        mv_pct = mv["mv_percentage"]
        print(f"Standard EPO MV%: {mv_pct}")
        
        # Standard EPO should pass MV
        assert mv_pct >= 60, f"Standard EPO MV {mv_pct}% should be >= 60%"
        
        # Overall should pass
        assert mv.get("pass") == True, "Standard EPO overall MV should pass"


class TestHHSMVResponseStructure:
    """Test that MV response includes all required HHS Calculator fields."""

    def test_mv_response_includes_category_breakdown(self, headers):
        """MV response should include category_breakdown array with 8 service categories."""
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        mv = data["mv"]
        
        # Check category_breakdown exists and has 8 items
        assert "category_breakdown" in mv, "Missing category_breakdown"
        categories = mv["category_breakdown"]
        assert isinstance(categories, list), "category_breakdown should be a list"
        assert len(categories) == 8, f"Expected 8 categories, got {len(categories)}"
        
        # Check each category has required fields
        expected_fields = ["category", "total_cost", "copays", "plan_pays", "employee_cost"]
        for cat in categories:
            for field in expected_fields:
                assert field in cat, f"Category missing field: {field}"
        
        # Check category names
        expected_categories = ["Inpatient", "Outpatient", "Physician", "Specialist", "ER", "Generic Rx", "Brand Rx", "Lab/Imaging"]
        actual_categories = [c["category"] for c in categories]
        for expected in expected_categories:
            assert expected in actual_categories, f"Missing category: {expected}"

    def test_mv_response_includes_premium_analysis(self, headers):
        """MV response should include premium_analysis object."""
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        mv = data["mv"]
        
        # Check premium_analysis exists
        assert "premium_analysis" in mv, "Missing premium_analysis"
        pa = mv["premium_analysis"]
        
        # Check required fields
        assert "total_monthly_premium" in pa, "Missing total_monthly_premium"
        assert "employer_contribution" in pa, "Missing employer_contribution"
        assert "employee_premium" in pa, "Missing employee_premium"
        assert "employer_pct" in pa, "Missing employer_pct"
        assert "employer_contribution_pass" in pa, "Missing employer_contribution_pass"

    def test_mv_response_includes_plan_parameters(self, headers):
        """MV response should include plan_parameters object."""
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        mv = data["mv"]
        
        # Check plan_parameters exists
        assert "plan_parameters" in mv, "Missing plan_parameters"
        pp = mv["plan_parameters"]
        
        # Check required fields
        assert "deductible" in pp, "Missing deductible"
        assert "coinsurance" in pp, "Missing coinsurance"
        assert "oop_max" in pp, "Missing oop_max"

    def test_mv_response_includes_cost_analysis(self, headers):
        """MV response should include total_allowed_cost, plan_pays, member_pays."""
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        mv = data["mv"]
        
        # Check cost analysis fields
        assert "total_allowed_cost" in mv, "Missing total_allowed_cost"
        assert mv["total_allowed_cost"] == 12500, f"Expected total_allowed_cost=12500, got {mv['total_allowed_cost']}"
        
        assert "plan_pays" in mv, "Missing plan_pays"
        assert "member_pays" in mv, "Missing member_pays"
        
        # Verify plan_pays + member_pays = total_allowed_cost
        total = mv["plan_pays"] + mv["member_pays"]
        assert abs(total - 12500) < 1, f"plan_pays + member_pays should equal 12500, got {total}"

    def test_mv_response_includes_employer_contribution_fields(self, headers):
        """MV response should include employer_contribution_pct and employer_contribution_pass."""
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        mv = data["mv"]
        
        # Check employer contribution fields
        assert "employer_contribution_pct" in mv, "Missing employer_contribution_pct"
        assert "employer_contribution_pass" in mv, "Missing employer_contribution_pass"
        
        # employer_contribution_pct should be a number
        assert isinstance(mv["employer_contribution_pct"], (int, float)), "employer_contribution_pct should be numeric"
        
        # employer_contribution_pass should be boolean
        assert isinstance(mv["employer_contribution_pass"], bool), "employer_contribution_pass should be boolean"


class TestMVPersistence:
    """Test that compliance check updates stored mv_percentage in DB."""

    def test_compliance_check_updates_stored_mv(self, headers):
        """After compliance check, the plan's mv_percentage should be updated in DB."""
        plan_id = PLAN_IDS["silver_ppo"]
        
        # Run compliance check
        response = requests.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check", headers=headers)
        assert response.status_code == 200
        calculated_mv = response.json()["mv"]["mv_percentage"]
        
        # Get plan from library
        response = requests.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200
        plans = response.json()
        
        # Find Silver PPO
        silver_ppo = next((p for p in plans if p["id"] == plan_id), None)
        assert silver_ppo is not None, "Silver PPO not found in plan library"
        
        # Check mv_percentage is updated
        stored_mv = silver_ppo.get("mv_percentage")
        print(f"Calculated MV: {calculated_mv}, Stored MV: {stored_mv}")
        assert stored_mv == calculated_mv, f"Stored MV {stored_mv} should match calculated MV {calculated_mv}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
