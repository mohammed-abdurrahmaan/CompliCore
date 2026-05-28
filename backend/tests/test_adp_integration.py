"""
Test ADP Integration and Payroll Endpoints
Tests:
- ADP status endpoint (configured:false when no credentials)
- ADP auth-url endpoint (returns 400 when not configured)
- ADP disconnect endpoint
- Payroll summary with source field
- Payroll generate and delete
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

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
        data = response.json()
        return data.get("token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def employer_id(auth_token):
    """Get employer ID from user profile"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("employer_id")
    pytest.skip("Could not get employer ID")


@pytest.fixture
def api_client(auth_token):
    """Authenticated requests session"""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestADPStatus:
    """Test ADP connection status endpoint"""
    
    def test_adp_status_returns_configured_false(self, api_client, employer_id):
        """ADP status should return configured:false when no credentials set"""
        response = api_client.get(f"{BASE_URL}/api/adp/status/{employer_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "configured" in data, "Response should contain 'configured' field"
        assert data["configured"] == False, "ADP should not be configured (no credentials)"
        assert "connected" in data, "Response should contain 'connected' field"
        assert data["connected"] == False, "ADP should not be connected"
        assert "last_sync" in data, "Response should contain 'last_sync' field"
        assert "worker_count" in data, "Response should contain 'worker_count' field"
        print(f"ADP Status: {data}")


class TestADPAuthURL:
    """Test ADP auth URL endpoint"""
    
    def test_adp_auth_url_returns_400_when_not_configured(self, api_client, employer_id):
        """ADP auth-url should return 400 error when credentials not configured"""
        response = api_client.get(f"{BASE_URL}/api/adp/auth-url/{employer_id}")
        
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "detail" in data, "Error response should contain 'detail' field"
        assert "not configured" in data["detail"].lower() or "ADP" in data["detail"], \
            f"Error message should mention ADP not configured: {data['detail']}"
        print(f"ADP Auth URL Error (expected): {data}")


class TestADPDisconnect:
    """Test ADP disconnect endpoint"""
    
    def test_adp_disconnect_works_without_error(self, api_client, employer_id):
        """ADP disconnect should work even if not connected"""
        response = api_client.post(f"{BASE_URL}/api/adp/disconnect/{employer_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data, "Response should contain 'success' field"
        assert data["success"] == True, "Disconnect should succeed"
        print(f"ADP Disconnect: {data}")


class TestPayrollSummary:
    """Test payroll summary endpoint with source field"""
    
    def test_payroll_summary_returns_source_field(self, api_client, employer_id):
        """Payroll summary should include source field (mock or adp)"""
        response = api_client.get(f"{BASE_URL}/api/payroll/summary/{employer_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # If no payroll data, source should be "none"
        if not data.get("has_payroll"):
            assert "source" in data, "Response should contain 'source' field"
            assert data["source"] == "none", "Source should be 'none' when no payroll data"
            print(f"Payroll Summary (no data): {data}")
        else:
            assert "source" in data, "Response should contain 'source' field"
            assert data["source"] in ["mock", "adp"], f"Source should be 'mock' or 'adp', got: {data['source']}"
            print(f"Payroll Summary (has data): source={data['source']}, employees={data.get('total_employees')}")


class TestPayrollGenerate:
    """Test payroll generate and delete endpoints"""
    
    def test_payroll_generate_creates_mock_data(self, api_client, employer_id):
        """Generate mock payroll should create employees"""
        # First reset any existing payroll
        reset_response = api_client.delete(f"{BASE_URL}/api/payroll/{employer_id}")
        assert reset_response.status_code == 200, f"Reset failed: {reset_response.text}"
        
        # Generate mock payroll
        response = api_client.post(f"{BASE_URL}/api/payroll/generate/{employer_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "employees" in data, "Response should contain 'employees' field"
        assert "count" in data, "Response should contain 'count' field"
        assert data["count"] > 0, "Should generate at least one employee"
        assert len(data["employees"]) == data["count"], "Employee count should match"
        print(f"Generated {data['count']} mock employees")
    
    def test_payroll_summary_shows_mock_source_after_generate(self, api_client, employer_id):
        """After generating mock payroll, summary should show source:mock"""
        # Ensure mock data exists
        api_client.post(f"{BASE_URL}/api/payroll/generate/{employer_id}")
        
        response = api_client.get(f"{BASE_URL}/api/payroll/summary/{employer_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("has_payroll") == True, "Should have payroll data"
        assert data.get("source") == "mock", f"Source should be 'mock', got: {data.get('source')}"
        assert data.get("total_employees", 0) > 0, "Should have employees"
        print(f"Payroll Summary: source={data['source']}, total_employees={data['total_employees']}")


class TestPayrollDelete:
    """Test payroll delete/reset endpoint"""
    
    def test_payroll_delete_resets_data(self, api_client, employer_id):
        """Delete payroll should reset all employee data"""
        # First ensure we have data
        api_client.post(f"{BASE_URL}/api/payroll/generate/{employer_id}")
        
        # Delete payroll
        response = api_client.delete(f"{BASE_URL}/api/payroll/{employer_id}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "message" in data, "Response should contain 'message' field"
        print(f"Payroll Delete: {data}")
        
        # Verify payroll is empty
        summary_response = api_client.get(f"{BASE_URL}/api/payroll/summary/{employer_id}")
        summary_data = summary_response.json()
        assert summary_data.get("has_payroll") == False, "Payroll should be empty after delete"
        print(f"Verified payroll is empty: {summary_data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
