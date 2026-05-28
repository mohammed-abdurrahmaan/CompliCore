"""
Test Employee 1095-C Download Feature
Tests the new GET /api/enrollment/employee/my-1095c/pdf endpoint
and verifies that employees with coverage offers can download their 1095-C form.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from test_credentials.md
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"

# Employee with offer (declined coverage) - David Chen
EMPLOYEE_EMAIL = "david.chen@company.com"
EMPLOYEE_PASSWORD = "test123"
EMPLOYEE_ID = "4ef89af1-6649-43cc-95c0-961c4b555697"


class TestEmployee1095CDownload:
    """Tests for employee 1095-C PDF download feature"""
    
    @pytest.fixture
    def employer_token(self):
        """Get employer auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Employer login failed: {response.status_code} - {response.text}")
    
    @pytest.fixture
    def employee_token(self):
        """Get employee auth token for David Chen"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip(f"Employee login failed: {response.status_code} - {response.text}")
    
    def test_employer_login(self):
        """Test employer can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        assert response.status_code == 200, f"Employer login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "employer"
        print(f"✓ Employer login successful: {EMPLOYER_EMAIL}")
    
    def test_employee_login(self):
        """Test employee David Chen can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYEE_EMAIL,
            "password": EMPLOYEE_PASSWORD
        })
        assert response.status_code == 200, f"Employee login failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data.get("user", {}).get("role") == "employee"
        print(f"✓ Employee login successful: {EMPLOYEE_EMAIL}")
    
    def test_irs_forms_shows_2_1095c_forms(self, employer_token):
        """Verify IRS Forms endpoint shows 2 1095-C forms for employer"""
        headers = {"Authorization": f"Bearer {employer_token}"}
        response = requests.get(f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/2026", headers=headers)
        assert response.status_code == 200, f"IRS Forms request failed: {response.text}"
        data = response.json()
        forms = data.get("forms", [])
        assert len(forms) == 2, f"Expected 2 1095-C forms, got {len(forms)}"
        print(f"✓ IRS Forms shows 2 1095-C forms")
        
        # Verify all forms have non-1H offer codes (meaning coverage was offered)
        for form in forms:
            offer_code = form.get("part2", {}).get("line14_all_year", "")
            assert offer_code != "1H", f"Form has 1H offer code, should be non-1H"
            print(f"  Form offer code: {offer_code}")
    
    def test_eligibility_shows_non_1h_for_offered_employees(self, employer_token):
        """Verify eligibility endpoint shows non-1H offer codes for employees with offers"""
        headers = {"Authorization": f"Bearer {employer_token}"}
        response = requests.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Eligibility request failed: {response.text}"
        data = response.json()
        results = data.get("results", [])
        
        # Count offer codes
        non_1h_count = sum(1 for r in results if r.get("offer_code") != "1H")
        assert non_1h_count == 2, f"Expected 2 employees with non-1H offer codes, got {non_1h_count}"
        print(f"✓ Eligibility shows 2 employees with non-1H offer codes")
        
        # Find David Chen's eligibility
        david_elig = next((r for r in results if r.get("employee_id") == EMPLOYEE_ID), None)
        if david_elig:
            assert david_elig.get("offer_code") != "1H", f"David Chen should have non-1H offer code, got {david_elig.get('offer_code')}"
            print(f"✓ David Chen has offer code: {david_elig.get('offer_code')}")
    
    def test_employee_1095c_pdf_download_success(self, employee_token):
        """Test employee can download their 1095-C PDF"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-1095c/pdf", headers=headers)
        
        assert response.status_code == 200, f"1095-C PDF download failed: {response.status_code} - {response.text}"
        
        # Verify it's a PDF
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected PDF content type, got: {content_type}"
        
        # Verify content disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, f"Expected attachment disposition, got: {content_disp}"
        assert "1095-C" in content_disp, f"Expected 1095-C in filename, got: {content_disp}"
        
        # Verify PDF content (starts with %PDF)
        assert response.content[:4] == b'%PDF', "Response is not a valid PDF"
        
        print(f"✓ Employee 1095-C PDF download successful")
        print(f"  Content-Type: {content_type}")
        print(f"  Content-Disposition: {content_disp}")
        print(f"  PDF size: {len(response.content)} bytes")
    
    def test_employee_portal_shows_my_plans(self, employee_token):
        """Test employee portal shows enrollment status"""
        headers = {"Authorization": f"Bearer {employee_token}"}
        response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-plans", headers=headers)
        
        assert response.status_code == 200, f"My plans request failed: {response.text}"
        data = response.json()
        
        # David Chen should have a current enrollment (declined)
        enrollment = data.get("current_enrollment")
        assert enrollment is not None, "Expected current enrollment for David Chen"
        
        status = enrollment.get("status")
        print(f"✓ Employee portal shows enrollment status: {status}")
        
        # Verify offer code is not 1H
        offer_code = enrollment.get("offer_code", "")
        print(f"  Offer code: {offer_code}")
    
    def test_unauthenticated_1095c_download_fails(self):
        """Test that unauthenticated requests fail"""
        response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-1095c/pdf")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Unauthenticated 1095-C download correctly rejected")


class TestEmployee1095CEdgeCases:
    """Edge case tests for 1095-C download"""
    
    def test_employer_cannot_use_employee_endpoint(self):
        """Test that employer role cannot use employee 1095-C endpoint"""
        # Login as employer
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Employer login failed")
        
        token = response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access employee endpoint
        response = requests.get(f"{BASE_URL}/api/enrollment/employee/my-1095c/pdf", headers=headers)
        # Should fail because employer doesn't have linked_employee_id
        assert response.status_code in [400, 404], f"Expected 400/404 for employer, got {response.status_code}"
        print(f"✓ Employer correctly cannot use employee 1095-C endpoint")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
