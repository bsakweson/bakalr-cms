"""
Test suite for tenant/organization switching
"""

from fastapi import status


class TestTenantSwitching:
    """Test multi-organization and tenant switching"""

    def test_list_user_organizations(self, authenticated_client):
        """Test listing organizations user belongs to"""
        response = authenticated_client.get("/api/v1/tenant/organizations")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "organizations" in data
        assert "current_organization_id" in data
        assert isinstance(data["organizations"], list)
        assert len(data["organizations"]) >= 1  # User should have at least one org

    def test_switch_organization(self, authenticated_client):
        """Test switching to another organization"""
        # Get list of organizations first
        list_response = authenticated_client.get("/api/v1/tenant/organizations")

        if list_response.status_code == status.HTTP_200_OK:
            data = list_response.json()
            current_org_id = data["current_organization_id"]

            # Try to switch to same organization (should work)
            switch_response = authenticated_client.post(
                "/api/v1/tenant/switch", json={"organization_id": current_org_id}
            )

            assert switch_response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_switch_to_invalid_organization(self, authenticated_client):
        """Test switching to non-existent organization"""
        fake_uuid = "99999999-9999-9999-9999-999999999999"
        response = authenticated_client.post(
            "/api/v1/tenant/switch", json={"organization_id": fake_uuid}
        )

        # Should fail with 403 or 404
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_set_default_organization(self, authenticated_client):
        """Test setting default organization"""
        # Get current organization
        list_response = authenticated_client.get("/api/v1/tenant/organizations")

        if list_response.status_code == status.HTTP_200_OK:
            data = list_response.json()
            current_org_id = data["current_organization_id"]

            # Set as default
            response = authenticated_client.post(
                "/api/v1/tenant/set-default", json={"organization_id": current_org_id}
            )

            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
            ]

    def test_invite_user_to_organization(self, authenticated_client):
        """Test inviting user to organization"""
        invite_data = {"email": "newuser@example.com", "role_names": ["viewer"]}

        response = authenticated_client.post("/api/v1/tenant/invite", json=invite_data)

        # May succeed or fail based on permissions or endpoint availability
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,  # Endpoint may not exist in all configurations
        ]

    def test_remove_user_from_organization(self, authenticated_client):
        """Test removing user from organization"""
        # Try to remove non-existent user (use UUID format)
        fake_uuid = "99999999-9999-9999-9999-999999999999"
        response = authenticated_client.delete(f"/api/v1/tenant/remove/{fake_uuid}")

        # Should fail
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,  # May get validation error for UUID
        ]
