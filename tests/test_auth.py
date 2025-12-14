"""
Tests for authentication endpoints
"""

from backend.main import app
from backend.models.user import User


def verify_user_email(email: str):
    """Helper to verify a user's email for test purposes"""
    from backend.core.dependencies import get_db

    db_generator = app.dependency_overrides[get_db]()
    db = next(db_generator)
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.is_email_verified = True
            db.commit()
    finally:
        try:
            next(db_generator)
        except StopIteration:
            pass


def test_register_user(client, test_user_data):
    """Test user registration"""
    response = client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_user_data["email"]
    assert "id" in data["user"]
    assert "password" not in data["user"]  # Password should not be returned


def test_register_duplicate_email(client, test_user_data):
    """Test registration with duplicate email fails"""
    # Register first time
    client.post("/api/v1/auth/register", json=test_user_data)

    # Try to register again with same email
    response = client.post("/api/v1/auth/register", json=test_user_data)

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


def test_login_success(client, test_user_data):
    """Test successful login"""
    # Register user first
    client.post("/api/v1/auth/register", json=test_user_data)

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client, test_user_data):
    """Test login with invalid credentials fails"""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": "WrongPassword123!"},
    )

    assert response.status_code == 401


def test_refresh_token(client, test_user_data):
    """Test token refresh"""
    # Register and login
    client.post("/api/v1/auth/register", json=test_user_data)
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )

    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_get_current_user(authenticated_client):
    """Test getting current user info"""
    response = authenticated_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data


def test_unauthorized_access(client):
    """Test accessing protected endpoint without auth fails"""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 403


def test_logout(authenticated_client):
    """Test logout"""
    response = authenticated_client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


# ==================== Account Deletion Tests ====================


