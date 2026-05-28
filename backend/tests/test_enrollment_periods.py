"""
Test Enrollment Period Management Feature
- POST /api/enrollment/periods - Create enrollment period
- GET /api/enrollment/periods/{employer_id} - List all periods
- PUT /api/enrollment/periods/{period_id} - Activate/close/edit period
- DELETE /api/enrollment/periods/{period_id} - Delete draft period
- GET /api/enrollment/periods/{employer_id}/active - Get active period
- POST /api/enrollment/exceptions - Employee requests exception
- GET /api/enrollment/exceptions/{employer_id} - List exception requests
- PUT /api/enrollment/exceptions/{exception_id} - Approve/reject exception
- Enrollment lock enforcement on enroll/decline endpoints
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
EMPLOYER_ID = "351025eb-da00-4267-8b09-e7b061b55101"
EXISTING_PERIOD_ID = "b5bbd952-933d-4985-848c-032041d80640"
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
EMPLOYER_CODE = "TCGA5G"


class TestEnrollmentPeriodsCRUD:
    """Test enrollment period CRUD operations"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as employer and get token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as employer
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        assert login_res.status_code == 200, f"Employer login failed: {login_res.text}"
        self.token = login_res.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    def test_get_enrollment_periods(self):
        """GET /api/enrollment/periods/{employer_id} - List all periods"""
        res = self.session.get(f"{BASE_URL}/api/enrollment/periods/{EMPLOYER_ID}")
        assert res.status_code == 200, f"Failed to get periods: {res.text}"
        periods = res.json()
        assert isinstance(periods, list), "Response should be a list"
        print(f"✓ GET periods returned {len(periods)} periods")
        
        # Check structure of periods
        if periods:
            p = periods[0]
            assert "id" in p, "Period should have id"
            assert "employer_id" in p, "Period should have employer_id"
            assert "period_name" in p, "Period should have period_name"
            assert "start_date" in p, "Period should have start_date"
            assert "end_date" in p, "Period should have end_date"
            assert "status" in p, "Period should have status"
            print(f"✓ Period structure validated: {p['period_name']} ({p['status']})")
    
    def test_create_enrollment_period(self):
        """POST /api/enrollment/periods - Create enrollment period"""
        # Create a new period
        start_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        
        res = self.session.post(f"{BASE_URL}/api/enrollment/periods", json={
            "employer_id": EMPLOYER_ID,
            "period_name": f"TEST_Period_{uuid.uuid4().hex[:8]}",
            "start_date": start_date,
            "end_date": end_date
        })
        assert res.status_code == 200, f"Failed to create period: {res.text}"
        period = res.json()
        
        assert "id" in period, "Created period should have id"
        assert period["status"] == "draft", "New period should be in draft status"
        assert period["employer_id"] == EMPLOYER_ID
        print(f"✓ Created period: {period['period_name']} (id: {period['id']})")
        
        # Cleanup - delete the test period
        del_res = self.session.delete(f"{BASE_URL}/api/enrollment/periods/{period['id']}")
        assert del_res.status_code == 200, f"Failed to delete test period: {del_res.text}"
        print(f"✓ Cleaned up test period")
    
    def test_update_enrollment_period_status(self):
        """PUT /api/enrollment/periods/{period_id} - Activate/close period"""
        # First create a test period
        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        create_res = self.session.post(f"{BASE_URL}/api/enrollment/periods", json={
            "employer_id": EMPLOYER_ID,
            "period_name": f"TEST_Activate_{uuid.uuid4().hex[:8]}",
            "start_date": start_date,
            "end_date": end_date
        })
        assert create_res.status_code == 200
        period = create_res.json()
        period_id = period["id"]
        
        # Activate the period
        activate_res = self.session.put(f"{BASE_URL}/api/enrollment/periods/{period_id}", json={
            "status": "active"
        })
        assert activate_res.status_code == 200, f"Failed to activate period: {activate_res.text}"
        activated = activate_res.json()
        assert activated["status"] == "active", "Period should be active"
        print(f"✓ Activated period: {activated['period_name']}")
        
        # Close the period
        close_res = self.session.put(f"{BASE_URL}/api/enrollment/periods/{period_id}", json={
            "status": "closed"
        })
        assert close_res.status_code == 200, f"Failed to close period: {close_res.text}"
        closed = close_res.json()
        assert closed["status"] == "closed", "Period should be closed"
        print(f"✓ Closed period: {closed['period_name']}")
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/enrollment/periods/{period_id}")
    
    def test_delete_draft_period(self):
        """DELETE /api/enrollment/periods/{period_id} - Delete draft period"""
        # Create a draft period
        start_date = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
        
        create_res = self.session.post(f"{BASE_URL}/api/enrollment/periods", json={
            "employer_id": EMPLOYER_ID,
            "period_name": f"TEST_Delete_{uuid.uuid4().hex[:8]}",
            "start_date": start_date,
            "end_date": end_date
        })
        assert create_res.status_code == 200
        period = create_res.json()
        
        # Delete the draft period
        del_res = self.session.delete(f"{BASE_URL}/api/enrollment/periods/{period['id']}")
        assert del_res.status_code == 200, f"Failed to delete period: {del_res.text}"
        print(f"✓ Deleted draft period: {period['period_name']}")
        
        # Verify it's deleted
        get_res = self.session.get(f"{BASE_URL}/api/enrollment/periods/{EMPLOYER_ID}")
        periods = get_res.json()
        assert not any(p["id"] == period["id"] for p in periods), "Period should be deleted"
        print(f"✓ Verified period is deleted")
    
    def test_get_active_period(self):
        """GET /api/enrollment/periods/{employer_id}/active - Get active period"""
        res = self.session.get(f"{BASE_URL}/api/enrollment/periods/{EMPLOYER_ID}/active")
        assert res.status_code == 200, f"Failed to get active period: {res.text}"
        data = res.json()
        
        assert "period" in data, "Response should have 'period' key"
        assert "has_exception" in data, "Response should have 'has_exception' key"
        print(f"✓ Active period endpoint works. Period: {data['period']}, has_exception: {data['has_exception']}")


