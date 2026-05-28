"""
Test IRS Offer Codes and 1095-C/1094-C Form Generation
Tests the critical ACA compliance requirement that offer codes reflect what was OFFERED,
not just what was enrolled in.

Key test scenarios:
- FT employees with plans available should get 1B/1C/1D/1E (not 1H)
- PT employees should get 1H (no offer)
- Declined coverage should still show the offer code for what was offered
- 1095-C Line 14 should match eligibility-calculated offer codes
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


class TestIRSOfferCodes:
    """Test IRS Offer Code assignment and 1095-C/1094-C form generation"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        if response.status_code == 200:
            token = response.json().get("token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip(f"Login failed: {response.status_code}")
    
    # ==========================================
    # ELIGIBILITY ENDPOINT TESTS
    # ==========================================
    
    def test_get_eligibility_returns_200(self):
        """GET /api/enrollment/eligibility/{employer_id} should return 200"""
        response = self.session.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "results" in data, "Response should contain 'results' array"
        assert "total" in data, "Response should contain 'total' count"
        print(f"✓ Eligibility endpoint returns 200 with {data['total']} employees")
    
    def test_eligibility_results_have_offer_codes(self):
        """Eligibility results should have offer_code field"""
        response = self.session.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        
        assert len(results) > 0, "Should have at least one eligibility result"
        
        # Check that all results have offer_code
        for r in results:
            assert "offer_code" in r, f"Employee {r.get('employee_name')} missing offer_code"
            assert r["offer_code"] in ["1A", "1B", "1C", "1D", "1E", "1F", "1G", "1H"], \
                f"Invalid offer code: {r['offer_code']}"
        
        print(f"✓ All {len(results)} eligibility results have valid offer codes")
    
    def test_ft_employees_not_1h_when_plans_available(self):
        """Full-time employees should NOT get 1H if medical plans are available"""
        response = self.session.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        
        # Check plans are available
        plans_response = self.session.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}")
        assert plans_response.status_code == 200
        plans = plans_response.json()
        medical_plans = [p for p in plans if p.get("category") == "medical" and p.get("status") == "active"]
        
        if len(medical_plans) == 0:
            pytest.skip("No active medical plans available")
        
        # FT employees with plans available should NOT have 1H
        ft_with_1h = []
        ft_with_valid_codes = []
        for r in results:
            if r.get("is_full_time"):
                if r.get("offer_code") == "1H":
                    ft_with_1h.append(r.get("employee_name"))
                else:
                    ft_with_valid_codes.append((r.get("employee_name"), r.get("offer_code")))
        
        # This is the critical test - FT employees should have 1B/1C/1D/1E, not 1H
        assert len(ft_with_1h) == 0, \
            f"FT employees incorrectly assigned 1H (no offer): {ft_with_1h[:5]}... ({len(ft_with_1h)} total)"
        
        print(f"✓ {len(ft_with_valid_codes)} FT employees have correct offer codes (not 1H)")
        print(f"  Sample codes: {ft_with_valid_codes[:5]}")
    
    def test_pt_employees_get_1h(self):
        """Part-time employees should get 1H (no offer)"""
        response = self.session.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        
        pt_employees = [r for r in results if not r.get("is_full_time")]
        
        if len(pt_employees) == 0:
            pytest.skip("No part-time employees in test data")
        
        for r in pt_employees:
            assert r.get("offer_code") == "1H", \
                f"PT employee {r.get('employee_name')} should have 1H, got {r.get('offer_code')}"
        
        print(f"✓ All {len(pt_employees)} PT employees correctly have 1H offer code")
    
    # ==========================================
    # RUN ELIGIBILITY ENGINE TESTS
    # ==========================================
    
    def test_run_eligibility_engine(self):
        """POST /api/enrollment/eligibility/run/{employer_id} should recalculate offer codes"""
        response = self.session.post(f"{BASE_URL}/api/enrollment/eligibility/run/{EMPLOYER_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "total_employees" in data, "Response should contain total_employees"
        assert "eligible" in data, "Response should contain eligible count"
        assert "results" in data, "Response should contain results array"
        
        print(f"✓ Eligibility engine ran: {data['total_employees']} employees, {data['eligible']} eligible")
    
    def test_eligibility_engine_assigns_correct_codes(self):
        """After running eligibility engine, FT employees should have proper offer codes"""
        # Run the engine
        run_response = self.session.post(f"{BASE_URL}/api/enrollment/eligibility/run/{EMPLOYER_ID}")
        assert run_response.status_code == 200
        
        # Get results
        response = self.session.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert response.status_code == 200
        data = response.json()
        results = data.get("results", [])
        
        # Count offer code distribution
        code_counts = {}
        for r in results:
            code = r.get("offer_code", "unknown")
            code_counts[code] = code_counts.get(code, 0) + 1
        
        print(f"✓ Offer code distribution after engine run: {code_counts}")
        
        # Verify FT employees don't have 1H
        ft_results = [r for r in results if r.get("is_full_time")]
        ft_1h_count = sum(1 for r in ft_results if r.get("offer_code") == "1H")
        
        # Check if plans exist
        plans_response = self.session.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}")
        plans = plans_response.json() if plans_response.status_code == 200 else []
        medical_plans = [p for p in plans if p.get("category") == "medical" and p.get("status") == "active"]
        
        if len(medical_plans) > 0:
            assert ft_1h_count == 0, \
                f"{ft_1h_count} FT employees have 1H despite {len(medical_plans)} medical plans available"
    
    # ==========================================
    # 1095-C FORM TESTS
    # ==========================================
    
    def test_get_1095c_forms_returns_200(self):
        """GET /api/irs-forms/1095c/{employer_id}/{tax_year} should return 200"""
        response = self.session.get(f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "forms" in data, "Response should contain 'forms' array"
        assert "count" in data, "Response should contain 'count'"
        assert "tax_year" in data, "Response should contain 'tax_year'"
        
        print(f"✓ 1095-C endpoint returns {data['count']} forms for tax year {data['tax_year']}")
    
    def test_1095c_line14_matches_eligibility_offer_codes(self):
        """1095-C Line 14 codes should match eligibility-calculated offer codes"""
        # Get eligibility results
        elig_response = self.session.get(f"{BASE_URL}/api/enrollment/eligibility/{EMPLOYER_ID}")
        assert elig_response.status_code == 200
        elig_data = elig_response.json()
        elig_map = {r["employee_id"]: r["offer_code"] for r in elig_data.get("results", [])}
        
        # Get 1095-C forms
        forms_response = self.session.get(f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}")
        assert forms_response.status_code == 200
        forms_data = forms_response.json()
        forms = forms_data.get("forms", [])
        
        if len(forms) == 0:
            pytest.skip("No 1095-C forms generated")
        
        mismatches = []
        matches = []
        for form in forms:
            emp_id = form.get("employee_id")
            line14 = form.get("part2", {}).get("line14_all_year", "")
            expected = elig_map.get(emp_id, "")
            
            if expected and line14 != expected:
                mismatches.append({
                    "employee": form.get("part1", {}).get("employee_name"),
                    "line14": line14,
                    "expected": expected
                })
            else:
                matches.append((form.get("part1", {}).get("employee_name"), line14))
        
        assert len(mismatches) == 0, \
            f"Line 14 mismatches found: {mismatches[:5]}"
        
        print(f"✓ All {len(matches)} 1095-C forms have Line 14 matching eligibility offer codes")
        print(f"  Sample: {matches[:3]}")
    
    def test_1095c_ft_employees_not_1h_or_1f(self):
        """1095-C Line 14 for FT employees should NOT be 1H or 1F if MEC+MV plans available"""
        # Check plans
        plans_response = self.session.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}")
        assert plans_response.status_code == 200
        plans = plans_response.json()
        
        # Check for MEC+MV plans
        mec_mv_plans = [p for p in plans 
                       if p.get("category") == "medical" 
                       and p.get("status") == "active"
                       and p.get("mec_qualified", False)
                       and (p.get("mv_percentage") or 0) >= 60]
        
        if len(mec_mv_plans) == 0:
            pytest.skip("No MEC+MV qualified plans available")
        
        # Get 1095-C forms
        forms_response = self.session.get(f"{BASE_URL}/api/irs-forms/1095c/{EMPLOYER_ID}/{TAX_YEAR}")
        assert forms_response.status_code == 200
        forms = forms_response.json().get("forms", [])
        
        invalid_codes = []
        valid_codes = []
        for form in forms:
            line14 = form.get("part2", {}).get("line14_all_year", "")
            emp_name = form.get("part1", {}).get("employee_name", "")
            
            if line14 in ["1H", "1F"]:
                invalid_codes.append((emp_name, line14))
            else:
                valid_codes.append((emp_name, line14))
        
        # With MEC+MV plans available, FT employees should have 1A/1B/1C/1D/1E
        assert len(invalid_codes) == 0, \
            f"FT employees with 1H/1F despite MEC+MV plans: {invalid_codes[:5]}"
        
        print(f"✓ All {len(valid_codes)} 1095-C forms have valid offer codes (1A-1E)")
    
    # ==========================================
    # 1094-C FORM TESTS
    # ==========================================
    
    def test_get_1094c_form_returns_200(self):
        """GET /api/irs-forms/1094c/{employer_id}/{tax_year} should return 200"""
        response = self.session.get(f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "form_type" in data, "Response should contain 'form_type'"
        assert data["form_type"] == "1094-C", "Form type should be 1094-C"
        assert "tax_year" in data, "Response should contain 'tax_year'"
        assert "part1" in data, "Response should contain 'part1'"
        assert "part2" in data, "Response should contain 'part2'"
        assert "summary" in data, "Response should contain 'summary'"
        
        print(f"✓ 1094-C form generated for tax year {data['tax_year']}")
        print(f"  Summary: {data.get('summary', {})}")
    
    def test_1094c_summary_uses_plan_library(self):
        """1094-C summary should use plan_library count, not legacy plans"""
        # Get plan library count
        plans_response = self.session.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}")
        assert plans_response.status_code == 200
        plan_library_count = len(plans_response.json())
        
        # Get 1094-C
        response = self.session.get(f"{BASE_URL}/api/irs-forms/1094c/{EMPLOYER_ID}/{TAX_YEAR}")
        assert response.status_code == 200
        data = response.json()
        
        summary = data.get("summary", {})
        plans_count = summary.get("plans_count", 0)
        
        # The 1094-C should reflect plan_library count
        assert plans_count == plan_library_count, \
            f"1094-C plans_count ({plans_count}) doesn't match plan_library ({plan_library_count})"
        
        print(f"✓ 1094-C summary correctly shows {plans_count} plans from plan_library")
    
    # ==========================================
    # IRS FORMS SUMMARY TESTS
    # ==========================================
    
    def test_get_irs_forms_summary(self):
        """GET /api/irs-forms/summary/{employer_id}/{tax_year} should return summary"""
        response = self.session.get(f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "total_employees" in data, "Response should contain total_employees"
        assert "full_time_employees" in data, "Response should contain full_time_employees"
        assert "plans_count" in data, "Response should contain plans_count"
        
        print(f"✓ IRS Forms summary: {data['total_employees']} employees, {data['full_time_employees']} FT, {data['plans_count']} plans")
    
    def test_irs_summary_plans_from_plan_library(self):
        """IRS summary should get plans from plan_library collection"""
        # Get plan library
        plans_response = self.session.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}")
        assert plans_response.status_code == 200
        plan_library = plans_response.json()
        active_plans = [p for p in plan_library if p.get("status") == "active"]
        
        # Get IRS summary
        response = self.session.get(f"{BASE_URL}/api/irs-forms/summary/{EMPLOYER_ID}/{TAX_YEAR}")
        assert response.status_code == 200
        data = response.json()
        
        assert data["plans_count"] == len(active_plans), \
            f"IRS summary plans_count ({data['plans_count']}) != plan_library active ({len(active_plans)})"
        
        print(f"✓ IRS summary correctly uses plan_library: {len(active_plans)} active plans")
    
    # ==========================================
    # PLAN LIBRARY TESTS
    # ==========================================
    
    def test_get_plan_library(self):
        """GET /api/enrollment/plans/{employer_id} should return plans"""
        response = self.session.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        plans = response.json()
        
        assert isinstance(plans, list), "Response should be a list"
        
        if len(plans) > 0:
            plan = plans[0]
            assert "id" in plan, "Plan should have 'id'"
            assert "plan_name" in plan, "Plan should have 'plan_name'"
            assert "category" in plan, "Plan should have 'category'"
            
            print(f"✓ Plan library returns {len(plans)} plans")
            print(f"  Sample: {plan.get('plan_name')} ({plan.get('category')})")
        else:
            print("✓ Plan library returns empty list (no plans configured)")
    
    def test_plan_compliance_check(self):
        """POST /api/enrollment/plans/{plan_id}/compliance-check should work"""
        # Get a plan
        plans_response = self.session.get(f"{BASE_URL}/api/enrollment/plans/{EMPLOYER_ID}")
        assert plans_response.status_code == 200
        plans = plans_response.json()
        
        if len(plans) == 0:
            pytest.skip("No plans available for compliance check")
        
        plan_id = plans[0]["id"]
        response = self.session.post(f"{BASE_URL}/api/enrollment/plans/{plan_id}/compliance-check")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "plan_id" in data, "Response should contain plan_id"
        assert "mec" in data, "Response should contain MEC check"
        assert "mv" in data, "Response should contain MV check"
        assert "affordability" in data, "Response should contain affordability check"
        
        print(f"✓ Compliance check for {data.get('plan_name')}")
        print(f"  MEC: {'PASS' if data['mec']['pass'] else 'FAIL'}")
        print(f"  MV: {'PASS' if data['mv']['pass'] else 'FAIL'} ({data['mv'].get('mv_percentage', 0)}%)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
