"""
Tests for content type and content entry endpoints
"""
import pytest


def test_create_content_type(authenticated_client, test_content_type_data):
    """Test creating a content type"""
    response = authenticated_client.post(
        "/api/v1/content-types",
        json=test_content_type_data
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_content_type_data["name"]
    assert data["slug"] == test_content_type_data["slug"]
    assert "id" in data
    assert "schema" in data


def test_list_content_types(authenticated_client, test_content_type_data):
    """Test listing content types"""
    # Create a content type
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    
    # List content types
    response = authenticated_client.get("/api/v1/content-types")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0


def test_get_content_type(authenticated_client, test_content_type_data):
    """Test getting a specific content type"""
    # Create content type
    create_response = authenticated_client.post(
        "/api/v1/content-types",
        json=test_content_type_data
    )
    content_type_id = create_response.json()["id"]
    
    # Get content type
    response = authenticated_client.get(f"/api/v1/content-types/{content_type_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == content_type_id
    assert data["name"] == test_content_type_data["name"]


def test_update_content_type(authenticated_client, test_content_type_data):
    """Test updating a content type"""
    # Create content type
    create_response = authenticated_client.post(
        "/api/v1/content-types",
        json=test_content_type_data
    )
    content_type_id = create_response.json()["id"]
    
    # Update content type
    updated_data = {
        **test_content_type_data,
        "description": "Updated description"
    }
    response = authenticated_client.put(
        f"/api/v1/content-types/{content_type_id}",
        json=updated_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"


def test_delete_content_type(authenticated_client, test_content_type_data):
    """Test deleting a content type"""
    # Create content type
    create_response = authenticated_client.post(
        "/api/v1/content-types",
        json=test_content_type_data
    )
    content_type_id = create_response.json()["id"]
    
    # Delete content type
    response = authenticated_client.delete(
        f"/api/v1/content-types/{content_type_id}"
    )
    
    assert response.status_code == 204


def test_create_content_entry(authenticated_client, test_content_type_data, test_content_data):
    """Test creating a content entry"""
    # Create content type first
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    
    # Create content entry
    response = authenticated_client.post("/api/v1/content", json=test_content_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["content_type"] == test_content_data["content_type"]
    assert data["slug"] == test_content_data["slug"]
    assert data["status"] == test_content_data["status"]
    assert "id" in data


def test_list_content_entries(authenticated_client, test_content_type_data, test_content_data):
    """Test listing content entries"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # List content entries
    response = authenticated_client.get("/api/v1/content")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0


def test_filter_content_by_type(authenticated_client, test_content_type_data, test_content_data):
    """Test filtering content by content type"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # Filter by content type
    response = authenticated_client.get(
        f"/api/v1/content?content_type={test_content_data['content_type']}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert all(
        item["content_type"] == test_content_data["content_type"]
        for item in data["items"]
    )


def test_get_content_by_slug(authenticated_client, test_content_type_data, test_content_data):
    """Test getting content by slug"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    authenticated_client.post("/api/v1/content", json=test_content_data)
    
    # Get by slug
    response = authenticated_client.get(
        f"/api/v1/content/{test_content_data['content_type']}/slug/{test_content_data['slug']}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == test_content_data["slug"]


def test_update_content_entry(authenticated_client, test_content_type_data, test_content_data):
    """Test updating a content entry"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    create_response = authenticated_client.post("/api/v1/content", json=test_content_data)
    content_id = create_response.json()["id"]
    
    # Update content
    updated_data = {
        **test_content_data,
        "fields": {
            **test_content_data["fields"],
            "title": "Updated Title"
        }
    }
    response = authenticated_client.put(f"/api/v1/content/{content_id}", json=updated_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["fields"]["title"] == "Updated Title"


def test_delete_content_entry(authenticated_client, test_content_type_data, test_content_data):
    """Test deleting a content entry"""
    # Create content type and entry
    authenticated_client.post("/api/v1/content-types", json=test_content_type_data)
    create_response = authenticated_client.post("/api/v1/content", json=test_content_data)
    content_id = create_response.json()["id"]
    
    # Delete content
    response = authenticated_client.delete(f"/api/v1/content/{content_id}")
    
    assert response.status_code == 204
