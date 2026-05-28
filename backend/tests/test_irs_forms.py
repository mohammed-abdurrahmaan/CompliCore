"""
IRS Forms 1094-C and 1095-C API Tests
Tests for IRS form generation, PDF download, and code reference endpoints.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials and data
TEST_EMAIL = "irstest@test.com"
TEST_PASSWORD = "test123"
EMPLOYER_ID = "b5d695f6-5b81-4ad9-8114-6ae84456d5fa"
TAX_YEAR = 2025

# Employee IDs from the test data
ALICE_EMPLOYEE_ID = "e024d118-0c64-46c3-a384-721562aab592"  # Enrolled, FT
BOB_EMPLOYEE_ID = "1843f04d-a031-4c1f-8ba8-f6fca2bea0fa"    # Not enrolled, FT


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "token" in data, "No token in login response"
    return data["token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    """Return headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


class TestIRSFormsSummary:
    """Tests for IRS Forms Summary endpoint."""

    def test_summary_endpoint_returns_200(self, headers):
        """GET /api/irs-forms/summary/{employer_id}/{tax_year} returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 200, f"Summary failed: {response.text}"

    def test_summary_contains_required_fields(self, headers):
        """Summary response contains all required fields."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        
        required_fields = [
            "employer_id", "employer_name", "tax_year",
            "total_employees", "full_time_employees", "part_time_employees",
            "total_fte", "is_ale", "mec_offered_count", "enrolled_count",
            "plans_count", "forms_1095c_needed"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_summary_employee_counts_correct(self, headers):
        """Summary shows correct employee counts (2 FT employees)."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        
        assert data["full_time_employees"] == 2, f"Expected 2 FT employees, got {data['full_time_employees']}"
        assert data["total_employees"] == 2, f"Expected 2 total employees, got {data['total_employees']}"
        assert data["forms_1095c_needed"] == 2, f"Expected 2 1095-C forms needed, got {data['forms_1095c_needed']}"

    def test_summary_mec_counts_correct(self, headers):
        """Summary shows correct MEC offered/enrolled counts."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        
        # Both employees have offered_mec=true, but only Alice is enrolled
        assert data["mec_offered_count"] == 2, f"Expected 2 MEC offered, got {data['mec_offered_count']}"
        assert data["enrolled_count"] == 1, f"Expected 1 enrolled, got {data['enrolled_count']}"

    def test_summary_invalid_employer_returns_404(self, headers):
        """Summary with invalid employer_id returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/summary/invalid-employer-id/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 404


class TestIRSCodesReference:
    """Tests for IRS Codes reference endpoint."""

    def test_codes_endpoint_returns_200(self, headers):
        """GET /api/irs-forms/codes returns 200."""
        response = requests.get(f"{BASE_URL}/api/irs-forms/codes", headers=headers)
        assert response.status_code == 200, f"Codes endpoint failed: {response.text}"

    def test_codes_contains_line14_codes(self, headers):
        """Codes response contains Line 14 offer codes."""
        response = requests.get(f"{BASE_URL}/api/irs-forms/codes", headers=headers)
        data = response.json()
        
        assert "line14_codes" in data, "Missing line14_codes"
        line14 = data["line14_codes"]
        
        # Check key codes exist
        expected_codes = ["1A", "1B", "1C", "1D", "1E", "1F", "1G", "1H"]
        for code in expected_codes:
            assert code in line14, f"Missing Line 14 code: {code}"

    def test_codes_contains_line16_codes(self, headers):
        """Codes response contains Line 16 safe harbor codes."""
        response = requests.get(f"{BASE_URL}/api/irs-forms/codes", headers=headers)
        data = response.json()
        
        assert "line16_codes" in data, "Missing line16_codes"
        line16 = data["line16_codes"]
        
        # Check key codes exist
        expected_codes = ["2A", "2B", "2C", "2F", "2G", "2H"]
        for code in expected_codes:
            assert code in line16, f"Missing Line 16 code: {code}"


class TestForm1094C:
    """Tests for Form 1094-C generation endpoint."""

    def test_1094c_generation_returns_200(self, headers):
        """GET /api/irs-forms/1094c/{employer_id}/{tax_year} returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 200, f"1094-C generation failed: {response.text}"

    def test_1094c_contains_required_parts(self, headers):
        """1094-C response contains Part I, II, III, IV."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        
        assert data["form_type"] == "1094-C", f"Wrong form type: {data.get('form_type')}"
        assert data["tax_year"] == TAX_YEAR, f"Wrong tax year: {data.get('tax_year')}"
        assert "part1" in data, "Missing part1"
        assert "part2" in data, "Missing part2"
        assert "part3" in data, "Missing part3"
        assert "part4" in data, "Missing part4"

    def test_1094c_part1_employer_info(self, headers):
        """1094-C Part I contains correct employer information."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        part1 = data["part1"]
        
        assert part1["employer_name"] == "Test Corp", f"Wrong employer name: {part1.get('employer_name')}"
        assert part1["employer_ein"] == "12-3456789", f"Wrong EIN: {part1.get('employer_ein')}"

    def test_1094c_part2_ale_info(self, headers):
        """1094-C Part II contains ALE member information."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        part2 = data["part2"]
        
        assert "total_1095c_forms" in part2, "Missing total_1095c_forms"
        assert "is_ale_member" in part2, "Missing is_ale_member"
        assert "total_fte" in part2, "Missing total_fte"
        assert "mec_offered_to_pct" in part2, "Missing mec_offered_to_pct"
        
        # With 2 FT employees, should have 2 1095-C forms
        assert part2["total_1095c_forms"] == 2, f"Expected 2 1095-C forms, got {part2['total_1095c_forms']}"

    def test_1094c_part3_monthly_data(self, headers):
        """1094-C Part III contains 12 months of data."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        monthly = data["part3"]["monthly_data"]
        
        assert len(monthly) == 12, f"Expected 12 months, got {len(monthly)}"
        
        # Check first month structure
        jan = monthly[0]
        assert jan["month"] == 1, f"First month should be 1, got {jan['month']}"
        assert jan["month_name"] == "Jan", f"First month name should be Jan, got {jan['month_name']}"
        assert "ft_employee_count" in jan, "Missing ft_employee_count"
        assert "total_employee_count" in jan, "Missing total_employee_count"

    def test_1094c_invalid_employer_returns_404(self, headers):
        """1094-C with invalid employer_id returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/invalid-employer-id/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 404


class TestForm1095CBatch:
    """Tests for Form 1095-C batch generation endpoint."""

    def test_1095c_batch_returns_200(self, headers):
        """GET /api/irs-forms/1095c/{employer_id}/{tax_year} returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 200, f"1095-C batch failed: {response.text}"

    def test_1095c_batch_contains_forms_array(self, headers):
        """1095-C batch response contains forms array and count."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        
        assert "forms" in data, "Missing forms array"
        assert "count" in data, "Missing count"
        assert "tax_year" in data, "Missing tax_year"
        assert data["tax_year"] == TAX_YEAR

    def test_1095c_batch_generates_for_ft_employees(self, headers):
        """1095-C batch generates forms for all full-time employees."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        
        # Should have 2 forms (Alice and Bob are both FT)
        assert data["count"] == 2, f"Expected 2 forms, got {data['count']}"
        assert len(data["forms"]) == 2, f"Expected 2 forms in array, got {len(data['forms'])}"

    def test_1095c_batch_form_structure(self, headers):
        """Each 1095-C form has correct structure."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}",
            headers=headers
        )
        data = response.json()
        
        for form in data["forms"]:
            assert form["form_type"] == "1095-C", f"Wrong form type: {form.get('form_type')}"
            assert form["tax_year"] == TAX_YEAR
            assert "part1" in form, "Missing part1"
            assert "part2" in form, "Missing part2"
            assert "part3" in form, "Missing part3"
            assert "employee_id" in form, "Missing employee_id"

    def test_1095c_batch_invalid_employer_returns_404(self, headers):
        """1095-C batch with invalid employer_id returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/invalid-employer-id/{TAX_YEAR}",
            headers=headers
        )
        assert response.status_code == 404


