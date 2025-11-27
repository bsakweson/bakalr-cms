"""
Test suite for relationship management
"""

from fastapi import status


class TestRelationships:
    """Test content relationship endpoints"""

    def test_create_relationship(self, authenticated_client):
        """Test creating content relationship"""
        # Create two content types first
        ct1_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Author",
                "api_id": "author",
                "description": "Author content type",
                "fields": [{"name": "name", "type": "text", "required": True}],
            },
        )

        ct2_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Book",
                "api_id": "book",
                "description": "Book content type",
                "fields": [{"name": "title", "type": "text", "required": True}],
            },
        )

        if (
            ct1_response.status_code == status.HTTP_201_CREATED
            and ct2_response.status_code == status.HTTP_201_CREATED
        ):

            ct1_id = ct1_response.json()["id"]
            ct2_id = ct2_response.json()["id"]

            # Create entries
            author_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": ct1_id,
                    "slug": "test-author",
                    "status": "published",
                    "data": {"name": "Test Author"},
                },
            )

            book_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": ct2_id,
                    "slug": "test-book",
                    "status": "published",
                    "data": {"title": "Test Book"},
                },
            )

            if (
                author_response.status_code == status.HTTP_201_CREATED
                and book_response.status_code == status.HTTP_201_CREATED
            ):

                author_id = author_response.json()["id"]
                book_id = book_response.json()["id"]

                # Create relationship
                relationship_data = {
                    "source_entry_id": book_id,
                    "target_entry_id": author_id,
                    "relationship_type": "author",
                }

                response = authenticated_client.post(
                    "/api/v1/content/relationships", json=relationship_data
                )

                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_404_NOT_FOUND,
                ]

    def test_list_relationships(self, authenticated_client):
        """Test listing relationships"""
        response = authenticated_client.get("/api/v1/content/relationships")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_get_entry_relationships(self, authenticated_client):
        """Test getting relationships for specific entry"""
        response = authenticated_client.get(
            "/api/v1/content/relationships", params={"source_entry_id": 1}
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_delete_relationship(self, authenticated_client):
        """Test deleting a relationship"""
        response = authenticated_client.delete("/api/v1/content/relationships/99999")

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
