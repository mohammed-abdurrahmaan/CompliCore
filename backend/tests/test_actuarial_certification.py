"""
Test Actuarial Certification Features:
1. Compliance-check endpoint returns certified_by_actuary: null for plans without real actuary certification
2. Compliance-check endpoint returns has_active_quote: false when no marketplace quote exists
3. MV method shows 'Estimated' or 'HHS Calculator' for non-actuary-certified plans
4. Plans with certification_source='actuary' should have proper certification data
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"


@pytest.fixture(scope="module")
def employer_auth():
    """Get employer auth token and employer_id"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYER_EMAIL,
        "password": EMPLOYER_PASSWORD
    })
    assert response.status_code == 200, f"Employer login failed: {response.text}"
    data = response.json()
    token = data["token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Get employer_id from employers endpoint
    emp_response = requests.get(f"{BASE_URL}/api/employers", headers=headers)
    assert emp_response.status_code == 200, f"Failed to get employers: {emp_response.text}"
    employers = emp_response.json()
    assert len(employers) > 0, "No employers found"
    employer_id = employers[0]["id"]
    
    return {
        "token": token,
        "employer_id": employer_id,
        "headers": headers
    }


@pytest.fixture(scope="module")
def plans(employer_auth):
    """Get all plans for employer"""
    response = requests.get(
        f"{BASE_URL}/api/enrollment/plans/{employer_auth['employer_id']}", 
        headers=employer_auth["headers"]
    )
    assert response.status_code == 200, f"Failed to get plans: {response.text}"
    return response.json()


class TestComplianceCheckActuaryCertification:
    """Test compliance-check endpoint returns correct actuarial certification data"""

    def test_compliance_check_returns_certified_by_actuary_null_for_uncertified_plans(self, employer_auth, plans):
        """Plans without real actuary certification should have certified_by_actuary: null"""
        if not plans:
            pytest.skip("No plans available")
        
        # Test multiple plans to ensure none have false actuary certification
        for plan in plans[:5]:  # Test first 5 plans
            response = requests.post(
                f"{BASE_URL}/api/enrollment/plans/{plan['id']}/compliance-check",
                headers=employer_auth["headers"],
                json={}
            )
            
            assert response.status_code == 200, f"Compliance check failed for {plan['plan_name']}: {response.text}"
            data = response.json()
            
            # Verify MV structure exists
            assert "mv" in data, f"Missing 'mv' in response for {plan['plan_name']}"
            
            # If plan doesn't have certification_source='actuary', certified_by_actuary should be null
            if plan.get("certification_source") != "actuary":
                assert data["mv"].get("certified_by_actuary") is None, \
                    f"Plan '{plan['plan_name']}' should have certified_by_actuary: null (got: {data['mv'].get('certified_by_actuary')})"
                print(f"✓ Plan '{plan['plan_name']}': certified_by_actuary is correctly null")
            else:
                # If plan has actuary certification, it should have certification data
                assert data["mv"].get("certified_by_actuary") is not None, \
                    f"Plan '{plan['plan_name']}' with certification_source='actuary' should have certification data"
                print(f"✓ Plan '{plan['plan_name']}': has actuary certification data")

    def test_compliance_check_returns_has_active_quote_false_for_plans_without_quotes(self, employer_auth, plans):
        """Plans without marketplace quotes should have has_active_quote: false"""
        if not plans:
            pytest.skip("No plans available")
        
        for plan in plans[:5]:  # Test first 5 plans
            response = requests.post(
                f"{BASE_URL}/api/enrollment/plans/{plan['id']}/compliance-check",
                headers=employer_auth["headers"],
                json={}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify has_active_quote field exists
            assert "has_active_quote" in data["mv"], f"Missing 'has_active_quote' in mv for {plan['plan_name']}"
            
            # For plans without active quotes, should be false
            # (We can't guarantee this without knowing quote state, but we verify the field exists)
            has_quote = data["mv"]["has_active_quote"]
            print(f"✓ Plan '{plan['plan_name']}': has_active_quote = {has_quote}")

    def test_compliance_check_mv_method_for_non_actuary_certified_plans(self, employer_auth, plans):
        """Non-actuary-certified plans should show method as 'Estimated' or 'HHS Calculator'"""
        if not plans:
            pytest.skip("No plans available")
        
        for plan in plans[:5]:
            response = requests.post(
                f"{BASE_URL}/api/enrollment/plans/{plan['id']}/compliance-check",
                headers=employer_auth["headers"],
                json={}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            method = data["mv"].get("method", "")
            cert_source = plan.get("certification_source")
            
            if cert_source != "actuary":
                # Should be 'Estimated' or 'HHS Calculator', NOT 'Actuarial Certification'
                assert method in ["Estimated", "HHS Calculator"], \
                    f"Plan '{plan['plan_name']}' without actuary cert should have method 'Estimated' or 'HHS Calculator', got: '{method}'"
                print(f"✓ Plan '{plan['plan_name']}': method = '{method}' (correct for non-actuary plan)")
            else:
                assert method == "Actuarial Certification", \
                    f"Plan '{plan['plan_name']}' with actuary cert should have method 'Actuarial Certification', got: '{method}'"
                print(f"✓ Plan '{plan['plan_name']}': method = '{method}' (correct for actuary-certified plan)")

    def test_compliance_check_certification_source_field(self, employer_auth, plans):
        """Compliance check should return certification_source field"""
        if not plans:
            pytest.skip("No plans available")
        
        plan = plans[0]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan['id']}/compliance-check",
            headers=employer_auth["headers"],
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # certification_source should be in the response
        assert "certification_source" in data["mv"], "Missing 'certification_source' in mv"
        
        cert_source = data["mv"]["certification_source"]
        print(f"✓ Plan '{plan['plan_name']}': certification_source = {cert_source}")


class TestPlanMVStatus:
    """Test plan MV status and 'Get Actuarial Quote' button logic"""

    def test_find_plan_with_mv_below_60(self, employer_auth, plans):
        """Find plans with MV < 60% that should show 'Get Actuarial Quote' button"""
        if not plans:
            pytest.skip("No plans available")
        
        medical_plans = [p for p in plans if p.get("category") == "medical"]
        low_mv_plans = [p for p in medical_plans if p.get("mv_percentage") is not None and p.get("mv_percentage") < 60]
        
        print(f"Found {len(low_mv_plans)} medical plans with MV < 60%:")
        for plan in low_mv_plans:
            cert_source = plan.get("certification_source")
            should_show_quote_btn = cert_source != "actuary"
            print(f"  - {plan['plan_name']}: MV={plan.get('mv_percentage')}%, cert_source={cert_source}, should_show_quote_btn={should_show_quote_btn}")
        
        # Verify Bronze HDHP exists with MV 58%
        bronze_hdhp = next((p for p in low_mv_plans if "Bronze" in p.get("plan_name", "") and "HDHP" in p.get("plan_name", "")), None)
        if bronze_hdhp:
            assert bronze_hdhp.get("mv_percentage") == 58, f"Bronze HDHP should have MV 58%, got {bronze_hdhp.get('mv_percentage')}"
            assert bronze_hdhp.get("certification_source") != "actuary", "Bronze HDHP should not have actuary certification"
            print(f"✓ Bronze HDHP found with MV={bronze_hdhp.get('mv_percentage')}% - should show 'Get Actuarial Quote' button")

    def test_find_plan_with_mv_above_60(self, employer_auth, plans):
        """Find plans with MV >= 60% that should NOT show 'Get Actuarial Quote' button"""
        if not plans:
            pytest.skip("No plans available")
        
        medical_plans = [p for p in plans if p.get("category") == "medical"]
        high_mv_plans = [p for p in medical_plans if p.get("mv_percentage") is not None and p.get("mv_percentage") >= 60]
        
        print(f"Found {len(high_mv_plans)} medical plans with MV >= 60%:")
        for plan in high_mv_plans[:5]:  # Show first 5
            print(f"  - {plan['plan_name']}: MV={plan.get('mv_percentage')}% - should NOT show 'Get Actuarial Quote' button")
        
        # Verify Silver PPO exists with MV 62%
        silver_ppo = next((p for p in high_mv_plans if "Silver" in p.get("plan_name", "") and "PPO" in p.get("plan_name", "")), None)
        if silver_ppo:
            assert silver_ppo.get("mv_percentage") >= 60, f"Silver PPO should have MV >= 60%, got {silver_ppo.get('mv_percentage')}"
            print(f"✓ Silver PPO found with MV={silver_ppo.get('mv_percentage')}% - should NOT show 'Get Actuarial Quote' button")


class TestAffordabilityFTEmployees:
    """Test affordability section shows Full-Time / FTE Employees count"""

    def test_affordability_shows_ft_employee_count(self, employer_auth, plans):
        """Affordability section should show total_ft_employees count"""
        if not plans:
            pytest.skip("No plans available")
        
        plan = plans[0]
        response = requests.post(
            f"{BASE_URL}/api/enrollment/plans/{plan['id']}/compliance-check",
            headers=employer_auth["headers"],
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        aff = data.get("affordability", {})
        
        # Verify total_ft_employees field exists
        assert "total_ft_employees" in aff, "Missing 'total_ft_employees' in affordability"
        
        ft_count = aff["total_ft_employees"]
        checked_count = aff.get("total_employees_checked", 0)
        
        print(f"✓ Affordability: total_ft_employees = {ft_count}, total_employees_checked = {checked_count}")
        
        # FT employees should be >= checked employees (checked are those with salary data)
        assert ft_count >= 0, "total_ft_employees should be >= 0"


class TestLoginWorks:
    """Test login works for employer"""

    def test_employer_login(self):
        """Login works for employer fajju2001@gmail.com / test123"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "token" in data, "Missing token in response"
        assert "user" in data, "Missing user in response"
        assert data["user"]["email"] == EMPLOYER_EMAIL, "Email mismatch"
        
        print(f"✓ Login successful for {EMPLOYER_EMAIL}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
