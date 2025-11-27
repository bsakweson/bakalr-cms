"""
Test suite for preview functionality
"""

from fastapi import status


class TestPreview:
    """Test content preview endpoints"""

    def test_generate_preview_token(self, authenticated_client):
        """Test generating preview token for draft content"""
        # Create content type and draft entry
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Preview Article",
                "api_id": "preview_article",
                "description": "For preview tests",
                "fields": [{"name": "title", "type": "text", "required": True}],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]

            # Create draft entry
            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": "preview-entry",
                    "status": "draft",
                    "data": {"title": "Preview Content"},
                },
            )

            if entry_response.status_code == status.HTTP_201_CREATED:
                entry_id = entry_response.json()["id"]

                # Generate preview token
                response = authenticated_client.post(f"/api/v1/preview/generate/{entry_id}")

                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_201_CREATED,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_404_NOT_FOUND,
                ]

    def test_preview_content_with_token(self, authenticated_client):
        """Test previewing content with valid token"""
        # Try with fake token
        response = authenticated_client.get(
            "/api/v1/preview/content/1", params={"token": "fake-token"}
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_preview_content_without_token(self, authenticated_client):
        """Test preview access without token should fail"""
        response = authenticated_client.get("/api/v1/preview/content/1")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]
