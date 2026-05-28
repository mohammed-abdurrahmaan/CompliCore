"""
Test Predictive Intelligence Endpoints
- GET /api/predictive/alerts/{employer_id} - Rule-based compliance alerts
- GET /api/predictive/growth/{employer_id} - Hiring growth projection
- GET /api/predictive/exposure/{employer_id} - Financial exposure forecasting
- POST /api/predictive/scenario/{employer_id} - Scenario modeling
- POST /api/predictive/ai-summary/{employer_id} - AI-powered compliance summary
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"

# Test credentials
TEST_EMAIL = "fajju2001@gmail.com"
TEST_PASSWORD = "test123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for employer"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def headers(auth_token):
    """Headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPredictiveAlerts:
    """Test compliance alerts endpoint"""
    
    def test_get_alerts_returns_200(self, headers):
        """GET /api/predictive/alerts/{employer_id} returns 200"""
        response = requests.get(f"{BASE_URL}/api/predictive/alerts/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: GET /api/predictive/alerts returns 200")
    
    def test_alerts_response_structure(self, headers):
        """Alerts response has alerts array with severity, title, detail, action fields"""
        response = requests.get(f"{BASE_URL}/api/predictive/alerts/{EMPLOYER_ID}", headers=headers)
        data = response.json()
        
        assert "alerts" in data, "Response missing 'alerts' field"
        assert "total" in data, "Response missing 'total' field"
        assert "critical" in data, "Response missing 'critical' count"
        assert "warnings" in data, "Response missing 'warnings' count"
        
        assert isinstance(data["alerts"], list), "'alerts' should be a list"
        
        # If there are alerts, verify structure
        if data["alerts"]:
            alert = data["alerts"][0]
            assert "id" in alert, "Alert missing 'id'"
            assert "severity" in alert, "Alert missing 'severity'"
            assert "title" in alert, "Alert missing 'title'"
            assert "detail" in alert, "Alert missing 'detail'"
            assert "action" in alert, "Alert missing 'action'"
            assert "category" in alert, "Alert missing 'category'"
            print(f"PASS: Alert structure verified - {len(data['alerts'])} alerts found")
        else:
            print("PASS: No alerts (compliant state)")


class TestPredictiveGrowth:
    """Test growth projection endpoint"""
    
    def test_get_growth_returns_200(self, headers):
        """GET /api/predictive/growth/{employer_id} returns 200"""
        response = requests.get(f"{BASE_URL}/api/predictive/growth/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: GET /api/predictive/growth returns 200")
    
    def test_growth_response_structure(self, headers):
        """Growth response has current workforce, avg_monthly_hires, history, projections"""
        response = requests.get(f"{BASE_URL}/api/predictive/growth/{EMPLOYER_ID}", headers=headers)
        data = response.json()
        
        # Current workforce
        assert "current" in data, "Response missing 'current' field"
        current = data["current"]
        assert "total" in current, "Current missing 'total'"
        assert "full_time" in current, "Current missing 'full_time'"
        assert "part_time" in current, "Current missing 'part_time'"
        assert "total_fte" in current, "Current missing 'total_fte'"
        assert "is_ale" in current, "Current missing 'is_ale'"
        
        # Hiring metrics
        assert "avg_monthly_hires" in data, "Response missing 'avg_monthly_hires'"
        assert "ft_hire_ratio" in data, "Response missing 'ft_hire_ratio'"
        
        # History
        assert "history" in data, "Response missing 'history'"
        assert isinstance(data["history"], list), "'history' should be a list"
        if data["history"]:
            h = data["history"][0]
            assert "month" in h, "History item missing 'month'"
            assert "hires" in h, "History item missing 'hires'"
        
        # Projections
        assert "projections" in data, "Response missing 'projections'"
        assert isinstance(data["projections"], list), "'projections' should be a list"
        if data["projections"]:
            p = data["projections"][0]
            assert "month" in p, "Projection missing 'month'"
            assert "projected_fte" in p, "Projection missing 'projected_fte'"
            assert "is_ale" in p, "Projection missing 'is_ale'"
        
        print(f"PASS: Growth structure verified - {current['total']} employees, {current['total_fte']} FTE")


class TestPredictiveExposure:
    """Test financial exposure endpoint"""
    
    def test_get_exposure_returns_200(self, headers):
        """GET /api/predictive/exposure/{employer_id} returns 200"""
        response = requests.get(f"{BASE_URL}/api/predictive/exposure/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: GET /api/predictive/exposure returns 200")
    
    def test_exposure_response_structure(self, headers):
        """Exposure response has current_exposure, premium_costs, worst_case, rates"""
        response = requests.get(f"{BASE_URL}/api/predictive/exposure/{EMPLOYER_ID}", headers=headers)
        data = response.json()
        
        # Current exposure
        assert "current_exposure" in data, "Response missing 'current_exposure'"
        exp = data["current_exposure"]
        assert "penalty_a" in exp, "Exposure missing 'penalty_a'"
        assert "penalty_b" in exp, "Exposure missing 'penalty_b'"
        assert "total_penalty_exposure" in exp, "Exposure missing 'total_penalty_exposure'"
        assert "affordability_exposure" in exp, "Exposure missing 'affordability_exposure'"
        
        # Premium costs
        assert "premium_costs" in data, "Response missing 'premium_costs'"
        costs = data["premium_costs"]
        assert "annual_employer_cost" in costs, "Costs missing 'annual_employer_cost'"
        assert "annual_employee_cost" in costs, "Costs missing 'annual_employee_cost'"
        
        # Worst case
        assert "worst_case" in data, "Response missing 'worst_case'"
        worst = data["worst_case"]
        assert "total_worst_case" in worst, "Worst case missing 'total_worst_case'"
        
        # Rates
        assert "rates" in data, "Response missing 'rates'"
        rates = data["rates"]
        assert "penalty_a_rate" in rates, "Rates missing 'penalty_a_rate'"
        assert "penalty_b_rate" in rates, "Rates missing 'penalty_b_rate'"
        assert "affordability_threshold" in rates, "Rates missing 'affordability_threshold'"
        
        print(f"PASS: Exposure structure verified - Total exposure: ${exp['total_penalty_exposure']:,}")


