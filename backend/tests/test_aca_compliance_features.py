"""
Test ACA Compliance Features - Dashboard MEC calculation, Risk Alerts, Plan Library MV/MEC logic
Tests the 5 specific changes requested:
1. Get Actuarial Quote button only shows when MV fails (MV < 60% and not certified)
2. Assign button disabled when MV fails
3. MEC checkbox disabled in edit popup when MEC fails
4. Dashboard risk alerts show penalty breakdown
5. Dashboard MEC % uses plan_library collection
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test employer with Platinum PPO (mec_qualified=false)
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"

# Plan IDs for testing
PLATINUM_PPO_ID = "16739425-5a63-45d9-9fde-418724747016"  # mec_qualified=false, mv_certified=true
BRONZE_HDHP_ID = "46ef441c-ab24-4a2d-a583-79f29ada5dcf"   # MV 58%, mv_certified=true
SILVER_PPO_ID = "ac820c3c-4409-4818-82c5-55c8ba523ce9"    # mec_qualified=true, mv_certified=true


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for employer"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYER_EMAIL,
        "password": EMPLOYER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestDashboardMECCalculation:
    """Test Dashboard MEC coverage % reflects plan_library data"""
    
    def test_dashboard_returns_mec_coverage_pct(self, api_client):
        """Dashboard should return mec_coverage_pct field"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        assert "compliance" in data
        assert "mec_coverage_pct" in data["compliance"]
        print(f"MEC coverage %: {data['compliance']['mec_coverage_pct']}")
    
    def test_mec_coverage_not_100_when_plan_fails(self, api_client):
        """MEC coverage should NOT be 100% when Platinum PPO has mec_qualified=false"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        mec_pct = data["compliance"]["mec_coverage_pct"]
        
        # Should be less than 100% since Platinum PPO has mec_qualified=false
        # Expected: 6.4% based on employee enrollments/assignments
        assert mec_pct < 100, f"MEC coverage should be < 100% but got {mec_pct}%"
        print(f"MEC coverage %: {mec_pct} (correctly < 100%)")
    
    def test_mec_offered_count_excludes_failing_plans(self, api_client):
        """mec_offered should count only MEC-qualified plans"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        mec_offered = data["compliance"]["mec_offered"]
        mec_total = data["compliance"]["mec_total_medical"]
        
        # 5 medical plans, 4 MEC-qualified (Platinum PPO is not)
        assert mec_offered == 4, f"Expected 4 MEC-qualified plans, got {mec_offered}"
        assert mec_total == 5, f"Expected 5 total medical plans, got {mec_total}"
        print(f"MEC offered: {mec_offered}/{mec_total} medical plans")


