"""
Tests for search endpoints and functionality
"""
import pytest


def test_search_content(authenticated_client, test_content_type_data, test_content_data):
    """Test searching content entries"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # Search for content
    response = authenticated_client.get(
        "/api/v1/search",
        params={"q": "first post"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_search_with_content_type_filter(authenticated_client, test_content_type_data, test_content_data):
    """Test searching with content type filter"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # Search with filter
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "q": "post",
            "content_type": "blog-post"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    if data["items"]:
        assert all(
            item["content_type"] == "blog-post"
            for item in data["items"]
        )


def test_search_with_status_filter(authenticated_client, test_content_type_data, test_content_data):
    """Test searching with status filter"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # Search with status filter
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "q": "post",
            "status": "published"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    if data["items"]:
        assert all(
            item["status"] == "published"
            for item in data["items"]
        )


def test_search_with_pagination(authenticated_client, test_content_type_data, test_content_data):
    """Test search with pagination"""
    # Create content type and multiple entries
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    
    for i in range(5):
        entry_data = {
            **test_content_data,
            "slug": f"test-post-{i}",
            "fields": {
                **test_content_data["fields"],
                "title": f"Test Post {i}"
            }
        }
        authenticated_client.post("/api/v1/content", json=entry_data)
    
    # Search with pagination
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "q": "test",
            "limit": 2,
            "offset": 0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 2
    assert "total" in data


def test_search_empty_query(authenticated_client):
    """Test search with empty query returns all content"""
    response = authenticated_client.get("/api/v1/search")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


def test_search_no_results(authenticated_client):
    """Test search with query that returns no results"""
    response = authenticated_client.get(
        "/api/v1/search",
        params={"q": "nonexistent-content-xyz"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_search_by_locale(authenticated_client, test_content_type_data, test_content_data):
    """Test searching content by locale"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # Search by locale
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "q": "post",
            "locale": "en"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_search_sorting(authenticated_client, test_content_type_data, test_content_data):
    """Test search results sorting"""
    # Create content type and entries
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    
    for i in range(3):
        entry_data = {
            **test_content_data,
            "slug": f"post-{i}",
            "fields": {
                **test_content_data["fields"],
                "title": f"Post {i}"
            }
        }
        authenticated_client.post("/api/v1/content", json=entry_data)
    
    # Search with sort
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "q": "post",
            "sort": "created_at:desc"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_search_unauthorized(client):
    """Test search without authentication"""
    # Depending on your implementation, search might be public or require auth
    response = client.get("/api/v1/search", params={"q": "test"})
    
    # Adjust this based on your security requirements
    # If search is public:
    # assert response.status_code == 200
    # If search requires auth:
    # assert response.status_code == 401
    assert response.status_code in [200, 401]


def test_advanced_search(authenticated_client, test_content_type_data, test_content_data):
    """Test advanced search with multiple filters"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # Advanced search
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "q": "post",
            "content_type": "blog-post",
            "status": "published",
            "locale": "en",
            "limit": 10,
            "offset": 0,
            "sort": "created_at:desc"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
