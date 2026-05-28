"""
Carrier Integration API Tests
Tests for insurance carrier integration endpoints:
- GET /api/carriers - List available carriers
- GET /api/carriers/{carrier_id}/plans - Get carrier plans
- POST /api/carriers/connect/{employer_id} - Connect employer to carrier
- GET /api/carriers/connection/{employer_id} - Get connection status
- POST /api/carriers/sync/{employer_id} - Sync enrollment data
- GET /api/carriers/sync-history/{employer_id} - Get sync history
- GET /api/carriers/sync-detail/{sync_id} - Get sync detail
- DELETE /api/carriers/disconnect/{employer_id} - Disconnect carrier
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@demo.com"
TEST_PASSWORD = "test123"

# Carrier IDs
CARRIER_IDS = ["bcbs", "uhc", "aetna", "cigna", "humana"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["token"]


@pytest.fixture(scope="module")
def headers(auth_token):
    """Return headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def employer_id(headers):
    """Get the employer ID for the test user."""
    response = requests.get(f"{BASE_URL}/api/employers", headers=headers)
    assert response.status_code == 200
    employers = response.json()
    assert len(employers) > 0, "No employers found"
    return employers[0]["id"]


class TestCarrierList:
    """Tests for GET /api/carriers - List available carriers"""
    
    def test_list_carriers_returns_5_carriers(self, headers):
        """Verify that 5 carriers are returned (bcbs, uhc, aetna, cigna, humana)"""
        response = requests.get(f"{BASE_URL}/api/carriers", headers=headers)
        assert response.status_code == 200
        
        carriers = response.json()
        assert len(carriers) == 5, f"Expected 5 carriers, got {len(carriers)}"
        
        carrier_ids = [c["id"] for c in carriers]
        for expected_id in CARRIER_IDS:
            assert expected_id in carrier_ids, f"Missing carrier: {expected_id}"
    
    def test_carrier_structure(self, headers):
        """Verify carrier data structure has required fields"""
        response = requests.get(f"{BASE_URL}/api/carriers", headers=headers)
        assert response.status_code == 200
        
        carriers = response.json()
        for carrier in carriers:
            assert "id" in carrier
            assert "name" in carrier
            assert "short_name" in carrier
            assert "plan_count" in carrier
            assert isinstance(carrier["plan_count"], int)
            assert carrier["plan_count"] > 0
    
    def test_bcbs_has_3_plans(self, headers):
        """Verify BCBS has 3 plans (PPO, HMO, HDHP)"""
        response = requests.get(f"{BASE_URL}/api/carriers", headers=headers)
        assert response.status_code == 200
        
        carriers = response.json()
        bcbs = next((c for c in carriers if c["id"] == "bcbs"), None)
        assert bcbs is not None
        assert bcbs["plan_count"] == 3
    
    def test_carriers_require_auth(self):
        """Verify carriers endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/carriers")
        # API returns 403 Forbidden when no auth token provided
        assert response.status_code in [401, 403]


class TestCarrierPlans:
    """Tests for GET /api/carriers/{carrier_id}/plans"""
    
    def test_get_bcbs_plans(self, headers):
        """Verify BCBS plans are returned with correct structure"""
        response = requests.get(f"{BASE_URL}/api/carriers/bcbs/plans", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "carrier" in data
        assert "plans" in data
        assert data["carrier"]["id"] == "bcbs"
        assert data["carrier"]["name"] == "Blue Cross Blue Shield"
        
        plans = data["plans"]
        assert len(plans) == 3
        
        plan_names = [p["name"] for p in plans]
        assert "Blue Choice PPO" in plan_names
        assert "Blue Preferred HMO" in plan_names
        assert "Blue HDHP with HSA" in plan_names
    
    def test_plan_structure(self, headers):
        """Verify plan data has required fields"""
        response = requests.get(f"{BASE_URL}/api/carriers/bcbs/plans", headers=headers)
        assert response.status_code == 200
        
        plans = response.json()["plans"]
        for plan in plans:
            assert "name" in plan
            assert "type" in plan
            assert "individual_deductible" in plan
            assert "family_deductible" in plan
            assert "coinsurance_rate" in plan
            assert "office_visit_copay" in plan
            assert "er_copay" in plan
            assert "oop_max_individual" in plan
            assert "oop_max_family" in plan
    
    def test_all_carriers_have_plans(self, headers):
        """Verify all 5 carriers return plans"""
        for carrier_id in CARRIER_IDS:
            response = requests.get(f"{BASE_URL}/api/carriers/{carrier_id}/plans", headers=headers)
            assert response.status_code == 200, f"Failed for carrier: {carrier_id}"
            data = response.json()
            assert len(data["plans"]) > 0, f"No plans for carrier: {carrier_id}"
    
    def test_invalid_carrier_returns_404(self, headers):
        """Verify invalid carrier ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/carriers/invalid_carrier/plans", headers=headers)
        assert response.status_code == 404


