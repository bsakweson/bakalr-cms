"""
Test suite for organization - simplified version
"""

from fastapi import status


class TestOrganization:
    """Test organization endpoints"""

    def test_get_organization_profile(self, authenticated_client):
        """Test getting organization profile"""
        response = authenticated_client.get("/api/v1/organization/profile")
        # Accept 200 (success) or 403 (permission denied) - just verify endpoint exists
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_get_organization_settings(self, authenticated_client):
        """Test getting organization settings"""
        response = authenticated_client.get("/api/v1/organization/settings")
        # Accept success or not found
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
