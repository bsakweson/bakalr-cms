"""
Test script for field-level permissions
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

def test_field_permissions():
    """Test field permission endpoints"""
    
    # 1. Register and authenticate a user
    print("\n🔵 Registering test user...")
    register_data = {
        "email": "fieldtest@example.com",
        "password": "SecurePassword123!",
        "username": "fieldtestuser",
        "first_name": "Field",
        "last_name": "Test"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code == 201:
        tokens = response.json()
        access_token = tokens["access_token"]
        print(f"✅ Registered and authenticated")
    else:
        # User might already exist, try logging in
        print("User might exist, trying login...")
        login_data = {
            "username": "fieldtest@example.com",
            "password": "SecurePassword123!"
        }
        response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
        if response.status_code == 200:
            tokens = response.json()
            access_token = tokens["access_token"]
            print(f"✅ Logged in")
        else:
            print("❌ Could not authenticate")
            print_response("LOGIN ERROR", response)
            return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 2. Get current user's organization
    print("\n🔵 Getting organization info...")
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        org_id = user_data["organization_id"]
        user_id = user_data["id"]
        print(f"✅ Organization ID: {org_id}")
        print(f"✅ User ID: {user_id}")
    else:
        print_response("GET USER ERROR", response)
        return
    
    # 3. Create a content type
    print("\n🔵 Creating content type...")
    content_type_data = {
        "name": "article",
        "display_name": "Article",
        "description": "Blog article with sensitive fields",
        "schema": {
            "title": {"type": "string", "required": True},
            "content": {"type": "text", "required": True},
            "author_salary": {"type": "number", "required": False},
            "internal_notes": {"type": "text", "required": False}
        }
    }
    
    response = requests.post(
        f"{BASE_URL}/content/types",
        headers=headers,
        json=content_type_data
    )
    if response.status_code == 201:
        content_type = response.json()
        content_type_id = content_type["id"]
        print(f"✅ Created content type: {content_type_id}")
    else:
        print_response("CREATE CONTENT TYPE ERROR", response)
        return
    
    # 4. Create a role
    print("\n🔵 Creating role...")
    role_data = {
        "name": "editor",
        "display_name": "Editor",
        "description": "Can edit articles but not see salaries"
    }
    
    response = requests.post(
        f"{BASE_URL}/content/roles",
        headers=headers,
        json=role_data
    )
    if response.status_code == 201:
        role = response.json()
        role_id = role["id"]
        print(f"✅ Created role: {role_id}")
    else:
        print_response("CREATE ROLE ERROR", response)
        return
    
    # 5. Create field-level permission
    print("\n🔵 Creating field permission for 'title' field...")
    field_perm_data = {
        "role_id": role_id,
        "content_type_id": content_type_id,
        "field_name": "title",
        "permission_name": "content.edit"
    }
    
    response = requests.post(
        f"{BASE_URL}/permissions/field",
        headers=headers,
        json=field_perm_data
    )
    print_response("CREATE FIELD PERMISSION", response)
    
    if response.status_code == 201:
        field_perm = response.json()
        field_perm_id = field_perm["id"]
        print(f"✅ Created field permission: {field_perm_id}")
    
    # 6. Create bulk field permissions
    print("\n🔵 Creating bulk field permissions...")
    bulk_perm_data = {
        "role_id": role_id,
        "content_type_id": content_type_id,
        "field_names": ["content", "title"],
        "permission_name": "content.read"
    }
    
    response = requests.post(
        f"{BASE_URL}/permissions/field/bulk",
        headers=headers,
        json=bulk_perm_data
    )
    print_response("CREATE BULK FIELD PERMISSIONS", response)
    
    # 7. Get accessible fields
    print("\n🔵 Getting accessible fields for content type...")
    response = requests.get(
        f"{BASE_URL}/permissions/accessible-fields/{content_type_id}",
        headers=headers
    )
    print_response("GET ACCESSIBLE FIELDS", response)
    
    # 8. Check field permissions
    print("\n🔵 Checking field permissions...")
    check_data = {
        "role_ids": [role_id],
        "content_type_id": content_type_id,
        "field_names": ["title", "author_salary", "internal_notes"],
        "permission_name": "content.read"
    }
    
    response = requests.post(
        f"{BASE_URL}/permissions/check",
        headers=headers,
        json=check_data
    )
    print_response("CHECK FIELD PERMISSIONS", response)
    
    # 9. List role's field permissions
    print("\n🔵 Listing role's field permissions...")
    response = requests.get(
        f"{BASE_URL}/permissions/role/{role_id}/fields",
        headers=headers
    )
    print_response("LIST ROLE FIELD PERMISSIONS", response)
    
    print("\n✅ Field permission tests completed!")

if __name__ == "__main__":
    test_field_permissions()