class TestForm1095CSingle:
    """Tests for Form 1095-C single employee endpoint."""

    def test_1095c_single_returns_200(self, headers):
        """GET /api/irs-forms/1095c/{employer_id}/{tax_year}/{employee_id} returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}",
            headers=headers
        )
        assert response.status_code == 200, f"1095-C single failed: {response.text}"

    def test_1095c_single_alice_enrolled(self, headers):
        """1095-C for Alice (enrolled) has correct Line 16 code 2C."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}",
            headers=headers
        )
        data = response.json()
        
        assert data["part1"]["employee_name"] == "Alice Johnson"
        assert data["part2"]["line16_all_year"] == "2C", f"Expected 2C for enrolled, got {data['part2']['line16_all_year']}"

    def test_1095c_single_bob_not_enrolled(self, headers):
        """1095-C for Bob (not enrolled) has safe harbor code (2F/2G/2H)."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{BOB_EMPLOYEE_ID}",
            headers=headers
        )
        data = response.json()
        
        assert data["part1"]["employee_name"] == "Bob Martinez"
        # Bob is not enrolled, so should have a safe harbor code
        line16 = data["part2"]["line16_all_year"]
        assert line16 in ["2F", "2G", "2H", ""], f"Expected safe harbor code, got {line16}"

    def test_1095c_single_line14_code_for_ft_offered(self, headers):
        """1095-C Line 14 code is correct for FT employee with MEC offered."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}",
            headers=headers
        )
        data = response.json()
        
        line14 = data["part2"]["line14_all_year"]
        # Alice is FT, offered MEC, no spouse/dependents, premium $100 <= FPL threshold
        # Should be 1A (qualifying offer) or 1B (employee only)
        assert line14 in ["1A", "1B"], f"Expected 1A or 1B for FT with MEC, got {line14}"

    def test_1095c_single_monthly_data(self, headers):
        """1095-C single has 12 months of data."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}",
            headers=headers
        )
        data = response.json()
        monthly = data["part2"]["monthly_data"]
        
        assert len(monthly) == 12, f"Expected 12 months, got {len(monthly)}"
        
        # Check each month has required fields
        for m in monthly:
            assert "month" in m
            assert "month_name" in m
            assert "line14_code" in m
            assert "line15_premium" in m
            assert "line16_code" in m

    def test_1095c_single_invalid_employee_returns_404(self, headers):
        """1095-C single with invalid employee_id returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/invalid-employee-id",
            headers=headers
        )
        assert response.status_code == 404


