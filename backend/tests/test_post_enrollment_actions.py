"""
Test Post-Enrollment Actions for Enrollment Review Page
- Step 1: Send Payroll Deductions to ADP (payroll-export endpoint)
- Step 2: Export Census for Insurance Carrier (carrier-export endpoint)
- Step 3: IRS Offer Codes auto-update (enrollment/review endpoint)
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
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestPayrollSummaryEndpoint:
    """Test GET /api/enrollment/payroll-summary/{employer_id}"""
    
    def test_payroll_summary_returns_200(self, headers):
        """Payroll summary endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/enrollment/payroll-summary/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Payroll summary returned 200")
    
    def test_payroll_summary_has_required_fields(self, headers):
        """Payroll summary should have enrolled_count, total_ee_deductions, total_er_contributions, carriers"""
        response = requests.get(f"{BASE_URL}/api/enrollment/payroll-summary/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields exist
        assert "enrolled_count" in data, "Missing enrolled_count field"
        assert "total_ee_deductions" in data, "Missing total_ee_deductions field"
        assert "total_er_contributions" in data, "Missing total_er_contributions field"
        assert "carriers" in data, "Missing carriers field"
        assert "ready" in data, "Missing ready field"
        
        # Validate data types
        assert isinstance(data["enrolled_count"], int), "enrolled_count should be int"
        assert isinstance(data["total_ee_deductions"], (int, float)), "total_ee_deductions should be numeric"
        assert isinstance(data["total_er_contributions"], (int, float)), "total_er_contributions should be numeric"
        assert isinstance(data["carriers"], list), "carriers should be a list"
        
        print(f"✓ Payroll summary has all required fields")
        print(f"  - enrolled_count: {data['enrolled_count']}")
        print(f"  - total_ee_deductions: ${data['total_ee_deductions']}")
        print(f"  - total_er_contributions: ${data['total_er_contributions']}")
        print(f"  - carriers: {data['carriers']}")


class TestPayrollExportEndpoint:
    """Test GET /api/enrollment/payroll-export/{employer_id}"""
    
    def test_payroll_export_returns_excel(self, headers):
        """Payroll export should return Excel file"""
        response = requests.get(f"{BASE_URL}/api/enrollment/payroll-export/{EMPLOYER_ID}", headers=headers)
        
        # Should return 200 with Excel file OR 400 if no enrolled employees
        if response.status_code == 400:
            data = response.json()
            assert "No enrolled employees" in data.get("detail", ""), f"Unexpected 400 error: {data}"
            print(f"✓ Payroll export returned 400 (no enrolled employees) - expected behavior")
            pytest.skip("No enrolled employees to export")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type is Excel
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheetml" in content_type or "application/vnd" in content_type, f"Expected Excel content type, got {content_type}"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Expected attachment disposition"
        assert ".xlsx" in content_disp, "Expected .xlsx filename"
        
        # Check file has content
        assert len(response.content) > 0, "Excel file should have content"
        
        print(f"✓ Payroll export returned Excel file ({len(response.content)} bytes)")
        print(f"  - Content-Type: {content_type}")
        print(f"  - Content-Disposition: {content_disp}")


class TestCarrierExportEndpoint:
    """Test GET /api/enrollment/carrier-export/{employer_id}"""
    
    def test_carrier_export_returns_excel(self, headers):
        """Carrier census export should return Excel file"""
        response = requests.get(f"{BASE_URL}/api/enrollment/carrier-export/{EMPLOYER_ID}", headers=headers)
        
        # Should return 200 with Excel file OR 400 if no enrolled employees
        if response.status_code == 400:
            data = response.json()
            assert "No enrolled employees" in data.get("detail", ""), f"Unexpected 400 error: {data}"
            print(f"✓ Carrier export returned 400 (no enrolled employees) - expected behavior")
            pytest.skip("No enrolled employees to export")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type is Excel
        content_type = response.headers.get("Content-Type", "")
        assert "spreadsheetml" in content_type or "application/vnd" in content_type, f"Expected Excel content type, got {content_type}"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Expected attachment disposition"
        assert ".xlsx" in content_disp, "Expected .xlsx filename"
        
        # Check file has content
        assert len(response.content) > 0, "Excel file should have content"
        
        print(f"✓ Carrier export returned Excel file ({len(response.content)} bytes)")
        print(f"  - Content-Type: {content_type}")
        print(f"  - Content-Disposition: {content_disp}")
    
    def test_carrier_export_with_carrier_filter(self, headers):
        """Carrier census export should accept carrier filter parameter"""
        # First get the payroll summary to find available carriers
        summary_response = requests.get(f"{BASE_URL}/api/enrollment/payroll-summary/{EMPLOYER_ID}", headers=headers)
        if summary_response.status_code != 200:
            pytest.skip("Could not get payroll summary")
        
        carriers = summary_response.json().get("carriers", [])
        if not carriers:
            pytest.skip("No carriers available to filter")
        
        # Test with first carrier
        carrier = carriers[0]
        response = requests.get(f"{BASE_URL}/api/enrollment/carrier-export/{EMPLOYER_ID}?carrier={carrier}", headers=headers)
        
        # Should return 200 or 400 (if no employees for that carrier)
        assert response.status_code in [200, 400], f"Expected 200 or 400, got {response.status_code}"
        print(f"✓ Carrier export with filter '{carrier}' returned {response.status_code}")


class TestEnrollmentReviewEndpoint:
    """Test GET /api/enrollment/review/{employer_id}"""
    
    def test_enrollment_review_returns_200(self, headers):
        """Enrollment review endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/enrollment/review/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Enrollment review returned 200")
    
    def test_enrollment_review_has_required_fields(self, headers):
        """Enrollment review should have total_enrollments, enrolled, declined counts"""
        response = requests.get(f"{BASE_URL}/api/enrollment/review/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_enrollments" in data, "Missing total_enrollments field"
        assert "enrolled" in data, "Missing enrolled field"
        assert "declined" in data, "Missing declined field"
        assert "pending_approval" in data, "Missing pending_approval field"
        assert "enrollments" in data, "Missing enrollments array"
        
        # Validate data types
        assert isinstance(data["total_enrollments"], int), "total_enrollments should be int"
        assert isinstance(data["enrolled"], int), "enrolled should be int"
        assert isinstance(data["declined"], int), "declined should be int"
        assert isinstance(data["enrollments"], list), "enrollments should be a list"
        
        print(f"✓ Enrollment review has all required fields")
        print(f"  - total_enrollments: {data['total_enrollments']}")
        print(f"  - enrolled: {data['enrolled']}")
        print(f"  - declined: {data['declined']}")
        print(f"  - pending_approval: {data['pending_approval']}")
    
    def test_enrollment_data_structure(self, headers):
        """Each enrollment should have employee_name, status, plan_name, coverage_tier, approved"""
        response = requests.get(f"{BASE_URL}/api/enrollment/review/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        enrollments = data.get("enrollments", [])
        if not enrollments:
            pytest.skip("No enrollments to validate structure")
        
        for enrollment in enrollments:
            assert "id" in enrollment, "Enrollment missing id"
            assert "employee_name" in enrollment, "Enrollment missing employee_name"
            assert "status" in enrollment, "Enrollment missing status"
            assert "approved" in enrollment, "Enrollment missing approved"
            
            # Status should be enrolled or declined
            assert enrollment["status"] in ["enrolled", "declined"], f"Invalid status: {enrollment['status']}"
            
            # If enrolled, should have plan info
            if enrollment["status"] == "enrolled":
                assert "plan_name" in enrollment, "Enrolled employee missing plan_name"
                assert "coverage_tier" in enrollment, "Enrolled employee missing coverage_tier"
        
        print(f"✓ All {len(enrollments)} enrollments have valid structure")


class TestEnrollmentProofEndpoint:
    """Test GET /api/enrollment/review/{employer_id}/proof/{enrollment_id}"""
    
    def test_enrollment_proof_returns_pdf(self, headers):
        """Enrollment proof should return PDF file"""
        # First get enrollments to find an enrollment ID
        review_response = requests.get(f"{BASE_URL}/api/enrollment/review/{EMPLOYER_ID}", headers=headers)
        if review_response.status_code != 200:
            pytest.skip("Could not get enrollment review")
        
        enrollments = review_response.json().get("enrollments", [])
        if not enrollments:
            pytest.skip("No enrollments to get proof for")
        
        enrollment_id = enrollments[0]["id"]
        
        response = requests.get(f"{BASE_URL}/api/enrollment/review/{EMPLOYER_ID}/proof/{enrollment_id}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Check content type is PDF
        content_type = response.headers.get("Content-Type", "")
        assert "pdf" in content_type.lower(), f"Expected PDF content type, got {content_type}"
        
        # Check Content-Disposition header for filename
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Expected attachment disposition"
        assert ".pdf" in content_disp, "Expected .pdf filename"
        
        # Check file has content
        assert len(response.content) > 0, "PDF file should have content"
        
        print(f"✓ Enrollment proof returned PDF file ({len(response.content)} bytes)")
        print(f"  - Content-Type: {content_type}")
        print(f"  - Content-Disposition: {content_disp}")
    
    def test_enrollment_proof_invalid_id_returns_404(self, headers):
        """Invalid enrollment ID should return 404"""
        response = requests.get(f"{BASE_URL}/api/enrollment/review/{EMPLOYER_ID}/proof/invalid-id-12345", headers=headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Invalid enrollment ID correctly returns 404")


class TestEligibilityEndpoint:
    """Test GET /api/enrollment/eligibility/{employer_id}"""
    
    def test_eligibility_returns_200(self, headers):
        """Eligibility endpoint should return 200"""
        response = requests.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print(f"✓ Eligibility endpoint returned 200")
    
    def test_eligibility_has_required_fields(self, headers):
        """Eligibility should have total, eligible, ineligible, results"""
        response = requests.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "total" in data, "Missing total field"
        assert "eligible" in data, "Missing eligible field"
        assert "ineligible" in data, "Missing ineligible field"
        assert "results" in data, "Missing results array"
        
        print(f"✓ Eligibility has all required fields")
        print(f"  - total: {data['total']}")
        print(f"  - eligible: {data['eligible']}")
        print(f"  - ineligible: {data['ineligible']}")
    
    def test_eligibility_results_structure(self, headers):
        """Each eligibility result should have employee_name, hours, salary, affordable, offer_code"""
        response = requests.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            pytest.skip("No eligibility results to validate")
        
        for result in results:
            assert "employee_name" in result, "Result missing employee_name"
            assert "weekly_hours" in result, "Result missing weekly_hours"
            assert "annual_salary" in result, "Result missing annual_salary"
            assert "eligible" in result, "Result missing eligible"
            assert "offer_code" in result, "Result missing offer_code"
        
        print(f"✓ All {len(results)} eligibility results have valid structure")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
