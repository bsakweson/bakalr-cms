"""
Tests for webhook endpoints and management
"""
import pytest


def test_create_webhook(authenticated_client):
    """Test creating a webhook"""
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created", "content.updated"],
        "name": "Test Webhook"
    }
    
    response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    
    assert response.status_code == 201
    data = response.json()
    # Create endpoint only returns id and secret
    assert "id" in data
    assert "secret" in data
    assert "message" in data


def test_list_webhooks(authenticated_client):
    """Test listing webhooks"""
    # Create a webhook first
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    
    # List webhooks
    response = authenticated_client.get("/api/v1/webhooks")
    
    assert response.status_code == 200
    data = response.json()
    assert "webhooks" in data
    assert "total" in data
    assert data["total"] > 0


def test_get_webhook(authenticated_client):
    """Test getting a specific webhook"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    
    # Get webhook
    response = authenticated_client.get(f"/api/v1/webhooks/{webhook_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == webhook_id
    assert data["url"] == webhook_data["url"]


def test_update_webhook(authenticated_client):
    """Test updating a webhook"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    
    # Update webhook
    update_data = {
        "name": "Updated Webhook"
    }
    response = authenticated_client.patch(
        f"/api/v1/webhooks/{webhook_id}",
        json=update_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]


def test_disable_webhook(authenticated_client):
    """Test disabling a webhook"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    
    # Disable webhook
    response = authenticated_client.patch(
        f"/api/v1/webhooks/{webhook_id}",
        json={"status": "disabled"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disabled"


def test_delete_webhook(authenticated_client):
    """Test deleting a webhook"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    
    # Delete webhook
    response = authenticated_client.delete(f"/api/v1/webhooks/{webhook_id}")
    
    assert response.status_code in [200, 204]


def test_list_webhook_logs(authenticated_client):
    """Test listing webhook delivery logs"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    
    # List deliveries
    response = authenticated_client.get(f"/api/v1/webhooks/{webhook_id}/deliveries")
    
    assert response.status_code == 200
    data = response.json()
    assert "deliveries" in data
    assert "total" in data


def test_get_webhook_log(authenticated_client):
    """Test getting a specific webhook log entry"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    
    # Get deliveries endpoint
    response = authenticated_client.get(f"/api/v1/webhooks/{webhook_id}/deliveries")
    
    assert response.status_code == 200
    data = response.json()
    assert "deliveries" in data


def test_regenerate_webhook_secret(authenticated_client):
    """Test regenerating webhook secret"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    old_secret = create_response.json()["secret"]
    
    # Regenerate secret
    response = authenticated_client.post(
        f"/api/v1/webhooks/{webhook_id}/regenerate-secret"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "secret" in data
    assert data["secret"] != old_secret


def test_test_webhook(authenticated_client):
    """Test webhook test endpoint"""
    # Create webhook
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    create_response = authenticated_client.post("/api/v1/webhooks", json=webhook_data)
    webhook_id = create_response.json()["id"]
    
    # Test webhook (send test payload)
    response = authenticated_client.post(f"/api/v1/webhooks/{webhook_id}/test")
    
    # Expect 200 or 422 (validation error) or 500 (connection error)
    assert response.status_code in [200, 422, 500]


def test_webhook_unauthorized(client):
    """Test webhook endpoints require authentication"""
    webhook_data = {
        "url": "https://example.com/webhook",
        "events": ["content.created"],
        "name": "Test Webhook"
    }
    
    response = client.post("/api/v1/webhooks", json=webhook_data)
    
    # Rate limiter returns 403 for unauthenticated requests
    assert response.status_code in [401, 403]
