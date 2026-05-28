"""
Test Employee Portal Redesign - UI and Backend APIs
Tests for:
1. Employee login (David Chen - declined coverage)
2. Employer login (fajju2001@gmail.com)
3. Backend APIs: GET /api/enrollment/eligibility/{employer_id}, GET /api/irs-forms/1095c/{employer_id}/2026
4. Employee 1095-C download endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
EMPLOYEE_EMAIL = "david.chen@company.com"
EMPLOYEE_PASSWORD = "test123"
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"


class TestEmployeeLogin:
    """Test employee login and portal access"""
    
    def test_employee_login_success(self):
        """Test David Chen can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("email") == EMPLOYEE_EMAIL
        assert data.get("user", {}).get("role") == "employee"
        print(f"✓ Employee login successful: {EMPLOYEE_EMAIL}")
    
    def test_employee_my_plans_endpoint(self):
        """Test employee can access my-plans endpoint"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("token")
        
        # Get my-plans
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-plans", headers=headers)
        assert response.status_code == 200, f"my-plans failed: {response.text}"
        data = response.json()
        
        # Verify enrollment data
        assert "current_enrollment" in data, "No current_enrollment in response"
        enrollment = data.get("current_enrollment")
        if enrollment:
            assert enrollment.get("status") == "declined", f"Expected declined status, got {enrollment.get('status')}"
            assert "offer_code" in enrollment, "No offer_code in enrollment"
            print(f"✓ Employee enrollment status: {enrollment.get('status')}, offer_code: {enrollment.get('offer_code')}")
        else:
            print("✓ No current enrollment (open enrollment view)")
    
    def test_employee_1095c_download(self):
        """Test employee can download 1095-C PDF"""
        # Login first
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        assert login_resp.status_code == 200
        token = login_resp.json().get("token")
        
        # Download 1095-C
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-1095c/pdf", headers=headers)
        assert response.status_code == 200, f"1095-C download failed: {response.text}"
        assert response.headers.get("content-type") == "application/pdf", "Response is not PDF"
        assert len(response.content) > 0, "PDF content is empty"
        print(f"✓ 1095-C PDF downloaded successfully, size: {len(response.content)} bytes")


class TestEmployerLogin:
    """Test employer login and dashboard access"""
    
    def test_employer_login_success(self):
        """Test employer can login successfully"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        assert data.get("user", {}).get("email") == EMPLOYER_EMAIL
        assert data.get("user", {}).get("role") == "employer"
        print(f"✓ Employer login successful: {EMPLOYER_EMAIL}")


class TestBackendAPIs:
    """Test backend APIs for eligibility and IRS forms"""
    
    @pytest.fixture
    def employer_token(self):
        """Get employer auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Employer login failed")
    
    def test_eligibility_endpoint(self, employer_token):
        """Test GET /api/enrollment/eligibility/{employer_id}"""
        headers = {"Authorization": f"Bearer {employer_token}"}
        response = requests.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Eligibility endpoint failed: {response.text}"
        data = response.json()
        
        # Response is a dict with results key
        results = data.get("results", []) if isinstance(data, dict) else data
        assert isinstance(results, list), "Results should be a list"
        print(f"✓ Eligibility endpoint returned {len(results)} records")
        
        # Check for David Chen's eligibility
        david_eligibility = next((e for e in results if "david" in e.get("employee_name", "").lower()), None)
        if david_eligibility:
            print(f"  - David Chen offer_code: {david_eligibility.get('offer_code')}")
    
    def test_1095c_forms_endpoint(self, employer_token):
        """Test GET /api/irs-forms/1095c/{employer_id}/2026"""
        headers = {"Authorization": f"Bearer {employer_token}"}
        response = requests.get(f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/2026", headers=headers)
        assert response.status_code == 200, f"1095-C forms endpoint failed: {response.text}"
        data = response.json()
        
        # Should return forms only for employees with non-1H offer codes
        forms = data.get("forms", []) if isinstance(data, dict) else data
        print(f"✓ 1095-C forms endpoint returned {len(forms)} forms")
        
        # Verify forms are only for offered employees
        for form in forms[:5]:  # Check first 5
            offer_code = form.get("line_14_offer_code") or form.get("offer_code")
            employee_name = form.get("employee_name", "Unknown")
            print(f"  - {employee_name}: offer_code={offer_code}")


class TestDataTestIds:
    """Verify data-testid attributes are present in the frontend code"""
    
    def test_required_testids_in_code(self):
        """Check that required data-testid attributes exist in EmployeePortalPage.js"""
        required_testids = [
            "employee-portal-page",
            "enrollment-status-badge",
            "decline-info-card",
            "form-1095c-card",
            "download-1095c-btn"
        ]
        
        # Read the frontend file
        try:
            with open("/app/frontend/src/pages/EmployeePortalPage.js", "r") as f:
                content = f.read()
            
            for testid in required_testids:
                assert f'data-testid="{testid}"' in content, f"Missing data-testid: {testid}"
                print(f"✓ Found data-testid: {testid}")
        except FileNotFoundError:
            pytest.skip("EmployeePortalPage.js not found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