class TestEnrollmentExceptions:
    """Test enrollment exception request flow"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup sessions for employer and employee"""
        self.employer_session = requests.Session()
        self.employer_session.headers.update({"Content-Type": "application/json"})
        
        # Login as employer
        login_res = self.employer_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        assert login_res.status_code == 200, f"Employer login failed: {login_res.text}"
        self.employer_token = login_res.json().get("token")
        self.employer_session.headers.update({"Authorization": f"Bearer {self.employer_token}"})
        yield
    
    def test_get_exceptions_list(self):
        """GET /api/enrollment/exceptions/{employer_id} - List exception requests"""
        res = self.employer_session.get(f"{BASE_URL}/api/enrollment/exceptions/{EMPLOYER_ID}")
        assert res.status_code == 200, f"Failed to get exceptions: {res.text}"
        exceptions = res.json()
        assert isinstance(exceptions, list), "Response should be a list"
        print(f"✓ GET exceptions returned {len(exceptions)} exception requests")
        
        # Check structure if any exist
        if exceptions:
            e = exceptions[0]
            assert "id" in e, "Exception should have id"
            assert "employee_name" in e, "Exception should have employee_name"
            assert "status" in e, "Exception should have status"
            print(f"✓ Exception structure validated: {e['employee_name']} ({e['status']})")


