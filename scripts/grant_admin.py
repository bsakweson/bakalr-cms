#!/usr/bin/env python3
"""
Grant admin permissions to user for search reindexing

This script assigns the necessary permissions to reindex search.
"""

import asyncio

import httpx

# Configuration
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"


async def login() -> str:
    """Login and get access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        raise Exception(f"Login failed: {response.text}")


async def get_user_info(token: str):
    """Get current user info"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/users/me", headers=headers)
        if response.status_code == 200:
            return response.json()
        return None


async def get_user_roles(token: str, user_id: int):
    """Get user's roles"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/users/{user_id}/roles", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []


async def get_admin_role(token: str):
    """Find admin role"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/roles", headers=headers)
        if response.status_code == 200:
            roles = response.json().get("items", [])
            for role in roles:
                if role["name"].lower() in ["admin", "administrator", "super_admin"]:
                    return role
        return None


async def assign_admin_role(token: str, user_id: int, role_id: int):
    """Assign admin role to user"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/users/{user_id}/roles/{role_id}", headers=headers)
        return response.status_code == 200


async def main():
    print("🔐 Checking user permissions...")

    # Login
    token = await login()
    print("✅ Authenticated")

    # Get user info
    user = await get_user_info(token)
    if not user:
        print("❌ Could not get user info")
        return

    print(f"   User: {user['email']}")
    print(f"   ID: {user['id']}")
    print(f"   Is Superuser: {user.get('is_superuser', False)}")

    # Get user roles
    roles = await get_user_roles(token, user["id"])
    print(f"\n📋 Current roles: {len(roles)}")
    for role in roles:
        print(f"   • {role['name']}")

    # Check if user already has admin role
    has_admin = any(r["name"].lower() in ["admin", "administrator", "super_admin"] for r in roles)

    if has_admin or user.get("is_superuser"):
        print("\n✅ User already has admin permissions!")
        return

    # Try to get admin role
    admin_role = await get_admin_role(token)
    if not admin_role:
        print("\n⚠️  No admin role found. Creating one might require superuser access.")
        print("   Try making yourself a superuser in the database:")
        print(f"   UPDATE users SET is_superuser = true WHERE email = '{EMAIL}';")
        return

    print(f"\n🔍 Found admin role: {admin_role['name']} (ID: {admin_role['id']})")

    # Assign admin role
    print("\n📝 Assigning admin role...")
    success = await assign_admin_role(token, user["id"], admin_role["id"])

    if success:
        print("✅ Admin role assigned successfully!")
        print("\n🎉 You can now run: poetry run python scripts/configure_search.py")
    else:
        print("❌ Could not assign admin role")
        print("   You may need to update the database directly:")
        print(f"   UPDATE users SET is_superuser = true WHERE email = '{EMAIL}';")


if __name__ == "__main__":
    asyncio.run(main())
