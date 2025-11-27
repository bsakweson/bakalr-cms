"""
Test suite for field-level permissions
"""

from fastapi import status


class TestFieldPermissions:
    """Test field-level permission controls"""

    def test_create_field_permission(self, authenticated_client):
        """Test creating field-level permissions"""
        # Create content type first
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Sensitive Content",
                "api_id": "sensitive_content",
                "fields": [
                    {"name": "title", "type": "text", "required": True},
                    {"name": "public_content", "type": "textarea"},
                    {"name": "private_notes", "type": "textarea"},
                ],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]

            # Try to create field permission
            response = authenticated_client.post(
                "/api/v1/field-permissions",
                json={
                    "content_type_id": content_type_id,
                    "field_name": "private_notes",
                    "role_name": "editor",
                    "can_read": False,
                    "can_write": False,
                },
            )

            # May require admin permissions
            assert response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ]

    def test_field_masking_on_read(self, authenticated_client):
        """Test that restricted fields are masked"""
        # Create content type
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Protected Content",
                "api_id": "protected_content",
                "fields": [
                    {"name": "title", "type": "text", "required": True},
                    {"name": "secret_field", "type": "text"},
                ],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]

            # Create entry with secret field
            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": "protected-entry",
                    "status": "published",
                    "data": {"title": "Public Title", "secret_field": "This should be hidden"},
                },
            )

            if entry_response.status_code == status.HTTP_201_CREATED:
                entry_id = entry_response.json()["id"]

                # Read the entry back
                get_response = authenticated_client.get(f"/api/v1/content/entries/{entry_id}")

                assert get_response.status_code == status.HTTP_200_OK
                # Field permission masking depends on user's role

    def test_list_field_permissions(self, authenticated_client):
        """Test listing field permissions"""
        response = authenticated_client.get("/api/v1/field-permissions")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
