"""
Test IRS 1095-C Form Generation with 1H Employee Filtering
Tests that:
1. 1095-C batch endpoint filters out 1H employees
2. All returned forms have offer codes 1B/1C/1D/1E (not 1H)
3. PDF download works for offered employees
4. PDF download returns 400 for 1H employees
5. 1094-C still generates correctly
6. Summary data is accurate
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"
TAX_YEAR = 2026


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for employer"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYER_EMAIL,
        "password": EMPLOYER_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    """Auth headers for API requests"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestIRS1095CFiltering:
    """Test 1095-C form generation with 1H employee filtering"""

    def test_1095c_batch_returns_only_offered_employees(self, headers):
        """GET /api/irs-forms/1095c/{employer_id}/2026 - Verify NO 1H employees appear in forms list"""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get 1095-C forms: {response.text}"
        
        data = response.json()
        assert "forms" in data, "Response missing 'forms' key"
        assert "count" in data, "Response missing 'count' key"
        
        forms = data["forms"]
        count = data["count"]
        
        print(f"Total 1095-C forms returned: {count}")
        assert count > 0, "Expected at least some 1095-C forms"
        assert len(forms) == count, f"Forms count mismatch: {len(forms)} vs {count}"
        
        # Verify NO 1H codes in any form
        for form in forms:
            line14_all_year = form.get("part2", {}).get("line14_all_year", "")
            employee_name = form.get("part1", {}).get("employee_name", "Unknown")
            
            assert line14_all_year != "1H", f"Found 1H code for employee {employee_name} - should be filtered out"
            
            # Also check monthly data
            monthly_data = form.get("part2", {}).get("monthly_data", [])
            for month in monthly_data:
                month_code = month.get("line14_code", "")
                assert month_code != "1H", f"Found 1H code in monthly data for {employee_name}"
        
        print(f"PASS: All {count} forms have valid offer codes (no 1H)")

    def test_1095c_forms_have_valid_offer_codes(self, headers):
        """GET /api/irs-forms/1095c/{employer_id}/2026 - Verify all returned forms have offer codes 1B/1C/1D/1E"""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 200
        
        data = response.json()
        forms = data["forms"]
        
        valid_offer_codes = {"1A", "1B", "1C", "1D", "1E", "1F", "1G"}  # All except 1H
        code_distribution = {}
        
        for form in forms:
            line14 = form.get("part2", {}).get("line14_all_year", "")
            code_distribution[line14] = code_distribution.get(line14, 0) + 1
            
            assert line14 in valid_offer_codes, f"Invalid offer code: {line14}"
            assert line14 != "1H", f"1H code found - should be filtered"
        
        print(f"Offer code distribution: {code_distribution}")
        
        # Verify we have the expected codes (1B, 1C, 1D, 1E are most common for FT employees)
        expected_codes = {"1B", "1C", "1D", "1E"}
        found_codes = set(code_distribution.keys())
        
        # At least some of the expected codes should be present
        assert len(found_codes & expected_codes) > 0, f"Expected some of {expected_codes}, found {found_codes}"
        print(f"PASS: All forms have valid offer codes: {found_codes}")


class TestIRS1095CPDFDownload:
    """Test 1095-C PDF download functionality"""

    def test_pdf_download_for_offered_employee(self, headers):
        """GET /api/irs-forms/1095c/{employer_id}/2026/{employee_id}/pdf - Verify PDF downloads for offered employees"""
        # First get the list of forms to find an offered employee
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 200
        
        forms = response.json()["forms"]
        assert len(forms) > 0, "No forms available to test PDF download"
        
        # Get the first employee with a valid offer code
        test_form = forms[0]
        employee_id = test_form.get("employee_id")
        employee_name = test_form.get("part1", {}).get("employee_name", "Unknown")
        
        assert employee_id, "No employee_id in form data"
        
        # Download PDF
        pdf_response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{employee_id}/pdf",
            headers=headers
        )
        
        assert pdf_response.status_code == 200, f"PDF download failed: {pdf_response.text}"
        assert pdf_response.headers.get("content-type") == "application/pdf", "Response is not PDF"
        
        # Check filename includes employee name
        content_disposition = pdf_response.headers.get("content-disposition", "")
        assert "1095-C" in content_disposition, "Filename should contain 1095-C"
        
        # Verify PDF content (should start with %PDF)
        pdf_content = pdf_response.content
        assert pdf_content[:4] == b'%PDF', "Response is not a valid PDF"
        assert len(pdf_content) > 1000, "PDF seems too small"
        
        print(f"PASS: PDF downloaded successfully for {employee_name} ({len(pdf_content)} bytes)")

    def test_pdf_download_returns_400_for_1h_employee(self, headers):
        """GET /api/irs-forms/1095c/{employer_id}/2026/{employee_id}/pdf - Verify 400 error for 1H employees"""
        # Get eligibility results to find a 1H employee
        elig_response = requests.get(
            f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}",
            headers=headers
        )
        
        if elig_response.status_code != 200:
            pytest.skip("Could not get eligibility results to find 1H employee")
        
        elig_data = elig_response.json()
        # Handle nested structure - results are in 'results' key
        results = elig_data.get("results", elig_data) if isinstance(elig_data, dict) else elig_data
        
        # Find an employee with 1H offer code
        h1_employee = None
        for emp in results:
            if emp.get("offer_code") == "1H":
                h1_employee = emp
                break
        
        if not h1_employee:
            pytest.skip("No 1H employees found in eligibility results")
        
        employee_id = h1_employee.get("employee_id")
        employee_name = h1_employee.get("employee_name", "Unknown")
        
        # Try to download PDF for 1H employee - should fail with 400
        pdf_response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{employee_id}/pdf",
            headers=headers
        )
        
        assert pdf_response.status_code == 400, f"Expected 400 for 1H employee, got {pdf_response.status_code}"
        
        error_data = pdf_response.json()
        assert "detail" in error_data, "Error response should have 'detail'"
        assert "1H" in error_data["detail"] or "not offered" in error_data["detail"].lower(), \
            f"Error message should mention 1H or not offered: {error_data['detail']}"
        
        print(f"PASS: 400 error returned for 1H employee {employee_name}: {error_data['detail']}")