class TestPredictiveScenario:
    """Test scenario modeling endpoint"""
    
    def test_scenario_hire_10_ft(self, headers):
        """POST /api/predictive/scenario with add_full_time: 10 returns scenario comparison"""
        response = requests.post(
            f"{BASE_URL}/api/predictive/scenario/{EMPLOYER_ID}",
            headers=headers,
            json={"add_full_time": 10}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Current state
        assert "current" in data, "Response missing 'current'"
        assert "scenario" in data, "Response missing 'scenario'"
        assert "delta" in data, "Response missing 'delta'"
        assert "warnings" in data, "Response missing 'warnings'"
        
        # Verify scenario reflects the change
        assert data["scenario"]["ft"] == data["current"]["ft"] + 10, "Scenario FT should be current + 10"
        
        print(f"PASS: Scenario hire 10 FT - Current FTE: {data['current']['total_fte']}, After: {data['scenario']['total_fte']}")
    
    def test_scenario_drop_mec(self, headers):
        """POST /api/predictive/scenario with drop_mec_coverage: true returns warnings"""
        response = requests.post(
            f"{BASE_URL}/api/predictive/scenario/{EMPLOYER_ID}",
            headers=headers,
            json={"drop_mec_coverage": True}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Should have warnings about dropping MEC
        assert "warnings" in data, "Response missing 'warnings'"
        assert isinstance(data["warnings"], list), "'warnings' should be a list"
        
        # If ALE, should warn about penalties
        if data["current"]["is_ale"]:
            assert len(data["warnings"]) > 0, "Should have warnings for ALE dropping MEC"
            warning_text = " ".join(data["warnings"]).lower()
            assert "mec" in warning_text or "penalty" in warning_text, "Should warn about MEC/penalty"
        
        print(f"PASS: Scenario drop MEC - {len(data['warnings'])} warnings generated")
    
    def test_scenario_response_structure(self, headers):
        """Scenario response has current, scenario, delta, warnings with proper fields"""
        response = requests.post(
            f"{BASE_URL}/api/predictive/scenario/{EMPLOYER_ID}",
            headers=headers,
            json={"add_full_time": 5, "add_part_time": 3}
        )
        data = response.json()
        
        # Current state fields
        current = data["current"]
        assert "ft" in current, "Current missing 'ft'"
        assert "pt" in current, "Current missing 'pt'"
        assert "total_fte" in current, "Current missing 'total_fte'"
        assert "is_ale" in current, "Current missing 'is_ale'"
        assert "mec_pct" in current, "Current missing 'mec_pct'"
        assert "total_penalty" in current, "Current missing 'total_penalty'"
        
        # Scenario state fields
        scenario = data["scenario"]
        assert "ft" in scenario, "Scenario missing 'ft'"
        assert "total_fte" in scenario, "Scenario missing 'total_fte'"
        assert "total_penalty" in scenario, "Scenario missing 'total_penalty'"
        
        # Delta fields
        delta = data["delta"]
        assert "fte_change" in delta, "Delta missing 'fte_change'"
        assert "ale_changed" in delta, "Delta missing 'ale_changed'"
        assert "penalty_change" in delta, "Delta missing 'penalty_change'"
        
        print(f"PASS: Scenario structure verified - FTE change: {delta['fte_change']}, Penalty change: ${delta['penalty_change']:,}")


class TestPredictiveAISummary:
    """Test AI-powered summary endpoint"""
    
    def test_ai_summary_returns_200(self, headers):
        """POST /api/predictive/ai-summary/{employer_id} returns 200"""
        response = requests.post(
            f"{BASE_URL}/api/predictive/ai-summary/{EMPLOYER_ID}",
            headers=headers,
            json={}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"PASS: POST /api/predictive/ai-summary returns 200")
    
    def test_ai_summary_response_structure(self, headers):
        """AI summary response has generated flag and summary text"""
        response = requests.post(
            f"{BASE_URL}/api/predictive/ai-summary/{EMPLOYER_ID}",
            headers=headers,
            json={}
        )
        data = response.json()
        
        assert "summary" in data, "Response missing 'summary'"
        assert "generated" in data, "Response missing 'generated'"
        
        # Summary should be a non-empty string
        assert isinstance(data["summary"], str), "'summary' should be a string"
        assert len(data["summary"]) > 0, "'summary' should not be empty"
        
        if data["generated"]:
            # If AI generated, should have additional fields
            assert "generated_at" in data, "Generated response missing 'generated_at'"
            print(f"PASS: AI summary generated - {len(data['summary'])} chars")
        else:
            print(f"PASS: AI summary fallback - {data['summary'][:100]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
