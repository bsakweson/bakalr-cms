"""
Simple test script for authentication endpoints
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
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_auth_flow():
    """Test complete authentication flow"""
    
    # 1. Register a new user
    print("\n🔵 Testing User Registration...")
    register_data = {
        "email": "test@example.com",
        "password": "SecurePassword123!",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    print_response("REGISTER", response)
    
    if response.status_code != 201:
        print("\n❌ Registration failed!")
        return
    
    tokens = response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    print(f"\n✅ Registration successful!")
    print(f"Access Token: {access_token[:50]}...")
    print(f"Refresh Token: {refresh_token[:50]}...")
    
    # 2. Get current user info
    print("\n🔵 Testing Get Current User...")
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print_response("GET CURRENT USER", response)
    
    if response.status_code == 200:
        print("\n✅ Get current user successful!")
    
    # 3. Login with the same credentials
    print("\n🔵 Testing Login...")
    login_data = {
        "email": "test@example.com",
        "password": "SecurePassword123!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print_response("LOGIN", response)
    
    if response.status_code == 200:
        print("\n✅ Login successful!")
        tokens = response.json()
        new_access_token = tokens["access_token"]
        print(f"New Access Token: {new_access_token[:50]}...")
    
    # 4. Refresh token
    print("\n🔵 Testing Token Refresh...")
    refresh_data = {
        "refresh_token": refresh_token
    }
    
    response = requests.post(f"{BASE_URL}/auth/refresh", json=refresh_data)
    print_response("REFRESH TOKEN", response)
    
    if response.status_code == 200:
        print("\n✅ Token refresh successful!")
        tokens = response.json()
        refreshed_access_token = tokens["access_token"]
        print(f"Refreshed Access Token: {refreshed_access_token[:50]}...")
    
    # 5. Change password
    print("\n🔵 Testing Password Change...")
    password_change_data = {
        "current_password": "SecurePassword123!",
        "new_password": "NewSecurePassword456!"
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/change-password",
        json=password_change_data,
        headers=headers
    )
    print_response("CHANGE PASSWORD", response)
    
    if response.status_code == 200:
        print("\n✅ Password change successful!")
    
    # 6. Login with new password
    print("\n🔵 Testing Login with New Password...")
    login_data = {
        "email": "test@example.com",
        "password": "NewSecurePassword456!"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print_response("LOGIN WITH NEW PASSWORD", response)
    
    if response.status_code == 200:
        print("\n✅ Login with new password successful!")
    
    # 7. Logout
    print("\n🔵 Testing Logout...")
    response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    print_response("LOGOUT", response)
    
    if response.status_code == 200:
        print("\n✅ Logout successful!")
    
    print("\n" + "="*60)
    print("  🎉 All authentication tests passed!")
    print("="*60 + "\n")

if __name__ == "__main__":
    try:
        test_auth_flow()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("   Make sure the server is running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