def test_delete_account_success(client, test_user_data):
    """Test successful account deletion for regular user"""
    # Register user
    client.post("/api/v1/auth/register", json=test_user_data)

    # Verify user's email so they can perform actions
    verify_user_email(test_user_data["email"])

    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    token = login_response.json()["access_token"]

    # Delete account - pass headers directly to the request
    response = client.request(
        "DELETE",
        "/api/v1/auth/account",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "password": test_user_data["password"],
            "confirmation": "DELETE",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data["message"].lower()
    assert data["deleted_users_count"] == 1

    # Verify user can no longer login
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert login_response.status_code == 401


def test_delete_account_wrong_password(authenticated_client, test_user_data):
    """Test account deletion fails with wrong password"""
    response = authenticated_client.request(
        "DELETE",
        "/api/v1/auth/account",
        json={
            "password": "WrongPassword123!",
            "confirmation": "DELETE",
        },
    )

    assert response.status_code == 401  # Unauthorized for wrong password
    assert (
        "invalid" in response.json()["detail"].lower()
        or "password" in response.json()["detail"].lower()
    )


def test_delete_account_wrong_confirmation(authenticated_client, test_user_data):
    """Test account deletion fails without typing DELETE"""
    response = authenticated_client.request(
        "DELETE",
        "/api/v1/auth/account",
        json={
            "password": test_user_data["password"],
            "confirmation": "delete",  # lowercase should fail
        },
    )

    assert response.status_code == 400
    assert "DELETE" in response.json()["detail"]


def test_delete_account_missing_confirmation(authenticated_client, test_user_data):
    """Test account deletion fails without confirmation"""
    response = authenticated_client.request(
        "DELETE",
        "/api/v1/auth/account",
        json={
            "password": test_user_data["password"],
        },
    )

    assert response.status_code == 422  # Validation error


def test_delete_account_unauthenticated(client):
    """Test account deletion fails without authentication"""
    response = client.request(
        "DELETE",
        "/api/v1/auth/account",
        json={
            "password": "TestPass123!",
            "confirmation": "DELETE",
        },
    )

    assert response.status_code == 403


def test_delete_organization_owner_deletes_org(client, db_session):
    """Test organization owner deletion deletes entire organization"""
    from backend.models.organization import Organization
    from backend.models.user import User

    # Register owner
    owner_data = {
        "email": "owner@example.com",
        "password": "OwnerPass123!",
        "full_name": "Org Owner",
        "organization_name": "Test Organization",
    }
    register_response = client.post("/api/v1/auth/register", json=owner_data)
    assert register_response.status_code == 201

    owner_token = register_response.json()["access_token"]
    org_id = register_response.json()["user"]["organization_id"]

    # Verify email for the owner
    verify_user_email(owner_data["email"])

    # Verify organization exists
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is not None

    # Delete owner account - pass headers directly to request
    response = client.request(
        "DELETE",
        "/api/v1/auth/account",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "password": owner_data["password"],
            "confirmation": "DELETE",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "deleted" in data["message"].lower()
    assert data["deleted_organization"] is not None  # Organization name is returned
    assert data["deleted_users_count"] >= 1

    # Verify organization is deleted
    db_session.expire_all()
    org = db_session.query(Organization).filter(Organization.id == org_id).first()
    assert org is None

    # Verify owner user is deleted
    user = db_session.query(User).filter(User.email == owner_data["email"]).first()
    assert user is None


# ==================== Profile Management Tests ====================


def test_get_profile(authenticated_client, test_user_data):
    """Test getting current user profile"""
    response = authenticated_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert "first_name" in data
    assert "last_name" in data
    assert "avatar_url" in data
    assert "gravatar_url" in data
    assert "bio" in data
    assert "preferences" in data


def test_gravatar_url_in_profile(authenticated_client, test_user_data):
    """Test that Gravatar URL is included in user profile"""
    response = authenticated_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    data = response.json()

    # Gravatar URL should be present
    assert "gravatar_url" in data
    assert data["gravatar_url"] is not None

    # Should be a valid Gravatar URL
    assert "gravatar.com/avatar/" in data["gravatar_url"]

    # Should include default and size parameters
    assert "d=" in data["gravatar_url"]  # default parameter
    assert "s=" in data["gravatar_url"]  # size parameter


def test_gravatar_url_in_login_response(client, test_user_data):
    """Test that Gravatar URL is included in login response"""
    # Register user
    client.post("/api/v1/auth/register", json=test_user_data)
    verify_user_email(test_user_data["email"])

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )

    assert response.status_code == 200
    data = response.json()

    # User object should contain gravatar_url
    assert "user" in data
    assert "gravatar_url" in data["user"]
    assert data["user"]["gravatar_url"] is not None
    assert "gravatar.com/avatar/" in data["user"]["gravatar_url"]


def test_update_profile_first_name(authenticated_client):
    """Test updating first name"""
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"first_name": "UpdatedFirst"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "UpdatedFirst"


def test_update_profile_last_name(authenticated_client):
    """Test updating last name"""
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"last_name": "UpdatedLast"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["last_name"] == "UpdatedLast"


def test_update_profile_full_name(authenticated_client):
    """Test updating profile with full_name (splits into first/last)"""
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"full_name": "John Smith"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Smith"


def test_update_profile_bio(authenticated_client):
    """Test updating bio"""
    bio_text = "This is my bio. I love coding!"
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"bio": bio_text},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == bio_text


def test_update_profile_username(authenticated_client):
    """Test updating username"""
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"username": "newusername123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newusername123"


def test_update_profile_username_already_taken(client, test_user_data):
    """Test updating username to one that's already taken"""
    # Register first user
    first_register = client.post("/api/v1/auth/register", json=test_user_data)
    first_token = first_register.json()["access_token"]

    # Verify first user's email
    verify_user_email(test_user_data["email"])

    # First user sets a username
    first_headers = {"Authorization": f"Bearer {first_token}", "Content-Type": "application/json"}
    client.put(
        "/api/v1/auth/profile",
        headers=first_headers,
        json={"username": "takenusername"},
    )

    # Register second user
    second_user = {
        "email": "second@example.com",
        "password": "TestPass123!",
        "full_name": "Second User",
        "organization_name": "Second Org",
    }
    second_register = client.post("/api/v1/auth/register", json=second_user)
    second_token = second_register.json()["access_token"]

    # Verify second user's email
    verify_user_email(second_user["email"])

    # Second user tries to use the same username
    second_headers = {"Authorization": f"Bearer {second_token}", "Content-Type": "application/json"}
    response = client.put(
        "/api/v1/auth/profile",
        headers=second_headers,
        json={"username": "takenusername"},
    )

    assert response.status_code == 400
    assert "username" in response.json()["detail"].lower()


