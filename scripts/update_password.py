#!/usr/bin/env python3
"""Update password for a user via API"""
import sys

import requests

# Use the admin user we just created to update the password
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"
API_URL = "http://localhost:8000/api/v1"

# Login as admin to get token
login_response = requests.post(
    f"{API_URL}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
)

if login_response.status_code != 200:
    print(f"❌ Failed to login as admin: {login_response.text}")
    sys.exit(1)

admin_token = login_response.json()["access_token"]
print("✅ Logged in as admin")

# Get the user ID for bsakweson@gmail.com
headers = {"Authorization": f"Bearer {admin_token}"}
users_response = requests.get(f"{API_URL}/users", headers=headers)

if users_response.status_code != 200:
    print(f"❌ Failed to get users: {users_response.text}")
    sys.exit(1)

users = users_response.json()
target_user = None
for user in users:
    if user["email"] == "bsakweson@gmail.com":
        target_user = user
        break

if not target_user:
    print("❌ User bsakweson@gmail.com not found")
    sys.exit(1)

user_id = target_user["id"]
print(f"✅ Found user: {target_user['email']} (ID: {user_id})")

# Update the password
update_response = requests.put(
    f"{API_URL}/users/{user_id}", headers=headers, json={"password": "Angelbenise123!@#"}
)

if update_response.status_code == 200:
    print("\n✅ Password updated successfully!")
    print("   Email: bsakweson@gmail.com")
    print("   Password: Angelbenise123!@#")
    print("   Organization: Bakalr Boutique")
else:
    print(f"❌ Failed to update password: {update_response.text}")
    sys.exit(1)
