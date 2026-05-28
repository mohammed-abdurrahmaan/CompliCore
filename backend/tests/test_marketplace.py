"""
Actuary Marketplace Backend Tests
Tests the full quote/payment/certification lifecycle for MV certification.
Features tested:
- Actuary directory listing
- Quote request creation
- Quote accept/reject by actuary
- Payment processing (mock)
- Certification delivery
- Certification validation/rejection (resubmission flow)
- Notifications
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMPLOYER_EMAIL = f"test_marketplace_{uuid.uuid4().hex[:8]}@test.com"
TEST_EMPLOYER_PASSWORD = "test123"
TEST_ACTUARY_EMAIL = f"test_actuary_{uuid.uuid4().hex[:8]}@test.com"
TEST_ACTUARY_PASSWORD = "test123"


class TestActuaryMarketplace:
    """Test the Actuary Marketplace feature"""
    
    employer_token = None
    actuary_token = None
    employer_id = None
    plan_id = None
    quote_id = None
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        pass
    
    # --- Authentication Tests ---
    
    def test_01_register_employer(self):
        """Register a test employer user"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMPLOYER_EMAIL,
            "password": TEST_EMPLOYER_PASSWORD,
            "name": "Test Employer User",
            "role": "employer",
            "company_name": "Test Marketplace Corp"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "employer"
        TestActuaryMarketplace.employer_token = data["token"]
        print(f"✓ Employer registered: {TEST_EMPLOYER_EMAIL}")
    
    def test_02_register_actuary(self):
        """Register a test actuary user"""
        response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_ACTUARY_EMAIL,
            "password": TEST_ACTUARY_PASSWORD,
            "name": "Test Actuary User",
            "role": "actuary",
            "company_name": "Test Actuary Firm"
        })
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "actuary"
        TestActuaryMarketplace.actuary_token = data["token"]
        print(f"✓ Actuary registered: {TEST_ACTUARY_EMAIL}")
    
    # --- Actuary Directory Tests ---
    
    def test_03_get_actuary_marketplace_directory(self):
        """GET /api/actuary-marketplace returns 6 mock actuaries"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/actuary-marketplace", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 6, f"Expected 6 actuaries, got {len(data)}"
        
        # Verify actuary structure
        actuary = data[0]
        assert "id" in actuary
        assert "name" in actuary
        assert "firm" in actuary
        assert "price" in actuary
        assert "turnaround_days" in actuary
        assert "rating" in actuary
        assert "specialties" in actuary
        print(f"✓ Actuary directory has {len(data)} actuaries")
    
    def test_04_get_actuary_detail(self):
        """GET /api/actuary-marketplace/{id} returns actuary details"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/actuary-marketplace/act-1", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "act-1"
        assert data["name"] == "Jane Doe, MAAA, FSA"
        assert data["firm"] == "Doe Actuarial Services"
        print(f"✓ Actuary detail: {data['name']}")
    
    def test_05_get_actuary_not_found(self):
        """GET /api/actuary-marketplace/{invalid_id} returns 404"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/actuary-marketplace/invalid-id", headers=headers)
        assert response.status_code == 404
        print("✓ Invalid actuary returns 404")
    
    # --- Setup: Create Employer and Plan ---
    
    def test_06_create_employer(self):
        """Create a test employer"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.post(f"{BASE_URL}/api/employers", json={
            "name": "Marketplace Test Corp",
            "ein": "99-8765432",
            "address": "456 Test Ave",
            "employee_count": 100
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        TestActuaryMarketplace.employer_id = data["id"]
        print(f"✓ Employer created: {data['name']}")
    
    def test_07_create_plan(self):
        """Create a test plan for certification"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.post(f"{BASE_URL}/api/plans", json={
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Test Gold PPO 2025",
            "plan_type": "PPO",
            "individual_deductible": 1500,
            "family_deductible": 3000,
            "coinsurance_rate": 0.20,
            "office_visit_copay": 25,
            "er_copay": 250,
            "inpatient_copay": 500,
            "rx_copay_generic": 10,
            "rx_copay_brand": 40,
            "oop_max_individual": 6000,
            "oop_max_family": 12000
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        TestActuaryMarketplace.plan_id = data["id"]
        print(f"✓ Plan created: {data['plan_name']}")
    
    # --- Quote Request Tests ---
    
    def test_08_create_quote_request(self):
        """POST /api/marketplace/quotes creates a new quote request"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.post(f"{BASE_URL}/api/marketplace/quotes", json={
            "actuary_id": "act-1",
            "plan_id": TestActuaryMarketplace.plan_id,
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Test Gold PPO 2025",
            "message": "Please certify this plan for MV compliance"
        }, headers=headers)
        assert response.status_code == 200, f"Quote creation failed: {response.text}"
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert data["actuary_id"] == "act-1"
        assert data["plan_id"] == TestActuaryMarketplace.plan_id
        assert data["quoted_price"] > 0
        TestActuaryMarketplace.quote_id = data["id"]
        print(f"✓ Quote request created: {data['id']}")
    
    def test_09_duplicate_quote_request_fails(self):
        """POST /api/marketplace/quotes fails for duplicate active request"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.post(f"{BASE_URL}/api/marketplace/quotes", json={
            "actuary_id": "act-1",
            "plan_id": TestActuaryMarketplace.plan_id,
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Test Gold PPO 2025",
            "message": "Duplicate request"
        }, headers=headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
        print("✓ Duplicate quote request correctly rejected")
    
    def test_10_get_quotes_employer(self):
        """GET /api/marketplace/quotes returns employer's quotes"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/marketplace/quotes", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        quote = next((q for q in data if q["id"] == TestActuaryMarketplace.quote_id), None)
        assert quote is not None
        assert quote["status"] == "pending"
        print(f"✓ Employer has {len(data)} quote(s)")
    
    def test_11_get_quote_detail(self):
        """GET /api/marketplace/quotes/{id} returns quote details"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.quote_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TestActuaryMarketplace.quote_id
        assert data["status"] == "pending"
        assert "plan_details" in data
        print(f"✓ Quote detail retrieved: status={data['status']}")
    
    # --- Quote Response Tests (Actuary) ---
    
    def test_12_actuary_accept_quote(self):
        """PUT /api/marketplace/quotes/{id}/respond accepts a quote"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.quote_id}/respond", json={
            "action": "accept",
            "quoted_price": 3500,
            "turnaround_days": 10,
            "actuary_message": "Happy to help with this certification"
        }, headers=headers)
        assert response.status_code == 200, f"Accept failed: {response.text}"
        data = response.json()
        assert data["status"] == "accepted"
        assert data["quoted_price"] == 3500
        assert data["turnaround_days"] == 10
        print(f"✓ Quote accepted: price=${data['quoted_price']}, days={data['turnaround_days']}")
    
    def test_13_cannot_respond_to_accepted_quote(self):
        """PUT /api/marketplace/quotes/{id}/respond fails for non-pending quote"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.quote_id}/respond", json={
            "action": "accept",
            "quoted_price": 4000
        }, headers=headers)
        assert response.status_code == 400
        assert "not in pending" in response.json()["detail"].lower()
        print("✓ Cannot respond to non-pending quote")
    
    # --- Payment Tests ---
    
    def test_14_pay_quote(self):
        """PUT /api/marketplace/quotes/{id}/pay processes mock payment"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.quote_id}/pay", json={
            "payment_method": "platform"
        }, headers=headers)
        assert response.status_code == 200, f"Payment failed: {response.text}"
        data = response.json()
        assert data["status"] == "paid"
        assert data["payment_status"] == "paid"
        print(f"✓ Payment processed: status={data['status']}")
    
    def test_15_cannot_pay_already_paid(self):
        """PUT /api/marketplace/quotes/{id}/pay fails for already paid quote"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.quote_id}/pay", json={
            "payment_method": "platform"
        }, headers=headers)
        assert response.status_code == 400
        print("✓ Cannot pay already paid quote")
    
    # --- Certification Delivery Tests ---
    
    def test_16_deliver_certification(self):
        """PUT /api/marketplace/quotes/{id}/deliver delivers certification"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.quote_id}/deliver", json={
            "mv_percentage": 68.5,
            "certification_notes": "Plan meets MV requirements. Calculated using HHS methodology.",
            "document_name": "MV_Cert_Test_Gold_PPO.pdf"
        }, headers=headers)
        assert response.status_code == 200, f"Delivery failed: {response.text}"
        data = response.json()
        assert data["status"] == "delivered"
        assert data["certification"]["mv_percentage"] == 68.5
        assert data["certification"]["delivery_count"] == 1
        print(f"✓ Certification delivered: MV={data['certification']['mv_percentage']}%")
    
    def test_17_cannot_deliver_to_non_paid(self):
        """PUT /api/marketplace/quotes/{id}/deliver fails for non-paid quote"""
        # Create a new quote that's not paid
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        
        # Create another plan first
        plan_resp = requests.post(f"{BASE_URL}/api/plans", json={
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Test Silver Plan",
            "plan_type": "HMO",
            "individual_deductible": 2500,
            "family_deductible": 5000,
            "coinsurance_rate": 0.30,
            "office_visit_copay": 30,
            "er_copay": 300,
            "inpatient_copay": 600,
            "rx_copay_generic": 15,
            "rx_copay_brand": 50,
            "oop_max_individual": 7500,
            "oop_max_family": 15000
        }, headers=headers)
        new_plan_id = plan_resp.json()["id"]
        
        # Create quote
        quote_resp = requests.post(f"{BASE_URL}/api/marketplace/quotes", json={
            "actuary_id": "act-2",
            "plan_id": new_plan_id,
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Test Silver Plan",
            "message": "Test"
        }, headers=headers)
        new_quote_id = quote_resp.json()["id"]
        
        # Try to deliver without payment
        headers_actuary = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{new_quote_id}/deliver", json={
            "mv_percentage": 55.0,
            "certification_notes": "Test"
        }, headers=headers_actuary)
        assert response.status_code == 400
        print("✓ Cannot deliver to non-paid quote")
    
    # --- Validation Tests ---
    
    def test_18_validate_certification_accept(self):
        """PUT /api/marketplace/quotes/{id}/validate validates certification"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.quote_id}/validate", json={
            "valid": True
        }, headers=headers)
        assert response.status_code == 200, f"Validation failed: {response.text}"
        data = response.json()
        assert data["status"] == "validated"
        assert data["validation"]["valid"] == True
        print(f"✓ Certification validated: status={data['status']}")
    
    def test_19_verify_plan_updated_after_validation(self):
        """Verify plan MV is updated after certification validation"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/plans/detail/{TestActuaryMarketplace.plan_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["mv_calculated"] == True
        assert data["mv_percentage"] == 68.5
        assert data["mv_meets_minimum"] == True
        assert data["certification_source"] == "actuary"
        print(f"✓ Plan MV updated: {data['mv_percentage']}%, certified by actuary")
    
    # --- Resubmission Flow Tests ---
    
    def test_20_create_quote_for_resubmission_test(self):
        """Create a new quote for resubmission flow testing"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        
        # Create another plan
        plan_resp = requests.post(f"{BASE_URL}/api/plans", json={
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Resubmit Test Plan",
            "plan_type": "PPO",
            "individual_deductible": 2000,
            "family_deductible": 4000,
            "coinsurance_rate": 0.25,
            "office_visit_copay": 30,
            "er_copay": 300,
            "inpatient_copay": 500,
            "rx_copay_generic": 15,
            "rx_copay_brand": 45,
            "oop_max_individual": 7000,
            "oop_max_family": 14000
        }, headers=headers)
        resubmit_plan_id = plan_resp.json()["id"]
        
        # Create quote
        quote_resp = requests.post(f"{BASE_URL}/api/marketplace/quotes", json={
            "actuary_id": "act-3",
            "plan_id": resubmit_plan_id,
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Resubmit Test Plan",
            "message": "Testing resubmission flow"
        }, headers=headers)
        assert quote_resp.status_code == 200
        TestActuaryMarketplace.resubmit_quote_id = quote_resp.json()["id"]
        TestActuaryMarketplace.resubmit_plan_id = resubmit_plan_id
        print(f"✓ Resubmission test quote created")
    
    def test_21_accept_resubmit_quote(self):
        """Accept the resubmission test quote"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.resubmit_quote_id}/respond", json={
            "action": "accept",
            "quoted_price": 3000,
            "turnaround_days": 7
        }, headers=headers)
        assert response.status_code == 200
        print("✓ Resubmit quote accepted")
    
    def test_22_pay_resubmit_quote(self):
        """Pay for the resubmission test quote"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.resubmit_quote_id}/pay", json={
            "payment_method": "platform"
        }, headers=headers)
        assert response.status_code == 200
        print("✓ Resubmit quote paid")
    
    def test_23_deliver_resubmit_certification(self):
        """Deliver certification for resubmission test"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.resubmit_quote_id}/deliver", json={
            "mv_percentage": 58.0,
            "certification_notes": "Initial calculation - may need review",
            "document_name": "MV_Cert_Resubmit_Test.pdf"
        }, headers=headers)
        assert response.status_code == 200
        print("✓ Resubmit certification delivered")
    
    def test_24_reject_certification_for_resubmission(self):
        """PUT /api/marketplace/quotes/{id}/validate rejects certification"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.resubmit_quote_id}/validate", json={
            "valid": False,
            "rejection_reason": "MV calculation appears incorrect. Please recalculate with updated deductible values."
        }, headers=headers)
        assert response.status_code == 200, f"Rejection failed: {response.text}"
        data = response.json()
        assert data["status"] == "resubmit_needed"
        assert data["validation"]["valid"] == False
        assert "incorrect" in data["validation"]["rejection_reason"].lower()
        print(f"✓ Certification rejected for resubmission: status={data['status']}")
    
    def test_25_resubmit_certification(self):
        """PUT /api/marketplace/quotes/{id}/deliver resubmits certification"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.resubmit_quote_id}/deliver", json={
            "mv_percentage": 62.5,
            "certification_notes": "Recalculated with corrected deductible values. Plan now meets MV.",
            "document_name": "MV_Cert_Resubmit_Test_v2.pdf"
        }, headers=headers)
        assert response.status_code == 200, f"Resubmission failed: {response.text}"
        data = response.json()
        assert data["status"] == "delivered"
        assert data["certification"]["mv_percentage"] == 62.5
        assert data["certification"]["delivery_count"] == 2
        print(f"✓ Certification resubmitted: MV={data['certification']['mv_percentage']}%, delivery_count={data['certification']['delivery_count']}")
    
    def test_26_validate_resubmitted_certification(self):
        """Validate the resubmitted certification"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.resubmit_quote_id}/validate", json={
            "valid": True
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "validated"
        print(f"✓ Resubmitted certification validated")
    
    # --- Notification Tests ---
    
    def test_27_get_notifications_employer(self):
        """GET /api/notifications returns employer notifications"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "unread_count" in data
        assert isinstance(data["notifications"], list)
        print(f"✓ Employer has {len(data['notifications'])} notifications, {data['unread_count']} unread")
    
    def test_28_mark_all_notifications_read(self):
        """PUT /api/notifications/read-all marks all as read"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.put(f"{BASE_URL}/api/notifications/read-all", headers=headers)
        assert response.status_code == 200
        
        # Verify all are read
        check_resp = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
        assert check_resp.json()["unread_count"] == 0
        print("✓ All notifications marked as read")
    
    # --- Quote Rejection Flow ---
    
    def test_29_create_quote_for_rejection_test(self):
        """Create a quote to test rejection flow"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        
        # Create another plan
        plan_resp = requests.post(f"{BASE_URL}/api/plans", json={
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Rejection Test Plan",
            "plan_type": "HDHP",
            "individual_deductible": 3000,
            "family_deductible": 6000,
            "coinsurance_rate": 0.20,
            "office_visit_copay": 0,
            "er_copay": 0,
            "inpatient_copay": 0,
            "rx_copay_generic": 0,
            "rx_copay_brand": 0,
            "oop_max_individual": 7500,
            "oop_max_family": 15000
        }, headers=headers)
        reject_plan_id = plan_resp.json()["id"]
        
        # Create quote
        quote_resp = requests.post(f"{BASE_URL}/api/marketplace/quotes", json={
            "actuary_id": "act-4",
            "plan_id": reject_plan_id,
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Rejection Test Plan",
            "message": "Testing rejection flow"
        }, headers=headers)
        assert quote_resp.status_code == 200
        TestActuaryMarketplace.reject_quote_id = quote_resp.json()["id"]
        print("✓ Rejection test quote created")
    
    def test_30_actuary_reject_quote(self):
        """PUT /api/marketplace/quotes/{id}/respond rejects a quote"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.actuary_token}"}
        response = requests.put(f"{BASE_URL}/api/marketplace/quotes/{TestActuaryMarketplace.reject_quote_id}/respond", json={
            "action": "reject",
            "actuary_message": "Unable to take on this project at this time"
        }, headers=headers)
        assert response.status_code == 200, f"Rejection failed: {response.text}"
        data = response.json()
        assert data["status"] == "rejected"
        print(f"✓ Quote rejected by actuary: status={data['status']}")
    
    # --- Edge Cases ---
    
    def test_31_quote_not_found(self):
        """GET /api/marketplace/quotes/{invalid_id} returns 404"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.get(f"{BASE_URL}/api/marketplace/quotes/invalid-quote-id", headers=headers)
        assert response.status_code == 404
        print("✓ Invalid quote ID returns 404")
    
    def test_32_plan_not_found_for_quote(self):
        """POST /api/marketplace/quotes with invalid plan returns 404"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        response = requests.post(f"{BASE_URL}/api/marketplace/quotes", json={
            "actuary_id": "act-1",
            "plan_id": "invalid-plan-id",
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Invalid Plan",
            "message": "Test"
        }, headers=headers)
        assert response.status_code == 404
        print("✓ Invalid plan ID returns 404")
    
    def test_33_actuary_not_found_for_quote(self):
        """POST /api/marketplace/quotes with invalid actuary returns 404"""
        headers = {"Authorization": f"Bearer {TestActuaryMarketplace.employer_token}"}
        
        # Create a new plan for this test
        plan_resp = requests.post(f"{BASE_URL}/api/plans", json={
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Edge Case Plan",
            "plan_type": "PPO",
            "individual_deductible": 1000,
            "family_deductible": 2000,
            "coinsurance_rate": 0.20,
            "office_visit_copay": 20,
            "er_copay": 200,
            "inpatient_copay": 400,
            "rx_copay_generic": 10,
            "rx_copay_brand": 30,
            "oop_max_individual": 5000,
            "oop_max_family": 10000
        }, headers=headers)
        edge_plan_id = plan_resp.json()["id"]
        
        response = requests.post(f"{BASE_URL}/api/marketplace/quotes", json={
            "actuary_id": "invalid-actuary-id",
            "plan_id": edge_plan_id,
            "employer_id": TestActuaryMarketplace.employer_id,
            "plan_name": "Edge Case Plan",
            "message": "Test"
        }, headers=headers)
        assert response.status_code == 404
        print("✓ Invalid actuary ID returns 404")
    
    def test_34_unauthenticated_access_denied(self):
        """API endpoints require authentication"""
        response = requests.get(f"{BASE_URL}/api/actuary-marketplace")
        assert response.status_code in [401, 403]
        
        response = requests.get(f"{BASE_URL}/api/marketplace/quotes")
        assert response.status_code in [401, 403]
        
        response = requests.get(f"{BASE_URL}/api/notifications")
        assert response.status_code in [401, 403]
        print("✓ Unauthenticated access correctly denied")


class TestMVCalculatorMarketplaceCTA:
    """Test MV Calculator's Actuary Marketplace CTA"""
    
    def test_mv_calculate_form_needs_certification(self):
        """POST /api/mv/calculate-form returns needs_actuarial_certification flag"""
        # Register a user first
        email = f"mv_test_{uuid.uuid4().hex[:8]}@test.com"
        reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "test123",
            "name": "MV Test User",
            "role": "employer"
        })
        token = reg_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test with a plan that needs certification (high deductible, low MV)
        response = requests.post(f"{BASE_URL}/api/mv/calculate-form", json={
            "plan_name": "High Deductible Test",
            "plan_type": "HDHP",
            "individual_deductible": 8000,
            "family_deductible": 16000,
            "oop_max_individual": 9000,
            "oop_max_family": 18000,
            "coinsurance_rate": 40,
            "copay_primary": 0,
            "copay_specialist": 0,
            "copay_emergency": 0,
            "copay_generic_rx": 0,
            "copay_brand_rx": 0,
            "essential_health_benefits": True,
            "preventive_care_100": True,
            "hsa_eligible": True,
            "hsa_employer_contribution": 0,
            "hra_employer_contribution": 0
        }, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "mv_percentage" in data
        assert "needs_actuarial_certification" in data
        # High deductible plan should likely need certification
        print(f"✓ MV calculation: {data['mv_percentage']}%, needs_cert={data['needs_actuarial_certification']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
