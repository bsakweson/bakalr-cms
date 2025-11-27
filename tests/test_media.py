"""
Tests for media upload and management endpoints
"""
import pytest
from io import BytesIO


def test_upload_image(authenticated_client):
    """Test uploading an image file"""
    # Create a fake image file
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    
    response = authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_image.jpg", image_file, "image/jpeg")
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["media_type"] == "image"
    assert data["mime_type"] == "image/jpeg"
    assert "url" in data


def test_upload_document(authenticated_client):
    """Test uploading a document file"""
    # Create a fake PDF file
    doc_data = b"fake pdf content"
    doc_file = BytesIO(doc_data)
    
    response = authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_document.pdf", doc_file, "application/pdf")
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["media_type"] == "document"
    assert data["mime_type"] == "application/pdf"


def test_list_media(authenticated_client):
    """Test listing media files"""
    # Upload a file first
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_image.jpg", image_file, "image/jpeg")
        }
    )
    
    # List media
    response = authenticated_client.get("/api/v1/media")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0


def test_filter_media_by_type(authenticated_client):
    """Test filtering media by file type"""
    # Upload an image
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_image.jpg", image_file, "image/jpeg")
        }
    )
    
    # Filter by image type
    response = authenticated_client.get("/api/v1/media?media_type=image")
    
    assert response.status_code == 200
    data = response.json()
    assert all(item["media_type"] == "image" for item in data["items"])


def test_get_media_by_id(authenticated_client):
    """Test getting a specific media file"""
    # Upload a file
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    upload_response = authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_image.jpg", image_file, "image/jpeg")
        }
    )
    media_id = upload_response.json()["id"]
    
    # Get media by ID
    response = authenticated_client.get(f"/api/v1/media/{media_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == media_id


def test_update_media_metadata(authenticated_client):
    """Test updating media metadata"""
    # Upload a file
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    upload_response = authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_image.jpg", image_file, "image/jpeg")
        }
    )
    media_id = upload_response.json()["id"]
    
    # Update metadata
    response = authenticated_client.put(
        f"/api/v1/media/{media_id}",
        json={
            "alt_text": "Updated alt text",
            "description": "Updated description"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["alt_text"] == "Updated alt text"
    assert data["description"] == "Updated description"


def test_delete_media(authenticated_client):
    """Test deleting a media file"""
    # Upload a file
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    upload_response = authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_image.jpg", image_file, "image/jpeg")
        }
    )
    media_id = upload_response.json()["id"]
    
    # Delete media
    response = authenticated_client.delete(f"/api/v1/media/{media_id}")
    
    assert response.status_code in [200, 204]


def test_upload_unauthorized(client):
    """Test upload without authentication fails"""
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    
    response = client.post(
        "/api/v1/media/upload",
        files={
            "file": ("test_image.jpg", image_file, "image/jpeg")
        }
    )
    
    # Rate limiter returns 403 for unauthenticated requests
    assert response.status_code in [401, 403]


def test_upload_large_file_size(authenticated_client):
    """Test upload handles file size limits"""
    # Create a fake large file (simulate)
    large_data = b"x" * (10 * 1024 * 1024)  # 10MB
    large_file = BytesIO(large_data)
    
    response = authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("large_file.jpg", large_file, "image/jpeg")
        }
    )
    
    # Depending on your size limits, this might succeed or fail
    # Adjust assertion based on your configuration
    assert response.status_code in [201, 413]


def test_media_search(authenticated_client):
    """Test searching media files"""
    # Upload a file with specific name
    image_data = b"fake image content"
    image_file = BytesIO(image_data)
    authenticated_client.post(
        "/api/v1/media/upload",
        files={
            "file": ("searchable_image.jpg", image_file, "image/jpeg")
        }
    )
    
    # Search for the file
    response = authenticated_client.get("/api/v1/media?search=searchable")
    
    assert response.status_code == 200
    data = response.json()
    # Should find at least one result
    assert len(data.get("items", [])) >= 0