class TestForm1094CPDF:
    """Tests for Form 1094-C PDF download endpoint."""

    def test_1094c_pdf_returns_200(self, headers):
        """GET /api/irs-forms/1094c/{employer_id}/{tax_year}/pdf returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}/pdf",
            headers=headers
        )
        assert response.status_code == 200, f"1094-C PDF failed: {response.text}"

    def test_1094c_pdf_content_type(self, headers):
        """1094-C PDF has correct content type."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}/pdf",
            headers=headers
        )
        assert "application/pdf" in response.headers.get("Content-Type", ""), \
            f"Wrong content type: {response.headers.get('Content-Type')}"

    def test_1094c_pdf_has_content_disposition(self, headers):
        """1094-C PDF has Content-Disposition header with filename."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}/pdf",
            headers=headers
        )
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Missing attachment in Content-Disposition"
        assert "1094-C" in content_disp, "Missing 1094-C in filename"
        assert str(TAX_YEAR) in content_disp, "Missing tax year in filename"

    def test_1094c_pdf_is_valid_pdf(self, headers):
        """1094-C PDF content starts with PDF magic bytes."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}/pdf",
            headers=headers
        )
        # PDF files start with %PDF
        assert response.content[:4] == b'%PDF', "Content is not a valid PDF"

    def test_1094c_pdf_invalid_employer_returns_404(self, headers):
        """1094-C PDF with invalid employer_id returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/invalid-employer-id/{TAX_YEAR}/pdf",
            headers=headers
        )
        assert response.status_code == 404


class TestForm1095CPDF:
    """Tests for Form 1095-C PDF download endpoint."""

    def test_1095c_pdf_returns_200(self, headers):
        """GET /api/irs-forms/1095c/{employer_id}/{tax_year}/{employee_id}/pdf returns 200."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}/pdf",
            headers=headers
        )
        assert response.status_code == 200, f"1095-C PDF failed: {response.text}"

    def test_1095c_pdf_content_type(self, headers):
        """1095-C PDF has correct content type."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}/pdf",
            headers=headers
        )
        assert "application/pdf" in response.headers.get("Content-Type", ""), \
            f"Wrong content type: {response.headers.get('Content-Type')}"

    def test_1095c_pdf_has_content_disposition(self, headers):
        """1095-C PDF has Content-Disposition header with filename."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}/pdf",
            headers=headers
        )
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp, "Missing attachment in Content-Disposition"
        assert "1095-C" in content_disp, "Missing 1095-C in filename"

    def test_1095c_pdf_is_valid_pdf(self, headers):
        """1095-C PDF content starts with PDF magic bytes."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}/pdf",
            headers=headers
        )
        # PDF files start with %PDF
        assert response.content[:4] == b'%PDF', "Content is not a valid PDF"

    def test_1095c_pdf_invalid_employee_returns_404(self, headers):
        """1095-C PDF with invalid employee_id returns 404."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/invalid-employee-id/pdf",
            headers=headers
        )
        assert response.status_code == 404


