"""
Test content relationships and data integrity
"""
import pytest
from fastapi import status


class TestContentRelationships:
    """Test content entry relationships and data consistency"""
    
    def test_content_entry_belongs_to_content_type(self, authenticated_client):
        """Test that content entries are properly linked to content types"""
        # Create content type
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Article",
                "api_id": "article",
                "description": "Article content",
                "fields": [
                    {"name": "title", "type": "text", "required": True},
                    {"name": "content", "type": "textarea", "required": True}
                ]
            }
        )
        assert ct_response.status_code == status.HTTP_201_CREATED
        content_type_id = ct_response.json()["id"]
        
        # Create content entry
        entry_response = authenticated_client.post(
            "/api/v1/content/entries",
            json={
                "content_type_id": content_type_id,
                "slug": "test-article",
                "status": "draft",
                "data": {
                    "title": "Test Article",
                    "content": "Article content here"
                }
            }
        )
        assert entry_response.status_code == status.HTTP_201_CREATED
        entry_data = entry_response.json()
        
        # Verify relationship
        assert entry_data["content_type_id"] == content_type_id
        assert entry_data["slug"] == "test-article"
        assert entry_data["status"] == "draft"
    
    def test_content_entry_requires_valid_content_type(self, authenticated_client):
        """Test that content entry creation fails with invalid content type"""
        response = authenticated_client.post(
            "/api/v1/content/entries",
            json={
                "content_type_id": 99999,  # Non-existent ID
                "slug": "invalid-entry",
                "status": "draft",
                "data": {"title": "Test"}
            }
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_content_type_deletion_cascade(self, authenticated_client):
        """Test that deleting a content type handles entries properly"""
        # Create content type
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Temporary Type",
                "api_id": "temp_type",
                "description": "Will be deleted",
                "fields": [{"name": "title", "type": "text", "required": True}]
            }
        )
        assert ct_response.status_code == status.HTTP_201_CREATED
        content_type_id = ct_response.json()["id"]
        
        # Create an entry
        entry_response = authenticated_client.post(
            "/api/v1/content/entries",
            json={
                "content_type_id": content_type_id,
                "slug": "temp-entry",
                "status": "draft",
                "data": {"title": "Temporary Entry"}
            }
        )
        assert entry_response.status_code == status.HTTP_201_CREATED
        entry_id = entry_response.json()["id"]
        
        # Delete the content type
        delete_response = authenticated_client.delete(
            f"/api/v1/content/types/{content_type_id}"
        )
        
        if delete_response.status_code == status.HTTP_204_NO_CONTENT:
            # Try to get the entry - should fail or be gone
            get_entry_response = authenticated_client.get(
                f"/api/v1/content/entries/{entry_id}"
            )
            assert get_entry_response.status_code in [
                status.HTTP_404_NOT_FOUND,
                status.HTTP_400_BAD_REQUEST
            ]
    
    def test_slug_uniqueness_per_organization(self, authenticated_client):
        """Test that slugs are unique within an organization"""
        # Create content type
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Page",
                "api_id": "page",
                "description": "Web pages",
                "fields": [{"name": "title", "type": "text", "required": True}]
            }
        )
        content_type_id = ct_response.json()["id"]
        
        # Create first entry with slug
        first_response = authenticated_client.post(
            "/api/v1/content/entries",
            json={
                "content_type_id": content_type_id,
                "slug": "unique-slug",
                "status": "draft",
                "data": {"title": "First Page"}
            }
        )
        assert first_response.status_code == status.HTTP_201_CREATED
        
        # Try to create another entry with same slug
        second_response = authenticated_client.post(
            "/api/v1/content/entries",
            json={
                "content_type_id": content_type_id,
                "slug": "unique-slug",
                "status": "draft",
                "data": {"title": "Second Page"}
            }
        )
        
        # Should fail due to slug conflict
        assert second_response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
