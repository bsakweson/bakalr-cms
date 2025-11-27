"""
Tests for search endpoints and functionality
"""
import pytest


def test_search_content(authenticated_client, test_content_type_data, test_content_data):
    """Test searching content entries"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content/entries", json=test_content_data)
    
    # Search for content
    response = authenticated_client.get(
        "/api/v1/search",
        params={"query": "test post"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert "total_hits" in data


def test_search_with_content_type_filter(authenticated_client, test_content_type_data, test_content_data):
    """Test searching with content type filter"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content/entries", json=test_content_data)
    
    # Search with filter
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "query": "post",
            "content_type_slug": "blog_post"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data


def test_search_with_status_filter(authenticated_client, test_content_type_data, test_content_data):
    """Test searching with status filter"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content/entries", json=test_content_data)
    
    # Search with status filter
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "query": "post",
            "status": "published"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data


def test_search_with_pagination(authenticated_client, test_content_type_data, test_content_data):
    """Test search with pagination"""
    # Create content type and multiple entries
    authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    
    for i in range(5):
        entry_data = {
            **test_content_data,
            "slug": f"test-post-{i}",
            "data": {
                **test_content_data["data"],
                "title": f"Test Post {i}"
            }
        }
        authenticated_client.post("/api/v1/content/entries", json=entry_data)
    
    # Search with pagination
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "query": "test",
            "limit": 2,
            "offset": 0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["hits"]) <= 2
    assert "total_hits" in data


def test_search_empty_query(authenticated_client):
    """Test search with minimal query"""
    response = authenticated_client.get("/api/v1/search", params={"query": "a"})
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert "total_hits" in data


def test_search_no_results(authenticated_client):
    """Test search with query that returns no results"""
    response = authenticated_client.get(
        "/api/v1/search",
        params={"query": "nonexistent-content-xyz-123456"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_hits"] == 0
    assert len(data["hits"]) == 0


def test_search_by_locale(authenticated_client, test_content_type_data, test_content_data):
    """Test searching content by locale"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content/entries", json=test_content_data)
    
    # Search by locale
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "query": "post",
            "locale": "en"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data


def test_search_sorting(authenticated_client, test_content_type_data, test_content_data):
    """Test search results sorting"""
    # Create content type and entries
    authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    
    for i in range(3):
        entry_data = {
            **test_content_data,
            "slug": f"post-{i}",
            "data": {
                **test_content_data["data"],
                "title": f"Post {i}"
            }
        }
        authenticated_client.post("/api/v1/content/entries", json=entry_data)
    
    # Search with sort
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "query": "post",
            "sort_by": "created_at",
            "sort_order": "desc"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data


def test_search_unauthorized(client):
    """Test search without authentication"""
    # Search requires authentication, rate limiter returns 403
    response = client.get("/api/v1/search", params={"query": "test"})
    
    assert response.status_code in [401, 403]


def test_advanced_search(authenticated_client, test_content_type_data, test_content_data):
    """Test advanced search with multiple filters"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content/types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content/entries", json=test_content_data)
    
    # Advanced search
    response = authenticated_client.get(
        "/api/v1/search",
        params={
            "query": "post",
            "content_type_slug": "blog_post",
            "status": "published",
            "limit": 10,
            "offset": 0,
            "sort_by": "created_at",
            "sort_order": "desc"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "hits" in data
    assert "total_hits" in data