def test_update_profile_email(authenticated_client, test_user_data):
    """Test updating email (resets verification)"""
    new_email = "newemail@example.com"
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"email": new_email},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == new_email
    assert data["is_email_verified"] is False


def test_update_profile_email_already_taken(client, test_user_data):
    """Test updating email to one that's already taken"""
    # Register first user
    client.post("/api/v1/auth/register", json=test_user_data)

    # Register second user with different email
    second_user = {
        "email": "second@example.com",
        "password": "TestPass123!",
        "full_name": "Second User",
        "organization_name": "Second Org",
    }
    register_response = client.post("/api/v1/auth/register", json=second_user)
    token = register_response.json()["access_token"]

    # Verify second user's email so they can update profile
    verify_user_email(second_user["email"])

    # Try to update second user's email to first user's email
    response = client.put(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": test_user_data["email"]},
    )

    assert response.status_code == 400
    assert "email" in response.json()["detail"].lower()


def test_update_profile_avatar_url(authenticated_client):
    """Test updating avatar URL"""
    avatar_url = "https://cdn.example.com/avatars/my-avatar.jpg"
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"avatar_url": avatar_url},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] == avatar_url


def test_update_profile_clear_avatar(authenticated_client):
    """Test clearing avatar URL by setting to empty string"""
    # First set an avatar
    authenticated_client.put(
        "/api/v1/auth/profile",
        json={"avatar_url": "https://example.com/avatar.jpg"},
    )

    # Then clear it
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"avatar_url": ""},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["avatar_url"] == "" or data["avatar_url"] is None


def test_update_profile_preferences(authenticated_client):
    """Test updating preferences JSON"""
    import json

    preferences = json.dumps(
        {"theme": "dark", "language": "en", "notifications": {"email": True, "push": False}}
    )

    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={"preferences": preferences},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["preferences"] is not None
    prefs = json.loads(data["preferences"])
    assert prefs["theme"] == "dark"
    assert prefs["language"] == "en"


def test_update_profile_multiple_fields(authenticated_client):
    """Test updating multiple profile fields at once"""
    response = authenticated_client.put(
        "/api/v1/auth/profile",
        json={
            "first_name": "MultiUpdate",
            "last_name": "Test",
            "bio": "Updated bio",
            "username": "multiupdate",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "MultiUpdate"
    assert data["last_name"] == "Test"
    assert data["bio"] == "Updated bio"
    assert data["username"] == "multiupdate"


def test_update_profile_unauthenticated(client):
    """Test updating profile without authentication fails"""
    response = client.put(
        "/api/v1/auth/profile",
        json={"first_name": "Hacker"},
    )

    assert response.status_code == 403


# ==================== Password Change Tests ====================


def test_change_password_success(authenticated_client, test_user_data):
    """Test successful password change"""
    new_password = "NewSecurePass123!"
    response = authenticated_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": test_user_data["password"],
            "new_password": new_password,
        },
    )

    assert response.status_code == 200


def test_change_password_wrong_current(authenticated_client):
    """Test password change fails with wrong current password"""
    response = authenticated_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": "WrongPassword123!",
            "new_password": "NewSecurePass123!",
        },
    )

    assert response.status_code == 400
    assert "current password" in response.json()["detail"].lower()


# ==================== Avatar Upload Tests ====================


def test_upload_avatar_success(authenticated_client):
    """Test successful avatar upload"""
    import io

    from PIL import Image

    # Create a simple test image
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("test_avatar.png", img_bytes, "image/png")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "avatar_url" in data
    assert data["avatar_url"] is not None
    assert len(data["avatar_url"]) > 0
    assert data["message"] == "Avatar uploaded successfully"


