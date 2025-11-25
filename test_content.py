"""
Test script for content management endpoints
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_response(title, response):
    """Print formatted response"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

def test_content_flow():
    """Test complete content management flow"""
    
    # 1. Register and login
    print("\n🔵 Setting up authentication...")
    register_data = {
        "email": "content_test@example.com",
        "password": "TestPassword123!",
        "username": "contentuser",
        "first_name": "Content",
        "last_name": "Tester"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code != 201:
        # Try login instead
        login_data = {"email": register_data["email"], "password": register_data["password"]}
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    tokens = response.json()
    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    print(f"✅ Authenticated as {register_data['email']}")
    
    # 2. Create a content type
    print("\n🔵 Creating content type...")
    content_type_data = {
        "name": "Blog Post",
        "api_id": "blog_post",
        "description": "A blog post content type",
        "fields": [
            {
                "name": "title",
                "type": "text",
                "required": True,
                "localized": True,
                "help_text": "The title of the blog post"
            },
            {
                "name": "body",
                "type": "textarea",
                "required": True,
                "localized": True,
                "help_text": "The main content of the blog post"
            },
            {
                "name": "author",
                "type": "text",
                "required": False,
                "help_text": "Author name"
            },
            {
                "name": "published_date",
                "type": "date",
                "required": False
            },
            {
                "name": "featured",
                "type": "boolean",
                "default": False
            }
        ],
        "display_field": "title"
    }
    
    response = requests.post(f"{BASE_URL}/content/types", json=content_type_data, headers=headers)
    print_response("CREATE CONTENT TYPE", response)
    
    if response.status_code != 201:
        print("\n❌ Failed to create content type!")
        return
    
    content_type = response.json()
    content_type_id = content_type["id"]
    print(f"\n✅ Content type created with ID: {content_type_id}")
    
    # 3. List content types
    print("\n🔵 Listing content types...")
    response = requests.get(f"{BASE_URL}/content/types", headers=headers)
    print_response("LIST CONTENT TYPES", response)
    
    # 4. Create a content entry (draft)
    print("\n🔵 Creating content entry (draft)...")
    entry_data = {
        "content_type_id": content_type_id,
        "data": {
            "title": "My First Blog Post",
            "body": "This is the content of my first blog post. It's amazing!",
            "author": "Content Tester",
            "published_date": "2025-11-24",
            "featured": True
        },
        "slug": "my-first-blog-post",
        "status": "draft",
        "seo_title": "My First Blog Post - Amazing Content",
        "seo_description": "Read about my first blog post experience",
        "seo_keywords": "blog, first post, amazing"
    }
    
    response = requests.post(f"{BASE_URL}/content/entries", json=entry_data, headers=headers)
    print_response("CREATE CONTENT ENTRY", response)
    
    if response.status_code != 201:
        print("\n❌ Failed to create content entry!")
        return
    
    entry = response.json()
    entry_id = entry["id"]
    print(f"\n✅ Content entry created with ID: {entry_id}")
    
    # 5. Get the content entry
    print("\n🔵 Getting content entry...")
    response = requests.get(f"{BASE_URL}/content/entries/{entry_id}", headers=headers)
    print_response("GET CONTENT ENTRY", response)
    
    # 6. Update the content entry
    print("\n🔵 Updating content entry...")
    update_data = {
        "data": {
            "title": "My First Blog Post (Updated)",
            "body": "This is the UPDATED content of my first blog post. It's even more amazing!",
            "author": "Content Tester",
            "published_date": "2025-11-24",
            "featured": True
        },
        "seo_title": "My First Blog Post (Updated) - Amazing Content"
    }
    
    response = requests.put(f"{BASE_URL}/content/entries/{entry_id}", json=update_data, headers=headers)
    print_response("UPDATE CONTENT ENTRY", response)
    
    if response.status_code == 200:
        print("\n✅ Content entry updated!")
    
    # 7. Publish the content entry
    print("\n🔵 Publishing content entry...")
    publish_data = {}
    
    response = requests.post(f"{BASE_URL}/content/entries/{entry_id}/publish", json=publish_data, headers=headers)
    print_response("PUBLISH CONTENT ENTRY", response)
    
    if response.status_code == 200:
        print("\n✅ Content entry published!")
    
    # 8. List all entries
    print("\n🔵 Listing all content entries...")
    response = requests.get(f"{BASE_URL}/content/entries", headers=headers)
    print_response("LIST CONTENT ENTRIES", response)
    
    # 9. Filter entries by status
    print("\n🔵 Listing published entries...")
    response = requests.get(f"{BASE_URL}/content/entries?status=published", headers=headers)
    print_response("LIST PUBLISHED ENTRIES", response)
    
    # 10. Create another entry
    print("\n🔵 Creating second content entry...")
    entry_data2 = {
        "content_type_id": content_type_id,
        "data": {
            "title": "Second Blog Post",
            "body": "This is my second post!",
            "author": "Content Tester",
            "featured": False
        },
        "status": "draft"
    }
    
    response = requests.post(f"{BASE_URL}/content/entries", json=entry_data2, headers=headers)
    if response.status_code == 201:
        print("\n✅ Second entry created!")
    
    # 11. Get content type details
    print("\n🔵 Getting content type with entry count...")
    response = requests.get(f"{BASE_URL}/content/types/{content_type_id}", headers=headers)
    print_response("GET CONTENT TYPE", response)
    
    print("\n" + "="*60)
    print("  🎉 All content management tests completed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        test_content_flow()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("   Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
