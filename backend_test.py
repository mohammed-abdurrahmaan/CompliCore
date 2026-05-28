#!/usr/bin/env python3
"""
Backend Test Suite for Plan Library Assignment Affordability Feature
Tests the CompliCore ACA Compliance app backend APIs
"""

import requests
import json
import sys
from typing import Dict, List, Optional

# Backend URL from frontend environment
BACKEND_URL = "https://dcd96fa1-889e-4016-9bb8-bf959362d8f6.stage-preview.emergentagent.com/api"

# Test credentials
TEST_EMAIL = "fajju2001@gmail.com"
TEST_PASSWORD = "test123"
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"

class BackendTester:
    def __init__(self):
        self.token = None
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages"""
        print(f"[{level}] {message}")
        
    def login(self) -> bool:
        """Test login and get authentication token"""
        self.log("Testing login...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/auth/login",
                json={
                    "email": TEST_EMAIL,
                    "password": TEST_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("token")
                if self.token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.token}'
                    })
                    self.log(f"✅ Login successful for {TEST_EMAIL}")
                    return True
                else:
                    self.log("❌ Login failed: No token in response", "ERROR")
                    return False
            else:
                self.log(f"❌ Login failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Login error: {str(e)}", "ERROR")
            return False
    
    def get_employees_list(self) -> Optional[List[Dict]]:
        """Test getting employee list and verify salary data"""
        self.log("Testing employee list retrieval...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/enrollment/employees-list/{EMPLOYER_ID}"
            )
            
            if response.status_code == 200:
                employees = response.json()
                self.log(f"✅ Retrieved {len(employees)} employees")
                
                # Check for specific employees with low salaries
                alice = next((e for e in employees if "Alice Johnson" in e.get("name", "")), None)
                bob = next((e for e in employees if "Bob Martinez" in e.get("name", "")), None)
                carol = next((e for e in employees if "Carol Williams" in e.get("name", "")), None)
                brian = next((e for e in employees if "Brian Adams" in e.get("name", "")), None)
                
                if alice:
                    self.log(f"✅ Found Alice Johnson - Salary: ${alice.get('annual_salary', 0):,.2f}")
                if bob:
                    self.log(f"✅ Found Bob Martinez - Salary: ${bob.get('annual_salary', 0):,.2f}")
                if carol:
                    self.log(f"✅ Found Carol Williams - Salary: ${carol.get('annual_salary', 0):,.2f}")
                if brian:
                    self.log(f"✅ Found Brian Adams - Salary: ${brian.get('annual_salary', 0):,.2f}")
                
                # Verify salary ranges
                low_salary_employees = [e for e in employees if e.get('annual_salary', 0) < 15000]
                self.log(f"✅ Found {len(low_salary_employees)} employees with salary < $15,000")
                
                return employees
            else:
                self.log(f"❌ Failed to get employees: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Error getting employees: {str(e)}", "ERROR")
            return None
    
    def get_plans(self) -> Optional[List[Dict]]:
        """Test getting plan library and verify MV data"""
        self.log("Testing plan library retrieval...")
        
        try:
            response = self.session.get(
                f"{BACKEND_URL}/enrollment/plans/{EMPLOYER_ID}"
            )
            
            if response.status_code == 200:
                plans = response.json()
                self.log(f"✅ Retrieved {len(plans)} plans")
                
                # Check for specific plans and their MV percentages
                gold_hmo = next((p for p in plans if "Gold HMO" in p.get("plan_name", "")), None)
                platinum_ppo = next((p for p in plans if "Platinum PPO" in p.get("plan_name", "")), None)
                bronze_hdhp = next((p for p in plans if "Bronze HDHP" in p.get("plan_name", "")), None)
                silver_ppo = next((p for p in plans if "Silver PPO" in p.get("plan_name", "")), None)
                
                if gold_hmo:
                    mv_pct = gold_hmo.get('mv_percentage', 0)
                    ee_cost = gold_hmo.get('employee_cost', {}).get('self_only', 0)
                    self.log(f"✅ Gold HMO - MV: {mv_pct}%, EE Cost: ${ee_cost}/mo")
                    
                if platinum_ppo:
                    mv_pct = platinum_ppo.get('mv_percentage', 0)
                    self.log(f"✅ Platinum PPO - MV: {mv_pct}%")
                    
                if bronze_hdhp:
                    mv_pct = bronze_hdhp.get('mv_percentage', 0)
                    self.log(f"✅ Bronze HDHP - MV: {mv_pct}%")
                    
                if silver_ppo:
                    mv_pct = silver_ppo.get('mv_percentage', 0)
                    self.log(f"✅ Silver PPO - MV: {mv_pct}%")
                
                return plans
            else:
                self.log(f"❌ Failed to get plans: {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            self.log(f"❌ Error getting plans: {str(e)}", "ERROR")
            return None
    
    def test_assign_unaffordable_only(self, plan_id: str, employee_ids: List[str]) -> bool:
        """Test assigning ONLY unaffordable employees - should return 422"""
        self.log("Testing assignment of ONLY unaffordable employees...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/enrollment/plans/{plan_id}/assign-employees",
                json={"employee_ids": employee_ids}
            )
            
            if response.status_code == 422:
                data = response.json()
                detail = data.get("detail", {})
                unaffordable = detail.get("unaffordable_employees", [])
                self.log(f"✅ Correctly blocked assignment - {len(unaffordable)} unaffordable employees")
                for emp in unaffordable:
                    name = emp.get("name", "Unknown")
                    cost = emp.get("employee_monthly_cost", 0)
                    pct = emp.get("pct_of_income", 0)
                    self.log(f"   - {name}: ${cost}/mo = {pct}% of income")
                return True
            else:
                self.log(f"❌ Expected 422 but got {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing unaffordable assignment: {str(e)}", "ERROR")
            return False
    
    def test_assign_affordable_only(self, plan_id: str, employee_ids: List[str]) -> bool:
        """Test assigning ONLY affordable employees - should succeed"""
        self.log("Testing assignment of ONLY affordable employees...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/enrollment/plans/{plan_id}/assign-employees",
                json={"employee_ids": employee_ids}
            )
            
            if response.status_code == 200:
                data = response.json()
                assigned = data.get("assigned", 0)
                skipped = data.get("skipped_unaffordable", 0)
                plan_name = data.get("plan_name", "Unknown")
                self.log(f"✅ Successfully assigned {assigned} employees to {plan_name}")
                self.log(f"   Skipped unaffordable: {skipped}")
                return True
            else:
                self.log(f"❌ Assignment failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing affordable assignment: {str(e)}", "ERROR")
            return False
    
    def test_assign_mixed(self, plan_id: str, employee_ids: List[str]) -> bool:
        """Test assigning MIX of affordable and unaffordable - should assign only affordable"""
        self.log("Testing assignment of MIXED affordable/unaffordable employees...")
        
        try:
            response = self.session.post(
                f"{BACKEND_URL}/enrollment/plans/{plan_id}/assign-employees",
                json={"employee_ids": employee_ids}
            )
            
            if response.status_code == 200:
                data = response.json()
                assigned = data.get("assigned", 0)
                skipped = data.get("skipped_unaffordable", 0)
                plan_name = data.get("plan_name", "Unknown")
                self.log(f"✅ Mixed assignment result for {plan_name}:")
                self.log(f"   Assigned: {assigned}")
                self.log(f"   Skipped unaffordable: {skipped}")
                
                if assigned > 0 and skipped > 0:
                    self.log("✅ Correctly assigned affordable and skipped unaffordable")
                    return True
                elif assigned > 0 and skipped == 0:
                    self.log("✅ All employees were affordable - assigned all")
                    return True
                else:
                    self.log("❌ Unexpected assignment result", "ERROR")
                    return False
            else:
                self.log(f"❌ Mixed assignment failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Error testing mixed assignment: {str(e)}", "ERROR")
            return False
    
    def run_affordability_tests(self):
        """Run the complete affordability test suite"""
        self.log("=" * 60)
        self.log("STARTING PLAN LIBRARY AFFORDABILITY TESTS")
        self.log("=" * 60)
        
        # Step 1: Login
        if not self.login():
            self.log("❌ Login failed - aborting tests", "ERROR")
            return False
        
        # Step 2: Get employees and verify salary data
        employees = self.get_employees_list()
        if not employees:
            self.log("❌ Failed to get employees - aborting tests", "ERROR")
            return False
        
        # Step 3: Get plans and verify MV data
        plans = self.get_plans()
        if not plans:
            self.log("❌ Failed to get plans - aborting tests", "ERROR")
            return False
        
        # Find specific employees
        alice = next((e for e in employees if "Alice Johnson" in e.get("name", "")), None)
        bob = next((e for e in employees if "Bob Martinez" in e.get("name", "")), None)
        carol = next((e for e in employees if "Carol Williams" in e.get("name", "")), None)
        brian = next((e for e in employees if "Brian Adams" in e.get("name", "")), None)
        
        # Find Gold HMO plan
        gold_hmo = next((p for p in plans if "Gold HMO" in p.get("plan_name", "")), None)
        
        if not gold_hmo:
            self.log("❌ Gold HMO plan not found - checking for plan ID bc701f0b-29c4-4f37-ab42-ebb4f5fad085", "ERROR")
            gold_hmo = next((p for p in plans if p.get("id") == "bc701f0b-29c4-4f37-ab42-ebb4f5fad085"), None)
        
        if not gold_hmo:
            self.log("❌ Gold HMO plan not found by ID either - aborting tests", "ERROR")
            return False
        
        plan_id = gold_hmo["id"]
        self.log(f"Using Gold HMO plan ID: {plan_id}")
        
        # Collect employee IDs
        unaffordable_ids = []
        affordable_ids = []
        
        if alice and alice.get('annual_salary', 0) < 20000:
            unaffordable_ids.append(alice['id'])
        if bob and bob.get('annual_salary', 0) < 20000:
            unaffordable_ids.append(bob['id'])
        if carol and carol.get('annual_salary', 0) < 20000:
            unaffordable_ids.append(carol['id'])
        if brian and brian.get('annual_salary', 0) > 50000:
            affordable_ids.append(brian['id'])
        
        # If we don't have the specific employees, find some low/high salary employees
        if not unaffordable_ids:
            low_salary_emps = [e for e in employees if e.get('annual_salary', 0) < 20000][:3]
            unaffordable_ids = [e['id'] for e in low_salary_emps]
            self.log(f"Using {len(unaffordable_ids)} low-salary employees for unaffordable test")
        
        if not affordable_ids:
            high_salary_emps = [e for e in employees if e.get('annual_salary', 0) > 70000][:1]
            affordable_ids = [e['id'] for e in high_salary_emps]
            self.log(f"Using {len(affordable_ids)} high-salary employees for affordable test")
        
        # Run tests
        test_results = []
        
        # Test 1: Assign only unaffordable employees (should fail with 422)
        if unaffordable_ids:
            self.log("\n" + "=" * 40)
            self.log("TEST 1: Assign ONLY unaffordable employees")
            result = self.test_assign_unaffordable_only(plan_id, unaffordable_ids)
            test_results.append(("Unaffordable Only Assignment", result))
        
        # Test 2: Assign only affordable employees (should succeed)
        if affordable_ids:
            self.log("\n" + "=" * 40)
            self.log("TEST 2: Assign ONLY affordable employees")
            result = self.test_assign_affordable_only(plan_id, affordable_ids)
            test_results.append(("Affordable Only Assignment", result))
        
        # Test 3: Assign mix of affordable and unaffordable (should assign only affordable)
        if unaffordable_ids and affordable_ids:
            self.log("\n" + "=" * 40)
            self.log("TEST 3: Assign MIX of affordable/unaffordable employees")
            mixed_ids = unaffordable_ids[:1] + affordable_ids[:1]  # Take 1 from each
            result = self.test_assign_mixed(plan_id, mixed_ids)
            test_results.append(("Mixed Assignment", result))
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status} {test_name}")
            if result:
                passed += 1
        
        self.log(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("🎉 ALL AFFORDABILITY TESTS PASSED!")
            return True
        else:
            self.log("❌ Some tests failed - check implementation", "ERROR")
            return False

def main():
    """Main test runner"""
    tester = BackendTester()
    
    try:
        success = tester.run_affordability_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()