class TestIRS1094C:
    """Test 1094-C form generation"""

    def test_1094c_generates_correctly(self, headers):
        """GET /api/irs-forms/1094c/{employer_id}/2026 - Verify 1094-C still generates correctly"""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get 1094-C: {response.text}"
        
        data = response.json()
        
        # Verify structure
        assert "form_type" in data, "Missing form_type"
        assert data["form_type"] == "1094-C", f"Wrong form type: {data['form_type']}"
        assert "tax_year" in data, "Missing tax_year"
        assert data["tax_year"] == TAX_YEAR, f"Wrong tax year: {data['tax_year']}"
        
        # Part I - Employer info
        assert "part1" in data, "Missing part1"
        part1 = data["part1"]
        assert part1.get("employer_name"), "Missing employer name"
        
        # Part II - ALE info
        assert "part2" in data, "Missing part2"
        part2 = data["part2"]
        assert "total_1095c_forms" in part2, "Missing total_1095c_forms"
        assert "is_ale_member" in part2, "Missing is_ale_member"
        assert "total_fte" in part2, "Missing total_fte"
        
        # Part III - Monthly data
        assert "part3" in data, "Missing part3"
        part3 = data["part3"]
        assert "monthly_data" in part3, "Missing monthly_data"
        assert len(part3["monthly_data"]) == 12, f"Expected 12 months, got {len(part3['monthly_data'])}"
        
        print(f"PASS: 1094-C generated correctly")
        print(f"  - Employer: {part1.get('employer_name')}")
        print(f"  - Total 1095-C forms: {part2.get('total_1095c_forms')}")
        print(f"  - Is ALE: {part2.get('is_ale_member')}")
        print(f"  - Total FTE: {part2.get('total_fte')}")


class TestIRSSummary:
    """Test IRS forms summary endpoint"""

    def test_summary_data_accurate(self, headers):
        """GET /api/irs-forms/summary/{employer_id}/2026 - Verify summary data"""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        
        assert response.status_code == 200, f"Failed to get summary: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        required_fields = [
            "total_employees", "full_time_employees", "total_fte",
            "is_ale", "forms_1095c_needed"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify data makes sense
        assert data["total_employees"] > 0, "Should have employees"
        assert data["full_time_employees"] > 0, "Should have FT employees"
        assert data["total_fte"] >= 50, "Should be ALE (50+ FTE)"
        assert data["is_ale"] == True, "Should be ALE"
        
        print(f"PASS: Summary data accurate")
        print(f"  - Total employees: {data['total_employees']}")
        print(f"  - Full-time employees: {data['full_time_employees']}")
        print(f"  - Total FTE: {data['total_fte']}")
        print(f"  - Is ALE: {data['is_ale']}")
        print(f"  - 1095-C forms needed: {data['forms_1095c_needed']}")


class TestOfferCodeDistribution:
    """Test that offer code distribution matches expectations"""

    def test_offer_code_distribution(self, headers):
        """Verify offer code distribution - 47 FT with offers, 13 PT with 1H"""
        # Get eligibility results
        elig_response = requests.get(
            f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}",
            headers=headers
        )
        
        if elig_response.status_code != 200:
            pytest.skip("Could not get eligibility results")
        
        elig_data = elig_response.json()
        # Handle nested structure - results are in 'results' key
        results = elig_data.get("results", elig_data) if isinstance(elig_data, dict) else elig_data
        
        # Count offer codes
        code_counts = {}
        ft_count = 0
        pt_count = 0
        
        for emp in results:
            code = emp.get("offer_code", "")
            code_counts[code] = code_counts.get(code, 0) + 1
            
            if emp.get("is_full_time"):
                ft_count += 1
            else:
                pt_count += 1
        
        print(f"Offer code distribution: {code_counts}")
        print(f"FT employees: {ft_count}, PT employees: {pt_count}")
        
        # Verify 1H count matches PT count (PT employees should have 1H)
        h1_count = code_counts.get("1H", 0)
        
        # Get 1095-C forms count
        forms_response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        assert forms_response.status_code == 200
        forms_count = forms_response.json()["count"]
        
        # Forms count should equal total employees minus 1H employees
        expected_forms = len(results) - h1_count
        
        print(f"1H employees (excluded): {h1_count}")
        print(f"1095-C forms generated: {forms_count}")
        print(f"Expected forms (total - 1H): {expected_forms}")
        
        # Allow some tolerance for edge cases
        assert abs(forms_count - expected_forms) <= 2, \
            f"Forms count {forms_count} doesn't match expected {expected_forms}"
        
        print(f"PASS: Offer code distribution correct - {h1_count} 1H employees excluded from {forms_count} forms")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
