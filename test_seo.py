"""
SEO Management API Tests
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.seo_utils import generate_slug, validate_slug
import json
import os
from datetime import datetime

# Remove test database if exists
if os.path.exists("bakalr_cms.db"):
    os.remove("bakalr_cms.db")

# Import after cleanup to create fresh DB
from backend.db.base import Base
from backend.db.session import engine
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# Test data
TEST_ORG = "seo-test-org"
TEST_EMAIL = "seotest@example.com"
TEST_PASSWORD = "SecurePass123!"

# Global token storage
auth_token = None
test_entry_id = None


def get_auth_headers():
    """Get authorization headers"""
    global auth_token
    
    if not auth_token:
        # Register user
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "organization_name": TEST_ORG,
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": "SEO Test User"
            }
        )
        
        # Login with JSON
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )
        
        if response.status_code == 200:
            auth_token = response.json()["access_token"]
        else:
            raise Exception(f"Login failed: {response.json()}")
    
    return {"Authorization": f"Bearer {auth_token}"}


def create_test_content():
    """Create test content entry"""
    global test_entry_id
    
    if test_entry_id:
        return test_entry_id  # Return cached entry
    
    headers = get_auth_headers()
    
    # Create content type
    ct_response = client.post(
        "/api/v1/content/types",
        headers=headers,
        json={
            "name": "SEO Article",
            "api_id": "seo_article",
            "description": "Test content type for SEO",
            "fields": [
                {
                    "name": "title",
                    "type": "text",
                    "required": True
                }
            ]
        }
    )
    
    if ct_response.status_code not in [200, 201]:
        # If already exists, get it
        if "already exists" in str(ct_response.json().get("detail", "")):
            types_response = client.get("/api/v1/content/types", headers=headers)
            for ct in types_response.json():
                if ct["api_id"] == "seo_article":
                    content_type_id = ct["id"]
                    break
        else:
            raise Exception(f"Content type creation failed: {ct_response.json()}")
    else:
        content_type_id = ct_response.json()["id"]
    
    # Create content entry
    entry_response = client.post(
        "/api/v1/content/entries",
        headers=headers,
        json={
            "content_type_id": content_type_id,
            "slug": f"test-seo-article-{int(datetime.now().timestamp())}",
            "data": {"title": "Test SEO Article"},
            "status": "published"
        }
    )
    
    if entry_response.status_code not in [200, 201]:
        raise Exception(f"Content entry creation failed: {entry_response.json()}")
    
    test_entry_id = entry_response.json()["id"]
    
    return test_entry_id


# ==================== Slug Validation Tests ====================

def test_slug_generation():
    """Test slug generation from text"""
    assert generate_slug("Hello World") == "hello-world"
    assert generate_slug("Test Article 123") == "test-article-123"
    assert generate_slug("Special!@#$%Characters") == "specialcharacters"
    assert generate_slug("  Multiple   Spaces  ") == "multiple-spaces"
    assert generate_slug("CamelCaseText") == "camelcasetext"


def test_validate_slug_format():
    """Test slug format validation"""
    # Valid slugs
    valid = validate_slug("valid-slug-123")
    assert valid.is_valid is True
    assert len(valid.errors) == 0
    
    # Invalid: uppercase
    invalid1 = validate_slug("Invalid-Slug")
    assert invalid1.is_valid is False
    assert any("lowercase" in e for e in invalid1.errors)
    
    # Invalid: special characters
    invalid2 = validate_slug("invalid_slug!")
    assert invalid2.is_valid is False
    
    # Invalid: leading hyphen
    invalid3 = validate_slug("-leading-hyphen")
    assert invalid3.is_valid is False
    assert any("start or end" in e for e in invalid3.errors)
    
    # Invalid: consecutive hyphens
    invalid4 = validate_slug("double--hyphen")
    assert invalid4.is_valid is False
    assert any("consecutive" in e for e in invalid4.errors)


def test_validate_slug_availability():
    """Test slug availability check"""
    headers = get_auth_headers()
    entry_id = create_test_content()
    
    # Get the entry's actual slug
    entry_response = client.get(f"/api/v1/content/entries/{entry_id}", headers=headers)
    entry_slug = entry_response.json()["slug"]
    
    # Check existing slug
    response = client.post(
        f"/api/v1/seo/validate-slug?slug={entry_slug}",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_valid"] is True
    assert data["is_available"] is False
    assert "already exists" in data["errors"][0]
    assert data["suggested_slug"] is not None
    
    # Check available slug
    response2 = client.post(
        "/api/v1/seo/validate-slug?slug=new-unique-slug",
        headers=headers
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["is_valid"] is True
    assert data2["is_available"] is True


def test_generate_slug_endpoint():
    """Test slug generation endpoint"""
    headers = get_auth_headers()
    
    response = client.post(
        "/api/v1/seo/generate-slug?text=My Awesome Article Title",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "my-awesome-article-title"
    assert data["text"] == "My Awesome Article Title"


# ==================== SEO Analysis Tests ====================

def test_analyze_seo_empty():
    """Test SEO analysis with no metadata"""
    headers = get_auth_headers()
    entry_id = create_test_content()
    
    response = client.get(
        f"/api/v1/seo/analyze/{entry_id}",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["score"] == 0
    assert len(data["issues"]) > 0
    assert len(data["suggestions"]) > 0
    assert data["has_keywords"] is False
    assert data["has_og_tags"] is False


def test_update_and_analyze_seo():
    """Test SEO update and analysis"""
    headers = get_auth_headers()
    entry_id = create_test_content()
    
    # Update SEO metadata
    seo_data = {
        "seo": {
            "title": "Complete SEO Title Between 50-60 Characters Long",
            "description": "This is a complete SEO description that falls within the optimal 150-160 character range for search engine results pages and provides value.",
            "keywords": ["seo", "testing", "optimization"],
            "canonical_url": "https://example.com/test",
            "robots": "index,follow"
        },
        "open_graph": {
            "og_title": "OG Title",
            "og_description": "OG Description",
            "og_image": "https://example.com/image.jpg",
            "og_type": "article"
        },
        "twitter": {
            "twitter_card": "summary_large_image",
            "twitter_title": "Twitter Title",
            "twitter_description": "Twitter Description",
            "twitter_image": "https://example.com/image.jpg"
        }
    }
    
    update_response = client.put(
        f"/api/v1/seo/update/{entry_id}",
        headers=headers,
        json=seo_data
    )
    assert update_response.status_code == 200
    
    # Analyze updated SEO
    analyze_response = client.get(
        f"/api/v1/seo/analyze/{entry_id}",
        headers=headers
    )
    assert analyze_response.status_code == 200
    data = analyze_response.json()
    assert data["score"] > 70  # Should have good score
    assert data["has_keywords"] is True
    assert data["has_og_tags"] is True
    assert data["has_twitter_tags"] is True
    assert data["has_canonical"] is True


# ==================== Sitemap Tests ====================

def test_get_sitemap_json():
    """Test sitemap JSON endpoint"""
    headers = get_auth_headers()
    create_test_content()
    
    response = client.get(
        "/api/v1/seo/sitemap?base_url=https://example.com",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_urls"] >= 1
    assert len(data["entries"]) >= 1
    assert "generated_at" in data
    
    # Check entry structure
    entry = data["entries"][0]
    assert "loc" in entry
    assert "lastmod" in entry
    assert "changefreq" in entry
    assert "priority" in entry


def test_get_sitemap_xml():
    """Test sitemap XML endpoint"""
    create_test_content()
    
    response = client.get(
        "/api/v1/seo/sitemap.xml?base_url=https://example.com"
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    
    xml_content = response.text
    assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_content
    assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in xml_content
    assert '<url>' in xml_content
    assert '<loc>' in xml_content
    assert '</urlset>' in xml_content


# ==================== Robots.txt Tests ====================

def test_generate_robots():
    """Test robots.txt generation"""
    headers = get_auth_headers()
    
    config = {
        "user_agent": "*",
        "allow": ["/public/"],
        "disallow": ["/api/", "/admin/"],
        "crawl_delay": 5,
        "sitemap_urls": ["https://example.com/sitemap.xml"]
    }
    
    response = client.post(
        "/api/v1/seo/robots.txt",
        headers=headers,
        json=config
    )
    assert response.status_code == 200
    data = response.json()
    
    content = data["content"]
    assert "User-agent: *" in content
    assert "Allow: /public/" in content
    assert "Disallow: /api/" in content
    assert "Disallow: /admin/" in content
    assert "Crawl-delay: 5" in content
    assert "Sitemap: https://example.com/sitemap.xml" in content


def test_get_default_robots():
    """Test default robots.txt endpoint"""
    response = client.get(
        "/api/v1/seo/robots.txt?base_url=https://example.com"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    
    content = response.text
    assert "User-agent: *" in content
    assert "Allow: /" in content
    assert "Disallow: /api/" in content
    assert "Disallow: /admin/" in content
    assert "Sitemap:" in content


# ==================== Structured Data Tests ====================

def test_generate_article_structured_data():
    """Test article structured data generation"""
    headers = get_auth_headers()
    entry_id = create_test_content()
    
    response = client.post(
        f"/api/v1/seo/structured-data/article/{entry_id}?author=Test Author",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    
    assert data["type"] == "Article"
    assert "@context" in data["data"]
    assert data["data"]["@context"] == "https://schema.org"
    assert data["data"]["@type"] == "Article"
    assert "headline" in data["data"]
    assert "author" in data["data"]
    assert data["data"]["author"]["name"] == "Test Author"


# ==================== Meta Preview Tests ====================

def test_meta_preview():
    """Test meta tags preview"""
    headers = get_auth_headers()
    entry_id = create_test_content()
    
    # Update with SEO data
    seo_data = {
        "seo": {
            "title": "Test Title",
            "description": "Test Description"
        },
        "open_graph": {
            "og_title": "OG Title",
            "og_description": "OG Description",
            "og_image": "https://example.com/og.jpg"
        },
        "twitter": {
            "twitter_title": "Twitter Title",
            "twitter_description": "Twitter Description",
            "twitter_image": "https://example.com/twitter.jpg",
            "twitter_card": "summary"
        }
    }
    
    client.put(
        f"/api/v1/seo/update/{entry_id}",
        headers=headers,
        json=seo_data
    )
    
    # Get preview
    response = client.get(
        f"/api/v1/seo/meta-preview/{entry_id}",
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    
    # Check Google preview
    assert data["google"]["title"] == "Test Title"
    assert data["google"]["description"] == "Test Description"
    
    # Check Facebook preview
    assert data["facebook"]["title"] == "OG Title"
    assert data["facebook"]["description"] == "OG Description"
    assert data["facebook"]["image"] == "https://example.com/og.jpg"
    
    # Check Twitter preview
    assert data["twitter"]["title"] == "Twitter Title"
    assert data["twitter"]["description"] == "Twitter Description"
    assert data["twitter"]["image"] == "https://example.com/twitter.jpg"
    assert data["twitter"]["card_type"] == "summary"


# ==================== Error Handling Tests ====================

def test_analyze_nonexistent_entry():
    """Test analyzing non-existent entry"""
    headers = get_auth_headers()
    
    response = client.get(
        "/api/v1/seo/analyze/999999",
        headers=headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_nonexistent_entry():
    """Test updating non-existent entry"""
    headers = get_auth_headers()
    
    response = client.put(
        "/api/v1/seo/update/999999",
        headers=headers,
        json={"seo": {"title": "Test"}}
    )
    assert response.status_code == 404


def test_structured_data_nonexistent_entry():
    """Test generating structured data for non-existent entry"""
    headers = get_auth_headers()
    
    response = client.post(
        "/api/v1/seo/structured-data/article/999999",
        headers=headers
    )
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