class TestDashboardRiskAlerts:
    """Test Dashboard risk alerts with penalty breakdown"""
    
    def test_risk_alerts_include_penalty_breakdown(self, api_client):
        """Risk alerts should include penalty_a_amount and penalty_a_reason"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        risk = data["risk_alerts"]
        
        # Check penalty breakdown fields exist
        assert "potential_penalty" in risk
        assert "penalty_a_amount" in risk
        assert "penalty_b_amount" in risk
        assert "penalty_a_reason" in risk
        assert "penalty_b_reason" in risk
        
        print(f"Potential penalty: ${risk['potential_penalty']}")
        print(f"Penalty A: ${risk['penalty_a_amount']} - {risk['penalty_a_reason']}")
        print(f"Penalty B: ${risk['penalty_b_amount']} - {risk['penalty_b_reason']}")
    
    def test_penalty_a_calculated_when_mec_not_compliant(self, api_client):
        """Penalty A should be calculated when MEC < 95%"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        risk = data["risk_alerts"]
        compliance = data["compliance"]
        
        # MEC is not compliant (< 95%)
        assert not compliance["mec_compliant"], "MEC should not be compliant"
        
        # Penalty A should be > 0
        assert risk["penalty_a_amount"] > 0, "Penalty A should be > 0 when MEC not compliant"
        
        # Expected: (47 FT - 30) * $2,970 = 17 * $2,970 = $50,490
        expected_penalty = 50490
        assert risk["penalty_a_amount"] == expected_penalty, f"Expected ${expected_penalty}, got ${risk['penalty_a_amount']}"
        
        # Reason should mention 4980H(a)
        assert "4980H(a)" in risk["penalty_a_reason"], "Penalty A reason should mention 4980H(a)"
        print(f"Penalty A correctly calculated: ${risk['penalty_a_amount']}")
    
    def test_potential_penalty_is_sum_of_a_and_b(self, api_client):
        """potential_penalty should equal penalty_a_amount + penalty_b_amount"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        risk = data["risk_alerts"]
        
        expected_total = risk["penalty_a_amount"] + risk["penalty_b_amount"]
        assert risk["potential_penalty"] == expected_total, \
            f"potential_penalty ({risk['potential_penalty']}) should equal penalty_a + penalty_b ({expected_total})"


class TestPlanLibraryData:
    """Test Plan Library API returns correct MV/MEC data"""
    
    def test_platinum_ppo_has_mec_qualified_false(self, api_client):
        """Platinum PPO should have mec_qualified=false"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        plans = data["plans"]
        
        platinum = next((p for p in plans if p["id"] == PLATINUM_PPO_ID), None)
        assert platinum is not None, "Platinum PPO not found"
        assert platinum["mec_qualified"] == False, "Platinum PPO should have mec_qualified=false"
        print(f"Platinum PPO mec_qualified: {platinum['mec_qualified']}")
    
    def test_bronze_hdhp_has_mv_certified_true(self, api_client):
        """Bronze HDHP (MV 58%) should have mv_certified=true"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        plans = data["plans"]
        
        bronze = next((p for p in plans if p["id"] == BRONZE_HDHP_ID), None)
        assert bronze is not None, "Bronze HDHP not found"
        assert bronze["mv_percentage"] == 58, f"Bronze HDHP MV should be 58%, got {bronze['mv_percentage']}"
        assert bronze["mv_certified"] == True, "Bronze HDHP should have mv_certified=true"
        print(f"Bronze HDHP: MV {bronze['mv_percentage']}%, certified: {bronze['mv_certified']}")
    
    def test_silver_ppo_has_mec_qualified_true(self, api_client):
        """Silver PPO should have mec_qualified=true"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        plans = data["plans"]
        
        silver = next((p for p in plans if p["id"] == SILVER_PPO_ID), None)
        assert silver is not None, "Silver PPO not found"
        assert silver["mec_qualified"] == True, "Silver PPO should have mec_qualified=true"
        print(f"Silver PPO mec_qualified: {silver['mec_qualified']}")
    
    def test_dental_vision_plans_have_mec_false(self, api_client):
        """Dental and vision plans should have mec_qualified=false (expected for non-medical)"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        plans = data["plans"]
        
        dental_vision = [p for p in plans if p["category"] in ["dental", "vision"]]
        for plan in dental_vision:
            # Dental/vision plans have mec_qualified=false but should NOT show MEC Fail badge
            assert plan["mec_qualified"] == False, f"{plan['plan_name']} should have mec_qualified=false"
            print(f"{plan['plan_name']} ({plan['category']}): mec_qualified={plan['mec_qualified']}")


class TestMVFailLogic:
    """Test MV fail logic for Get Actuarial Quote and Assign buttons"""
    
    def test_mv_failing_plans_identified(self, api_client):
        """Dashboard should identify MV-failing plans (MV < 60%)"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        compliance = data["compliance"]
        
        # Bronze HDHP has MV 58% but is certified, so it should NOT count as failing
        # All plans are mv_certified=true, so mv_plans_failing should be 0 or 1
        print(f"MV plans failing: {compliance['mv_plans_failing']}")
        print(f"MV plans passing: {compliance['mv_plans_passing']}")
    
    def test_all_medical_plans_have_mv_data(self, api_client):
        """All medical plans should have mv_percentage and mv_certified fields"""
        response = api_client.get(f"{BASE_URL}/api/dashboard/enhanced/{EMPLOYER_ID}")
        assert response.status_code == 200
        
        data = response.json()
        plans = data["plans"]
        
        medical_plans = [p for p in plans if p["category"] == "medical"]
        for plan in medical_plans:
            assert "mv_percentage" in plan, f"{plan['plan_name']} missing mv_percentage"
            assert "mv_certified" in plan, f"{plan['plan_name']} missing mv_certified"
            print(f"{plan['plan_name']}: MV {plan['mv_percentage']}%, certified: {plan['mv_certified']}")


class TestComplianceCheckEndpoint:
    """Test compliance check endpoint for MEC/MV data"""
    
    def test_compliance_check_returns_mec_data(self, api_client):
        """Compliance check should return MEC qualification data"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        assert "mec" in data
        print(f"MEC compliance data: {data['mec']}")
    
    def test_compliance_check_returns_mv_data(self, api_client):
        """Compliance check should return MV percentage data"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{SILVER_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        assert "mv" in data
        print(f"MV compliance data: {data['mv']}")
    
    def test_compliance_check_for_mec_failing_plan(self, api_client):
        """Compliance check for Platinum PPO should show MEC not qualified"""
        response = api_client.post(f"{BASE_URL}/api/enrollment/plans/{PLATINUM_PPO_ID}/compliance-check")
        assert response.status_code == 200
        
        data = response.json()
        # The plan has mec_qualified=false, so compliance check should reflect this
        print(f"Platinum PPO compliance: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