class TestCarrierConnection:
    """Tests for carrier connection endpoints"""
    
    def test_get_connection_status(self, headers, employer_id):
        """Verify connection status endpoint returns correct structure"""
        response = requests.get(f"{BASE_URL}/api/carriers/connection/{employer_id}", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        # Should have 'connected' field
        assert "connected" in data
        
        if data["connected"]:
            assert "carrier_id" in data
            assert "carrier_name" in data
            assert "status" in data
            assert data["status"] == "connected"
    
    def test_connection_for_nonexistent_employer(self, headers):
        """Verify connection status for non-existent employer returns not connected"""
        fake_employer_id = str(uuid.uuid4())
        response = requests.get(f"{BASE_URL}/api/carriers/connection/{fake_employer_id}", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["connected"] == False


class TestCarrierSync:
    """Tests for carrier sync endpoints"""
    
    def test_sync_history(self, headers, employer_id):
        """Verify sync history endpoint returns list of sync logs"""
        response = requests.get(f"{BASE_URL}/api/carriers/sync-history/{employer_id}", headers=headers)
        assert response.status_code == 200
        
        history = response.json()
        assert isinstance(history, list)
        
        if len(history) > 0:
            log = history[0]
            assert "id" in log
            assert "employer_id" in log
            assert "carrier_id" in log
            assert "carrier_name" in log
            assert "total_employees" in log
            assert "results" in log
            assert "synced_at" in log
            
            # Verify results structure
            results = log["results"]
            assert "enrolled" in results
            assert "waived" in results
            assert "not_offered" in results
            assert "plans_created" in results
            assert "employees_updated" in results
    
    def test_sync_detail(self, headers, employer_id):
        """Verify sync detail endpoint returns full sync data with enrollments"""
        # First get sync history to get a sync_id
        history_response = requests.get(f"{BASE_URL}/api/carriers/sync-history/{employer_id}", headers=headers)
        assert history_response.status_code == 200
        
        history = history_response.json()
        if len(history) == 0:
            pytest.skip("No sync history available")
        
        sync_id = history[0]["id"]
        
        # Get sync detail
        response = requests.get(f"{BASE_URL}/api/carriers/sync-detail/{sync_id}", headers=headers)
        assert response.status_code == 200
        
        detail = response.json()
        assert "id" in detail
        assert "enrollments" in detail
        assert isinstance(detail["enrollments"], list)
        
        if len(detail["enrollments"]) > 0:
            enrollment = detail["enrollments"][0]
            assert "employee_id" in enrollment
            assert "employee_name" in enrollment
            assert "enrolled" in enrollment
            assert "enrollment_status" in enrollment
    
    def test_sync_detail_invalid_id(self, headers):
        """Verify sync detail with invalid ID returns 404"""
        response = requests.get(f"{BASE_URL}/api/carriers/sync-detail/invalid-sync-id", headers=headers)
        assert response.status_code == 404


class TestCarrierConnectDisconnect:
    """Tests for connect/disconnect flow - uses a fresh employer to avoid affecting existing data"""
    
    @pytest.fixture
    def test_employer_id(self, headers):
        """Create a test employer for connect/disconnect tests"""
        unique_name = f"TEST_Carrier_Employer_{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{BASE_URL}/api/employers", headers=headers, json={
            "name": unique_name,
            "ein": f"99-{uuid.uuid4().hex[:7]}",
            "address": "123 Test St",
            "city": "Test City",
            "state": "CA",
            "zip_code": "90210",
            "contact_name": "Test Contact",
            "contact_email": f"test_{uuid.uuid4().hex[:6]}@test.com",
            "contact_phone": "555-0100",
            "industry": "Technology",
            "employee_count": 10,
            "aca_status": "ALE"
        })
        # API returns 200 or 201 for successful creation
        assert response.status_code in [200, 201], f"Failed to create test employer: {response.text}"
        employer = response.json()
        yield employer["id"]
        
        # Cleanup: delete test employer
        requests.delete(f"{BASE_URL}/api/employers/{employer['id']}", headers=headers)
    
    def test_connect_carrier(self, headers, test_employer_id):
        """Test connecting an employer to a carrier"""
        response = requests.post(
            f"{BASE_URL}/api/carriers/connect/{test_employer_id}",
            headers=headers,
            json={
                "carrier_id": "uhc",
                "group_number": "TEST-GRP-001"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["carrier_id"] == "uhc"
        assert data["carrier_name"] == "UnitedHealthcare"
        assert data["status"] == "connected"
        assert data["group_number"] == "TEST-GRP-001"
        
        # Verify connection via GET
        conn_response = requests.get(f"{BASE_URL}/api/carriers/connection/{test_employer_id}", headers=headers)
        assert conn_response.status_code == 200
        conn_data = conn_response.json()
        assert conn_data["connected"] == True
        assert conn_data["carrier_id"] == "uhc"
    
    def test_connect_invalid_carrier(self, headers, test_employer_id):
        """Test connecting to invalid carrier returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/carriers/connect/{test_employer_id}",
            headers=headers,
            json={"carrier_id": "invalid_carrier"}
        )
        assert response.status_code == 404
    
    def test_connect_invalid_employer(self, headers):
        """Test connecting invalid employer returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/carriers/connect/{str(uuid.uuid4())}",
            headers=headers,
            json={"carrier_id": "bcbs"}
        )
        assert response.status_code == 404
    
    def test_disconnect_carrier(self, headers, test_employer_id):
        """Test disconnecting a carrier"""
        # First connect
        requests.post(
            f"{BASE_URL}/api/carriers/connect/{test_employer_id}",
            headers=headers,
            json={"carrier_id": "aetna"}
        )
        
        # Then disconnect
        response = requests.delete(f"{BASE_URL}/api/carriers/disconnect/{test_employer_id}", headers=headers)
        assert response.status_code == 200
        
        # Verify disconnected
        conn_response = requests.get(f"{BASE_URL}/api/carriers/connection/{test_employer_id}", headers=headers)
        assert conn_response.status_code == 200
        assert conn_response.json()["connected"] == False
    
    def test_disconnect_not_connected(self, headers, test_employer_id):
        """Test disconnecting when not connected returns 404"""
        # Ensure not connected
        requests.delete(f"{BASE_URL}/api/carriers/disconnect/{test_employer_id}", headers=headers)
        
        # Try to disconnect again
        response = requests.delete(f"{BASE_URL}/api/carriers/disconnect/{test_employer_id}", headers=headers)
        assert response.status_code == 404


class TestCarrierSyncExecution:
    """Tests for sync execution - uses existing connected employer"""
    
    def test_sync_returns_enrollment_data(self, headers, employer_id):
        """Test that sync returns enrollment data with correct structure"""
        # Check if connected first
        conn_response = requests.get(f"{BASE_URL}/api/carriers/connection/{employer_id}", headers=headers)
        if not conn_response.json().get("connected"):
            pytest.skip("Employer not connected to carrier")
        
        response = requests.post(f"{BASE_URL}/api/carriers/sync/{employer_id}", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "sync_id" in data
        assert "carrier_name" in data
        assert "total_employees" in data
        assert "results" in data
        assert "enrollments" in data
        assert "synced_at" in data
        
        # Verify results structure
        results = data["results"]
        assert "enrolled" in results
        assert "waived" in results
        assert "not_offered" in results
        assert "plans_created" in results
        assert "employees_updated" in results
        
        # Verify totals add up
        total = results["enrolled"] + results["waived"] + results["not_offered"]
        assert total == data["total_employees"], f"Totals don't match: {total} != {data['total_employees']}"
    
    def test_sync_creates_plans_if_needed(self, headers, employer_id):
        """Test that sync creates plans from carrier data"""
        conn_response = requests.get(f"{BASE_URL}/api/carriers/connection/{employer_id}", headers=headers)
        if not conn_response.json().get("connected"):
            pytest.skip("Employer not connected to carrier")
        
        response = requests.post(f"{BASE_URL}/api/carriers/sync/{employer_id}", headers=headers)
        assert response.status_code == 200
        
        # plans_created should be 0 if plans already exist, or > 0 if new
        results = response.json()["results"]
        assert "plans_created" in results
        assert isinstance(results["plans_created"], int)
    
    def test_sync_updates_employees(self, headers, employer_id):
        """Test that sync updates employee records"""
        conn_response = requests.get(f"{BASE_URL}/api/carriers/connection/{employer_id}", headers=headers)
        if not conn_response.json().get("connected"):
            pytest.skip("Employer not connected to carrier")
        
        response = requests.post(f"{BASE_URL}/api/carriers/sync/{employer_id}", headers=headers)
        assert response.status_code == 200
        
        results = response.json()["results"]
        assert results["employees_updated"] > 0
    
    def test_sync_without_connection_fails(self, headers):
        """Test that sync without carrier connection returns 400"""
        # Create a new employer without carrier connection
        unique_name = f"TEST_NoCarrier_{uuid.uuid4().hex[:8]}"
        create_response = requests.post(f"{BASE_URL}/api/employers", headers=headers, json={
            "name": unique_name,
            "ein": f"88-{uuid.uuid4().hex[:7]}",
            "address": "456 Test Ave",
            "city": "Test Town",
            "state": "NY",
            "zip_code": "10001",
            "contact_name": "No Carrier",
            "contact_email": f"nocarrier_{uuid.uuid4().hex[:6]}@test.com",
            "contact_phone": "555-0200",
            "industry": "Healthcare",
            "employee_count": 5,
            "aca_status": "ALE"
        })
        
        if create_response.status_code != 201:
            pytest.skip("Could not create test employer")
        
        new_employer_id = create_response.json()["id"]
        
        try:
            # Try to sync without connection
            response = requests.post(f"{BASE_URL}/api/carriers/sync/{new_employer_id}", headers=headers)
            assert response.status_code == 400
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/employers/{new_employer_id}", headers=headers)


class TestDuplicatePlanPrevention:
    """Test that duplicate syncs don't create duplicate plans"""
    
    def test_second_sync_no_new_plans(self, headers, employer_id):
        """Verify that running sync twice doesn't create duplicate plans"""
        conn_response = requests.get(f"{BASE_URL}/api/carriers/connection/{employer_id}", headers=headers)
        if not conn_response.json().get("connected"):
            pytest.skip("Employer not connected to carrier")
        
        # First sync
        first_response = requests.post(f"{BASE_URL}/api/carriers/sync/{employer_id}", headers=headers)
        assert first_response.status_code == 200
        
        # Second sync
        second_response = requests.post(f"{BASE_URL}/api/carriers/sync/{employer_id}", headers=headers)
        assert second_response.status_code == 200
        
        # Second sync should create 0 new plans (they already exist)
        second_results = second_response.json()["results"]
        assert second_results["plans_created"] == 0, "Duplicate plans were created"


class TestEmployeeDataPersistence:
    """Test that employee records are actually updated after sync"""
    
    def test_employee_has_plan_assignment(self, headers, employer_id):
        """Verify employee records have plan assignments after sync"""
        conn_response = requests.get(f"{BASE_URL}/api/carriers/connection/{employer_id}", headers=headers)
        if not conn_response.json().get("connected"):
            pytest.skip("Employer not connected to carrier")
        
        # Run sync
        sync_response = requests.post(f"{BASE_URL}/api/carriers/sync/{employer_id}", headers=headers)
        assert sync_response.status_code == 200
        
        enrollments = sync_response.json()["enrollments"]
        enrolled_employees = [e for e in enrollments if e["enrolled"]]
        
        if len(enrolled_employees) == 0:
            pytest.skip("No enrolled employees in sync")
        
        # Get an enrolled employee's ID
        enrolled_emp = enrolled_employees[0]
        emp_id = enrolled_emp["employee_id"]
        
        # Fetch payroll employee to verify plan assignment (sync updates payroll_employees)
        payroll_response = requests.get(f"{BASE_URL}/api/payroll/{employer_id}", headers=headers)
        
        if payroll_response.status_code == 200:
            payroll_data = payroll_response.json()
            # Find the enrolled employee in payroll data
            emp_data = next((e for e in payroll_data if e.get("id") == emp_id), None)
            if emp_data:
                # Verify plan assignment fields exist
                assert "plan_id" in emp_data or "plan_name" in emp_data, "Employee missing plan assignment"
                # Enrolled employees should have plan_name
                assert emp_data.get("plan_name") is not None, "Enrolled employee missing plan_name"