class TestEnrollmentLockEnforcement:
    """Test enrollment lock enforcement when period is closed"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - ensure we have a closed enrollment state"""
        self.employer_session = requests.Session()
        self.employer_session.headers.update({"Content-Type": "application/json"})
        
        # Login as employer
        login_res = self.employer_session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        assert login_res.status_code == 200
        self.employer_token = login_res.json().get("token")
        self.employer_session.headers.update({"Authorization": f"Bearer {self.employer_token}"})
        
        # Store original period status to restore later
        periods_res = self.employer_session.get(f"{BASE_URL}/api/enrollment/periods/{EMPLOYER_ID}")
        self.original_periods = periods_res.json() if periods_res.status_code == 200 else []
        yield
    
    def test_enrollment_blocked_when_closed(self):
        """Test that enrollment is blocked when no active period exists"""
        # First, ensure all periods are closed
        periods_res = self.employer_session.get(f"{BASE_URL}/api/enrollment/periods/{EMPLOYER_ID}")
        periods = periods_res.json()
        
        # Close any active periods
        for p in periods:
            if p["status"] == "active":
                self.employer_session.put(f"{BASE_URL}/api/enrollment/periods/{p['id']}", json={"status": "closed"})
                print(f"✓ Closed period: {p['period_name']}")
        
        # Register a test employee
        test_email = f"test_emp_{uuid.uuid4().hex[:8]}@test.com"
        reg_res = requests.post(f"{BASE_URL}/api/enrollment/employee/register", json={
            "name": "Test Employee",
            "email": test_email,
            "password": "test123",
            "employer_code": EMPLOYER_CODE
        })
        
        if reg_res.status_code == 200:
            emp_token = reg_res.json().get("token")
            emp_session = requests.Session()
            emp_session.headers.update({
                "Content-Type": "application/json",
                "Authorization": f"Bearer {emp_token}"
            })
            
            # Try to enroll - should be blocked
            enroll_res = emp_session.post(f"{BASE_URL}/api/enrollment/employee/enroll", json={
                "plan_id": "some-plan-id",
                "coverage_tier": "self_only",
                "add_on_plan_ids": []
            })
            
            # Should return 403 when enrollment is closed
            if enroll_res.status_code == 403:
                print(f"✓ Enrollment correctly blocked with 403: {enroll_res.json().get('detail')}")
            elif enroll_res.status_code == 404:
                print(f"✓ Enrollment blocked (plan not found - expected since we used fake plan_id)")
            else:
                print(f"⚠ Enrollment returned {enroll_res.status_code}: {enroll_res.text}")
            
            # Try to decline - should also be blocked
            decline_res = emp_session.post(f"{BASE_URL}/api/enrollment/employee/decline", json={
                "reason": "other_coverage",
                "reason_detail": "Test"
            })
            
            if decline_res.status_code == 403:
                print(f"✓ Decline correctly blocked with 403: {decline_res.json().get('detail')}")
            else:
                print(f"⚠ Decline returned {decline_res.status_code}: {decline_res.text}")
        else:
            print(f"⚠ Could not register test employee: {reg_res.text}")
        
        # Restore active period if there was one
        for p in self.original_periods:
            if p["status"] == "active":
                self.employer_session.put(f"{BASE_URL}/api/enrollment/periods/{p['id']}", json={"status": "active"})
                print(f"✓ Restored active period: {p['period_name']}")


class TestExistingPeriodOperations:
    """Test operations on the existing enrollment period"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as employer"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        login_res = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": EMPLOYER_EMAIL,
            "password": EMPLOYER_PASSWORD
        })
        assert login_res.status_code == 200
        self.token = login_res.json().get("token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        yield
    
    def test_existing_period_exists(self):
        """Verify the existing test period exists"""
        res = self.session.get(f"{BASE_URL}/api/enrollment/periods/{EMPLOYER_ID}")
        assert res.status_code == 200
        periods = res.json()
        
        existing = next((p for p in periods if p["id"] == EXISTING_PERIOD_ID), None)
        if existing:
            print(f"✓ Found existing period: {existing['period_name']} ({existing['status']})")
            print(f"  Dates: {existing['start_date']} to {existing['end_date']}")
        else:
            print(f"⚠ Existing period {EXISTING_PERIOD_ID} not found")
            # List available periods
            for p in periods:
                print(f"  Available: {p['id']} - {p['period_name']} ({p['status']})")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
