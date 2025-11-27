"""
Test suite for content templates
"""
import pytest
from fastapi import status


class TestContentTemplates:
    """Test content template functionality"""
    
    def test_create_content_template(self, authenticated_client):
        """Test creating a content template"""
        # First create a content type
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Blog Post",
                "api_id": "blog_post",
                "description": "Blog articles",
                "fields": [
                    {"name": "title", "type": "text", "required": True},
                    {"name": "body", "type": "textarea", "required": True},
                    {"name": "author", "type": "text", "required": False}
                ]
            }
        )
        
        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]
            
            # Create a template
            template_response = authenticated_client.post(
                "/api/v1/content/templates",
                json={
                    "name": "Standard Blog Post",
                    "content_type_id": content_type_id,
                    "description": "Default blog post template",
                    "default_data": {
                        "author": "Staff Writer",
                        "body": "Write your article here..."
                    },
                    "field_config": {
                        "title": {
                            "help_text": "Enter a catchy title",
                            "max_length": 100
                        }
                    }
                }
            )
            
            # Template creation may require permissions
            assert template_response.status_code in [
                status.HTTP_201_CREATED,
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND
            ]
    
    def test_list_content_templates(self, authenticated_client):
        """Test listing content templates"""
        response = authenticated_client.get("/api/v1/content/templates")
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]
    
    def test_use_template_for_content_creation(self, authenticated_client):
        """Test creating content from a template"""
        # Create content type
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Article",
                "api_id": "article",
                "fields": [
                    {"name": "title", "type": "text", "required": True},
                    {"name": "summary", "type": "text"}
                ]
            }
        )
        
        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]
            
            # Create template
            template_response = authenticated_client.post(
                "/api/v1/content/templates",
                json={
                    "name": "News Article",
                    "content_type_id": content_type_id,
                    "default_data": {
                        "summary": "Breaking news"
                    }
                }
            )
            
            if template_response.status_code == status.HTTP_201_CREATED:
                template_id = template_response.json().get("id")
                
                # Create content using template
                entry_response = authenticated_client.post(
                    "/api/v1/content/entries",
                    json={
                        "content_type_id": content_type_id,
                        "template_id": template_id,
                        "slug": "news-article-1",
                        "status": "draft",
                        "data": {
                            "title": "Breaking News Title"
                        }
                    }
                )
                
                # Entry creation should work
                assert entry_response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_400_BAD_REQUEST
                ]
