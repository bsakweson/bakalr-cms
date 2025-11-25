"""
Tests for authentication endpoints
"""
import pytest


def test_register_user(client, test_user_data):
    """Test user registration"""
    response = client.post("/api/v1/auth/register", json=test_user_data)
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["full_name"] == test_user_data["full_name"]
    assert "id" in data
    assert "password" not in data  # Password should not be returned


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
        json={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


def test_login_invalid_credentials(client, test_user_data):
    """Test login with invalid credentials fails"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user_data["email"],
            "password": "WrongPassword123!"
        }
    )
    
    assert response.status_code == 401


def test_refresh_token(client, test_user_data):
    """Test token refresh"""
    # Register and login
    client.post("/api/v1/auth/register", json=test_user_data)
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "username": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh token
    response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_get_current_user(authenticated_client):
    """Test getting current user info"""
    response = authenticated_client.get("/api/v1/users/me")
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "full_name" in data


def test_unauthorized_access(client):
    """Test accessing protected endpoint without auth fails"""
    response = client.get("/api/v1/users/me")
    
    assert response.status_code == 401


def test_logout(authenticated_client):
    """Test logout"""
    response = authenticated_client.post("/api/v1/auth/logout")
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"
