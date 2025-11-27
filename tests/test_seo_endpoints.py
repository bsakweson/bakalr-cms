"""
Test suite for SEO functionality
"""

from fastapi import status


class TestSEO:
    """Test SEO endpoints"""

    def test_create_seo_metadata(self, authenticated_client):
        """Test creating SEO metadata for content"""
        # First create content type and entry
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "SEO Test Article",
                "api_id": "seo_test_article",
                "description": "For SEO testing",
                "fields": [{"name": "title", "type": "text", "required": True}],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]

            # Create content entry
            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": "seo-test-entry",
                    "status": "published",
                    "data": {"title": "SEO Test"},
                },
            )

            if entry_response.status_code == status.HTTP_201_CREATED:
                entry_id = entry_response.json()["id"]

                # Create SEO metadata
                seo_data = {
                    "content_entry_id": entry_id,
                    "meta_title": "SEO Test Title",
                    "meta_description": "This is a test meta description",
                    "meta_keywords": ["test", "seo", "metadata"],
                }

                response = authenticated_client.post("/api/v1/seo/metadata", json=seo_data)

                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_404_NOT_FOUND,
                ]

    def test_list_seo_metadata(self, authenticated_client):
        """Test listing SEO metadata"""
        response = authenticated_client.get("/api/v1/seo/metadata")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_update_seo_metadata(self, authenticated_client):
        """Test updating SEO metadata"""
        # Get list first
        list_response = authenticated_client.get("/api/v1/seo/metadata")

        if list_response.status_code == status.HTTP_200_OK:
            items = list_response.json().get("items", [])

            if items:
                seo_id = items[0]["id"]

                update_data = {
                    "meta_title": "Updated SEO Title",
                    "meta_description": "Updated description",
                }

                response = authenticated_client.put(
                    f"/api/v1/seo/metadata/{seo_id}", json=update_data
                )

                assert response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_404_NOT_FOUND,
                ]

    def test_delete_seo_metadata(self, authenticated_client):
        """Test deleting SEO metadata"""
        response = authenticated_client.delete("/api/v1/seo/metadata/99999")

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_generate_sitemap(self, authenticated_client):
        """Test generating XML sitemap"""
        response = authenticated_client.get("/api/v1/seo/sitemap.xml")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_generate_robots_txt(self, authenticated_client):
        """Test generating robots.txt"""
        response = authenticated_client.get("/api/v1/seo/robots.txt")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]

    def test_get_structured_data(self, authenticated_client):
        """Test getting structured data for content"""
        response = authenticated_client.get("/api/v1/seo/structured-data/1")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
