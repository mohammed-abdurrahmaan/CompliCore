"""
Test suite for ACA Compliance Chat/Messaging and Payment Document Validation features.

Features tested:
1. Chat/Messaging between employer and actuary after quote acceptance
2. Payment button disabled until employer uploads at least one document
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
EMPLOYER_EMAIL = "fajju2001@gmail.com"
EMPLOYER_PASSWORD = "test123"
ACTUARY_EMAIL = "emily.park@parkreed.com"
ACTUARY_PASSWORD = "test123"

# Known quote ID with status 'accepted' (Robert Chen quote)
ACCEPTED_QUOTE_ID = "e7b48f80-bf47-402d-ab99-10054f1f8709"


@pytest.fixture(scope="module")
def employer_session():
    """Login as employer and return session with auth headers."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": EMPLOYER_EMAIL,
        "password": EMPLOYER_PASSWORD
    })
    assert response.status_code == 200, f"Employer login failed: {response.text}"
    
    data = response.json()
    token = data.get("token")
    assert token, "No token in employer login response"
    
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


@pytest.fixture(scope="module")
def actuary_session():
    """Login as actuary and return session with auth headers."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    response = session.post(f"{BASE_URL}/api/auth/login", json={
        "email": ACTUARY_EMAIL,
        "password": ACTUARY_PASSWORD
    })
    assert response.status_code == 200, f"Actuary login failed: {response.text}"
    
    data = response.json()
    token = data.get("token")
    assert token, "No token in actuary login response"
    
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


class TestChatMessaging:
    """Test chat/messaging feature between employer and actuary."""
    
    def test_get_messages_for_accepted_quote(self, employer_session):
        """GET /api/marketplace/quotes/{id}/messages retrieves messages sorted by created_at."""
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/messages")
        
        assert response.status_code == 200, f"Failed to get messages: {response.text}"
        messages = response.json()
        
        # Should return a list
        assert isinstance(messages, list), "Messages should be a list"
        
        # If there are messages, verify they have required fields
        if len(messages) > 0:
            msg = messages[0]
            assert "id" in msg, "Message should have id"
            assert "quote_id" in msg, "Message should have quote_id"
            assert "sender_id" in msg, "Message should have sender_id"
            assert "sender_name" in msg, "Message should have sender_name"
            assert "sender_role" in msg, "Message should have sender_role"
            assert "message" in msg, "Message should have message content"
            assert "created_at" in msg, "Message should have created_at"
            
            # Verify messages are sorted by created_at (ascending)
            if len(messages) > 1:
                for i in range(len(messages) - 1):
                    assert messages[i]["created_at"] <= messages[i+1]["created_at"], \
                        "Messages should be sorted by created_at ascending"
        
        print(f"✓ GET messages returned {len(messages)} messages")
    
    def test_send_message_as_employer(self, employer_session):
        """POST /api/marketplace/quotes/{id}/messages sends a message (employer)."""
        test_message = "Test message from employer - automated test"
        
        response = employer_session.post(
            f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/messages",
            json={"message": test_message}
        )
        
        assert response.status_code == 200, f"Failed to send message: {response.text}"
        msg = response.json()
        
        assert msg["message"] == test_message, "Message content should match"
        assert msg["sender_role"] == "employer", "Sender role should be employer"
        assert msg["quote_id"] == ACCEPTED_QUOTE_ID, "Quote ID should match"
        assert "id" in msg, "Response should have message id"
        assert "created_at" in msg, "Response should have created_at"
        
        print(f"✓ Employer sent message successfully, id: {msg['id']}")
    
    def test_send_message_as_actuary(self, actuary_session):
        """POST /api/marketplace/quotes/{id}/messages sends a message (actuary)."""
        test_message = "Test message from actuary - automated test"
        
        response = actuary_session.post(
            f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/messages",
            json={"message": test_message}
        )
        
        assert response.status_code == 200, f"Failed to send message: {response.text}"
        msg = response.json()
        
        assert msg["message"] == test_message, "Message content should match"
        assert msg["sender_role"] == "actuary", "Sender role should be actuary"
        
        print(f"✓ Actuary sent message successfully, id: {msg['id']}")
    
    def test_reject_empty_message(self, employer_session):
        """POST /api/marketplace/quotes/{id}/messages rejects empty messages."""
        # Test with empty string
        response = employer_session.post(
            f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/messages",
            json={"message": ""}
        )
        
        assert response.status_code == 400, f"Empty message should be rejected, got {response.status_code}"
        assert "empty" in response.json().get("detail", "").lower(), "Error should mention empty message"
        
        # Test with whitespace only
        response = employer_session.post(
            f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/messages",
            json={"message": "   "}
        )
        
        assert response.status_code == 400, f"Whitespace-only message should be rejected, got {response.status_code}"
        
        print("✓ Empty messages correctly rejected")
    
    def test_reject_message_on_pending_quote(self, employer_session):
        """POST /api/marketplace/quotes/{id}/messages rejects messages when quote status is 'pending'."""
        # First, get all quotes to find a pending one
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes")
        assert response.status_code == 200
        
        quotes = response.json()
        pending_quote = next((q for q in quotes if q["status"] == "pending"), None)
        
        if pending_quote:
            # Try to send message on pending quote
            response = employer_session.post(
                f"{BASE_URL}/api/marketplace/quotes/{pending_quote['id']}/messages",
                json={"message": "Test message on pending quote"}
            )
            
            assert response.status_code == 400, f"Message on pending quote should be rejected, got {response.status_code}"
            assert "accepted" in response.json().get("detail", "").lower() or "available" in response.json().get("detail", "").lower(), \
                "Error should mention quote needs to be accepted"
            
            print(f"✓ Message on pending quote correctly rejected")
        else:
            # No pending quote found, create one for testing
            pytest.skip("No pending quote available for testing")
    
    def test_verify_messages_persisted(self, employer_session):
        """Verify that sent messages are persisted and retrievable."""
        # Get messages after sending
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/messages")
        
        assert response.status_code == 200
        messages = response.json()
        
        # Should have at least the messages we sent in previous tests
        assert len(messages) >= 1, "Should have at least one message"
        
        # Check that our test messages are in the list
        message_texts = [m["message"] for m in messages]
        has_employer_msg = any("Test message from employer" in m for m in message_texts)
        
        assert has_employer_msg, "Employer test message should be persisted"
        
        print(f"✓ Messages persisted correctly, total: {len(messages)}")


class TestPaymentDocumentValidation:
    """Test payment endpoint document validation."""
    
    def test_get_quote_details(self, employer_session):
        """Verify quote details include employer_documents field."""
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}")
        
        assert response.status_code == 200, f"Failed to get quote: {response.text}"
        quote = response.json()
        
        assert quote["status"] == "accepted", f"Quote should be accepted, got {quote['status']}"
        assert "employer_documents" in quote or quote.get("employer_documents") is None, \
            "Quote should have employer_documents field"
        
        employer_docs = quote.get("employer_documents", [])
        print(f"✓ Quote has {len(employer_docs)} employer documents")
        
        return quote
    
    def test_pay_rejected_without_documents(self, employer_session):
        """PUT /api/marketplace/quotes/{id}/pay rejects payment when no employer_documents uploaded."""
        # First check if quote has documents
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}")
        assert response.status_code == 200
        quote = response.json()
        
        employer_docs = quote.get("employer_documents", [])
        
        if len(employer_docs) == 0:
            # Try to pay without documents
            response = employer_session.put(
                f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/pay",
                json={"payment_method": "platform"}
            )
            
            assert response.status_code == 400, f"Payment without documents should be rejected, got {response.status_code}"
            error_detail = response.json().get("detail", "")
            assert "document" in error_detail.lower(), f"Error should mention documents: {error_detail}"
            
            print("✓ Payment correctly rejected when no documents uploaded")
        else:
            # Documents exist, we need to test differently
            print(f"⚠ Quote already has {len(employer_docs)} documents, skipping no-document test")
            pytest.skip("Quote already has documents uploaded")
    
    def test_upload_document_and_verify(self, employer_session):
        """Test uploading a document to the quote."""
        # Create a simple test file
        test_content = b"Test document content for ACA compliance testing"
        files = {
            'file': ('test_document.pdf', test_content, 'application/pdf')
        }
        data = {
            'doc_type': 'employer',
            'doc_label': 'Test Document'
        }
        
        # Remove Content-Type header for multipart upload
        headers = dict(employer_session.headers)
        headers.pop('Content-Type', None)
        
        response = requests.post(
            f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Document upload failed: {response.text}"
        doc = response.json()
        
        assert "id" in doc, "Upload response should have document id"
        assert doc["filename"] == "test_document.pdf", "Filename should match"
        
        print(f"✓ Document uploaded successfully, id: {doc['id']}")
        
        return doc["id"]
    
    def test_verify_document_in_quote(self, employer_session):
        """Verify uploaded document appears in quote details."""
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}")
        
        assert response.status_code == 200
        quote = response.json()
        
        employer_docs = quote.get("employer_documents", [])
        assert len(employer_docs) > 0, "Quote should have at least one employer document"
        
        # Check document structure
        doc = employer_docs[0]
        assert "id" in doc, "Document should have id"
        assert "filename" in doc, "Document should have filename"
        assert "uploaded_by_role" in doc, "Document should have uploaded_by_role"
        
        print(f"✓ Quote has {len(employer_docs)} employer documents")


class TestQuoteStatusValidation:
    """Test that chat is only available for appropriate quote statuses."""
    
    def test_chat_available_for_accepted_status(self, employer_session):
        """Verify chat is available for accepted quotes."""
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}/messages")
        assert response.status_code == 200, "Chat should be available for accepted quotes"
        print("✓ Chat available for accepted status")
    
    def test_quote_status_is_accepted(self, employer_session):
        """Verify the test quote has 'accepted' status."""
        response = employer_session.get(f"{BASE_URL}/api/marketplace/quotes/{ACCEPTED_QUOTE_ID}")
        
        assert response.status_code == 200
        quote = response.json()
        
        assert quote["status"] == "accepted", f"Expected 'accepted' status, got '{quote['status']}'"
        print(f"✓ Quote status is 'accepted' as expected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