def test_upload_avatar_jpeg(authenticated_client):
    """Test avatar upload with JPEG format"""
    import io

    from PIL import Image

    img = Image.new("RGB", (256, 256), color="blue")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_bytes.seek(0)

    response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("avatar.jpg", img_bytes, "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert ".jpg" in data["avatar_url"] or ".jpeg" in data["avatar_url"]


def test_upload_avatar_webp(authenticated_client):
    """Test avatar upload with WebP format"""
    import io

    from PIL import Image

    img = Image.new("RGB", (128, 128), color="green")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="WEBP")
    img_bytes.seek(0)

    response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("avatar.webp", img_bytes, "image/webp")},
    )

    assert response.status_code == 200
    data = response.json()
    assert ".webp" in data["avatar_url"]


def test_upload_avatar_invalid_type(authenticated_client):
    """Test avatar upload fails for non-image files"""
    import io

    # Create a fake text file
    text_content = b"This is not an image"
    text_file = io.BytesIO(text_content)

    response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("document.txt", text_file, "text/plain")},
    )

    assert response.status_code == 400
    assert "invalid file type" in response.json()["detail"].lower()


def test_upload_avatar_pdf_rejected(authenticated_client):
    """Test avatar upload fails for PDF files"""
    import io

    pdf_content = b"%PDF-1.4 fake pdf content"
    pdf_file = io.BytesIO(pdf_content)

    response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("document.pdf", pdf_file, "application/pdf")},
    )

    assert response.status_code == 400
    assert "invalid file type" in response.json()["detail"].lower()


def test_upload_avatar_too_large(authenticated_client):
    """Test avatar upload fails for files over 5MB"""
    import io

    # Create a file larger than 5MB
    large_content = b"x" * (6 * 1024 * 1024)  # 6MB
    large_file = io.BytesIO(large_content)

    response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("large_avatar.png", large_file, "image/png")},
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


def test_upload_avatar_empty_file(authenticated_client):
    """Test avatar upload fails for empty files"""
    import io

    empty_file = io.BytesIO(b"")

    response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("empty.png", empty_file, "image/png")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_avatar_updates_profile(authenticated_client):
    """Test that avatar upload updates the user's profile"""
    import io

    from PIL import Image

    img = Image.new("RGB", (100, 100), color="purple")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # Upload avatar
    upload_response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("profile.png", img_bytes, "image/png")},
    )
    assert upload_response.status_code == 200
    avatar_url = upload_response.json()["avatar_url"]

    # Verify profile is updated
    profile_response = authenticated_client.get("/api/v1/auth/me")
    assert profile_response.status_code == 200
    assert profile_response.json()["avatar_url"] == avatar_url


def test_upload_avatar_unauthenticated(client):
    """Test avatar upload fails without authentication"""
    import io

    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    response = client.post(
        "/api/v1/auth/avatar",
        files={"file": ("test.png", img_bytes, "image/png")},
    )

    assert response.status_code == 403


def test_delete_avatar_success(authenticated_client):
    """Test successful avatar deletion"""
    import io

    from PIL import Image

    # First upload an avatar
    img = Image.new("RGB", (100, 100), color="yellow")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    upload_response = authenticated_client.post(
        "/api/v1/auth/avatar",
        files={"file": ("avatar.png", img_bytes, "image/png")},
    )
    assert upload_response.status_code == 200

    # Now delete the avatar
    delete_response = authenticated_client.delete("/api/v1/auth/avatar")
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["message"] == "Avatar removed successfully"
    assert data["avatar_url"] is None

    # Verify profile no longer has avatar
    profile_response = authenticated_client.get("/api/v1/auth/me")
    assert profile_response.status_code == 200
    assert profile_response.json()["avatar_url"] is None


def test_delete_avatar_no_avatar(authenticated_client):
    """Test deleting avatar when none exists fails"""
    # Make sure no avatar is set first by updating profile
    authenticated_client.put(
        "/api/v1/auth/profile",
        json={"avatar_url": ""},
    )

    response = authenticated_client.delete("/api/v1/auth/avatar")
    assert response.status_code == 400
    assert "no avatar" in response.json()["detail"].lower()


def test_delete_avatar_unauthenticated(client):
    """Test avatar deletion fails without authentication"""
    response = client.delete("/api/v1/auth/avatar")
    assert response.status_code == 403
