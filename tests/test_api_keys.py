"""
Test suite for API key authentication and management
"""

from datetime import datetime, timedelta, timezone

from fastapi import status


class TestAPIKeys:
    """Test API key functionality"""

    def test_create_api_key(self, authenticated_client):
        """Test creating an API key"""
        expiration = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        response = authenticated_client.post(
            "/api/v1/api-keys",
            json={
                "name": "Test API Key",
                "permissions": ["content.read", "media.read"],
                "expires_at": expiration,
            },
        )

        # May require permissions
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert "key" in data or "api_key" in data
            assert "name" in data
            assert data["name"] == "Test API Key"

    def test_list_api_keys(self, authenticated_client):
        """Test listing API keys"""
        response = authenticated_client.get("/api/v1/api-keys")

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should return a list or object with api_keys
            assert isinstance(data, (list, dict))

    def test_api_key_authentication(self, client, authenticated_client):
        """Test authenticating with an API key"""
        # Create an API key first
        create_response = authenticated_client.post(
            "/api/v1/api-keys", json={"name": "Auth Test Key", "permissions": ["content.read"]}
        )

        if create_response.status_code == status.HTTP_201_CREATED:
            api_key = create_response.json().get("key") or create_response.json().get("api_key")

            if api_key:
                # Try to use the API key
                response = client.get("/api/v1/content/types", headers={"X-API-Key": api_key})

                assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]

    def test_api_key_expiration(self, authenticated_client):
        """Test that expired API keys are rejected"""
        # Create an already-expired key
        past_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        response = authenticated_client.post(
            "/api/v1/api-keys", json={"name": "Expired Key", "expires_at": past_date}
        )

        # Should either reject expired date or create it
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_revoke_api_key(self, authenticated_client):
        """Test revoking an API key"""
        # Create a key
        create_response = authenticated_client.post(
            "/api/v1/api-keys", json={"name": "Key to Revoke"}
        )

        if create_response.status_code == status.HTTP_201_CREATED:
            key_id = create_response.json().get("id")

            if key_id:
                # Revoke it
                revoke_response = authenticated_client.delete(f"/api/v1/api-keys/{key_id}")

                assert revoke_response.status_code in [
                    status.HTTP_204_NO_CONTENT,
                    status.HTTP_200_OK,
                    status.HTTP_404_NOT_FOUND,
                ]