class TestIRSCodeLogic:
    """Tests for IRS code determination logic."""

    def test_line14_1a_qualifying_offer(self, headers):
        """Line 14 code 1A for qualifying offer (affordable + MV + self-only <= FPL)."""
        # Alice has premium $100/mo which is <= FPL threshold ($113.20)
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}",
            headers=headers
        )
        data = response.json()
        
        # Alice: FT, offered MEC, no spouse/dependents, premium $100 <= $113.20
        line14 = data["part2"]["line14_all_year"]
        # Should be 1A (qualifying offer) since premium is affordable
        assert line14 == "1A", f"Expected 1A for qualifying offer, got {line14}"

    def test_line16_2c_enrolled(self, headers):
        """Line 16 code 2C for employee enrolled in coverage."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{ALICE_EMPLOYEE_ID}",
            headers=headers
        )
        data = response.json()
        
        # Alice is enrolled
        line16 = data["part2"]["line16_all_year"]
        assert line16 == "2C", f"Expected 2C for enrolled employee, got {line16}"

    def test_line16_safe_harbor_not_enrolled(self, headers):
        """Line 16 code is safe harbor (2F/2G/2H) for not enrolled employee."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}/{BOB_EMPLOYEE_ID}",
            headers=headers
        )
        data = response.json()
        
        # Bob is not enrolled, should get safe harbor code
        line16 = data["part2"]["line16_all_year"]
        # Bob has premium $120/mo, FPL threshold is ~$113.20
        # So FPL safe harbor fails, but W-2 or Rate of Pay might pass
        # If no safe harbor passes, line16 could be empty
        assert line16 in ["2F", "2G", "2H", ""], f"Expected safe harbor or empty, got {line16}"


class TestAuthRequired:
    """Tests that endpoints require authentication."""

    def test_summary_requires_auth(self):
        """Summary endpoint requires authentication."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}"
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_1094c_requires_auth(self):
        """1094-C endpoint requires authentication."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}"
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_1095c_requires_auth(self):
        """1095-C endpoint requires authentication."""
        response = requests.get(
            f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}"
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"

    def test_codes_requires_auth(self):
        """Codes endpoint requires authentication."""
        response = requests.get(f"{BASE_URL}/api/irs-forms/codes")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
