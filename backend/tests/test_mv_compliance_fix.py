"""
Test MV (Minimum Value) Compliance Fix
Bug: MV check was incorrectly passing plans where employer contribution was far below 60% of total premium.
Fix: MV now requires BOTH actuarial value >= 60% AND employer contribution >= 60% of total premium.

Test Plans:
- Platinum PPO: mv=90%, er_contrib=$6/$750 = 0.8% → SHOULD FAIL MV (employer_contribution_pass: false)
- Silver PPO: mv=62%, er_contrib=$350/$450 = 77.8% → SHOULD PASS MV
- Gold HMO: mv=78%, er_contrib=$465/$580 = 80.2% → SHOULD PASS MV
- Bronze HDHP: mv=89%, er_contrib=$250/$320 = 78.1% → SHOULD PASS MV
- Standard EPO: mv=68%, er_contrib=$340/$420 = 81% → SHOULD PASS MV
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Plan IDs from the employer's plan library
PLAN_IDS = {
    "platinum_ppo": "16739425-5a63-45d9-9fde-418724747016",  # mv=90%, er=0.8% → FAIL
    "silver_ppo": "ac820c3c-4409-4818-82c5-55c8ba523ce9",    # mv=62%, er=77.8% → PASS
    "gold_hmo": "bc701f0b-29c4-4f37-ab42-ebb4f5fad085",      # mv=78%, er=80.2% → PASS
    "bronze_hdhp": "46ef441c-ab24-4a2d-a583-79f29ada5dcf",   # mv=89%, er=78.1% → PASS
    "standard_epo": "70cb740e-d7c1-4798-8ddc-035bfe79bbd5",  # mv=68%, er=81% → PASS
}

EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for employer"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "fajju2001@gmail.com", "password": "test123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json().get("token")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestMVComplianceFix:
    """Test MV compliance check with employer contribution validation"""

    def test_platinum_ppo_should_fail_mv(self, auth_headers):
        """
        Platinum PPO: mv=90%, employer_contrib=$6/$750 = 0.8%
        Expected: MV FAIL because employer contribution < 60%
        """
        plan_id = PLAN_IDS["platinum_ppo"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance check failed: {response.text}"
        
        data = response.json()
        mv = data.get("mv", {})
        
        # MV should FAIL overall
        assert mv.get("pass") == False, f"Platinum PPO MV should FAIL but got pass={mv.get('pass')}"
        
        # Actuarial value should pass (90% >= 60%)
        assert mv.get("actuarial_pass") == True, f"Actuarial should pass (90% >= 60%) but got {mv.get('actuarial_pass')}"
        
        # Employer contribution should FAIL (0.8% < 60%)
        assert mv.get("employer_contribution_pass") == False, f"Employer contribution should FAIL but got {mv.get('employer_contribution_pass')}"
        
        # Verify employer contribution percentage is calculated correctly
        er_pct = mv.get("employer_contribution_pct", 0)
        assert er_pct < 10, f"Employer contribution should be ~0.8% but got {er_pct}%"
        
        print(f"✓ Platinum PPO MV check: pass={mv.get('pass')}, actuarial_pass={mv.get('actuarial_pass')}, employer_contribution_pass={mv.get('employer_contribution_pass')}, er_pct={er_pct}%")

    def test_silver_ppo_should_pass_mv(self, auth_headers):
        """
        Silver PPO: mv=62%, employer_contrib=$350/$450 = 77.8%
        Expected: MV PASS (both actuarial >= 60% and employer contrib >= 60%)
        """
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance check failed: {response.text}"
        
        data = response.json()
        mv = data.get("mv", {})
        
        # MV should PASS overall
        assert mv.get("pass") == True, f"Silver PPO MV should PASS but got pass={mv.get('pass')}"
        
        # Actuarial value should pass (62% >= 60%)
        assert mv.get("actuarial_pass") == True, f"Actuarial should pass (62% >= 60%) but got {mv.get('actuarial_pass')}"
        
        # Employer contribution should pass (77.8% >= 60%)
        assert mv.get("employer_contribution_pass") == True, f"Employer contribution should pass (77.8% >= 60%) but got {mv.get('employer_contribution_pass')}"
        
        er_pct = mv.get("employer_contribution_pct", 0)
        assert er_pct >= 60, f"Employer contribution should be ~77.8% but got {er_pct}%"
        
        print(f"✓ Silver PPO MV check: pass={mv.get('pass')}, actuarial_pass={mv.get('actuarial_pass')}, employer_contribution_pass={mv.get('employer_contribution_pass')}, er_pct={er_pct}%")

    def test_gold_hmo_should_pass_mv(self, auth_headers):
        """
        Gold HMO: mv=78%, employer_contrib=$465/$580 = 80.2%
        Expected: MV PASS
        """
        plan_id = PLAN_IDS["gold_hmo"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance check failed: {response.text}"
        
        data = response.json()
        mv = data.get("mv", {})
        
        assert mv.get("pass") == True, f"Gold HMO MV should PASS but got pass={mv.get('pass')}"
        assert mv.get("actuarial_pass") == True, f"Actuarial should pass (78% >= 60%)"
        assert mv.get("employer_contribution_pass") == True, f"Employer contribution should pass (80.2% >= 60%)"
        
        print(f"✓ Gold HMO MV check: pass={mv.get('pass')}, er_pct={mv.get('employer_contribution_pct')}%")

    def test_bronze_hdhp_should_pass_mv(self, auth_headers):
        """
        Bronze HDHP: mv=89%, employer_contrib=$250/$320 = 78.1%
        Expected: MV PASS
        """
        plan_id = PLAN_IDS["bronze_hdhp"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance check failed: {response.text}"
        
        data = response.json()
        mv = data.get("mv", {})
        
        assert mv.get("pass") == True, f"Bronze HDHP MV should PASS but got pass={mv.get('pass')}"
        assert mv.get("actuarial_pass") == True, f"Actuarial should pass (89% >= 60%)"
        assert mv.get("employer_contribution_pass") == True, f"Employer contribution should pass (78.1% >= 60%)"
        
        print(f"✓ Bronze HDHP MV check: pass={mv.get('pass')}, er_pct={mv.get('employer_contribution_pct')}%")

    def test_standard_epo_should_pass_mv(self, auth_headers):
        """
        Standard EPO: mv=68%, employer_contrib=$340/$420 = 81%
        Expected: MV PASS
        """
        plan_id = PLAN_IDS["standard_epo"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Compliance check failed: {response.text}"
        
        data = response.json()
        mv = data.get("mv", {})
        
        assert mv.get("pass") == True, f"Standard EPO MV should PASS but got pass={mv.get('pass')}"
        assert mv.get("actuarial_pass") == True, f"Actuarial should pass (68% >= 60%)"
        assert mv.get("employer_contribution_pass") == True, f"Employer contribution should pass (81% >= 60%)"
        
        print(f"✓ Standard EPO MV check: pass={mv.get('pass')}, er_pct={mv.get('employer_contribution_pct')}%")

    def test_mv_response_includes_new_fields(self, auth_headers):
        """
        Verify MV response includes the new fields:
        - employer_contribution_pct
        - employer_contribution_pass
        - actuarial_pass
        """
        plan_id = PLAN_IDS["platinum_ppo"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        mv = data.get("mv", {})
        
        # Check all required fields exist
        assert "employer_contribution_pct" in mv, "Missing employer_contribution_pct field"
        assert "employer_contribution_pass" in mv, "Missing employer_contribution_pass field"
        assert "actuarial_pass" in mv, "Missing actuarial_pass field"
        assert "pass" in mv, "Missing pass field"
        assert "mv_percentage" in mv, "Missing mv_percentage field"
        assert "threshold" in mv, "Missing threshold field"
        
        print(f"✓ MV response includes all required fields: {list(mv.keys())}")


class TestMVComplianceResponseStructure:
    """Test the overall compliance response structure"""

    def test_compliance_response_structure(self, auth_headers):
        """Verify the compliance check response has correct structure"""
        plan_id = PLAN_IDS["silver_ppo"]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level structure
        assert "mv" in data, "Missing mv section"
        assert "mec" in data, "Missing mec section"
        assert "affordability" in data, "Missing affordability section"
        assert "overall_compliant" in data, "Missing overall_compliant field"
        
        # Check MEC structure
        mec = data.get("mec", {})
        assert "pass" in mec, "Missing mec.pass"
        assert "checks" in mec, "Missing mec.checks"
        
        print(f"✓ Compliance response structure is correct")
        print(f"  - overall_compliant: {data.get('overall_compliant')}")
        print(f"  - mv.pass: {data.get('mv', {}).get('pass')}")
        print(f"  - mec.pass: {data.get('mec', {}).get('pass')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
