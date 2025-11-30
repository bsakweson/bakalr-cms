#!/usr/bin/env python3
"""
Seed default roles and permissions for an organization
"""

import asyncio
import sys

import httpx

API_BASE = "http://localhost:8000/api/v1"


async def seed_roles(email: str, password: str):
    """Seed roles and permissions"""
    client = httpx.AsyncClient(timeout=30.0)

    try:
        # Login
        print(f"🔐 Logging in as {email}...")
        response = await client.post(
            f"{API_BASE}/auth/login", json={"email": email, "password": password}
        )

        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            return False

        data = response.json()
        token = data["access_token"]
        org_id = data.get("organization_id")

        print(f"✅ Logged in (Organization ID: {org_id})")

        headers = {"Authorization": f"Bearer {token}"}

        # Check existing roles
        response = await client.get(f"{API_BASE}/roles/", headers=headers)
        if response.status_code == 200:
            existing_roles = response.json()
            print(f"\n📋 Existing roles: {existing_roles['total']}")
            for role in existing_roles["roles"]:
                print(
                    f"   - {role['name']} (ID: {role['id']}) - {len(role['permissions'])} permissions"
                )

            if existing_roles["total"] > 0:
                print("\n✅ Roles already exist. No need to seed.")
                return True

        # Get all available permissions
        print("\n🔐 Fetching permissions...")
        response = await client.get(f"{API_BASE}/roles/permissions", headers=headers)

        if response.status_code == 200:
            perms_data = response.json()
            all_permissions = perms_data["permissions"]
            print(f"✅ Found {len(all_permissions)} permissions")

            # Create roles with permissions
            admin_perm_ids = [p["id"] for p in all_permissions]  # Admin gets all permissions
            editor_perm_ids = [
                p["id"]
                for p in all_permissions
                if "delete" not in p["name"] and "manage" not in p["name"]
            ]
            viewer_perm_ids = [
                p["id"]
                for p in all_permissions
                if p["name"].startswith("view_") or p["name"].endswith("_read")
            ]

            roles_to_create = [
                {
                    "name": "admin",
                    "description": "Full administrative access",
                    "permission_ids": admin_perm_ids,
                },
                {
                    "name": "editor",
                    "description": "Can create and edit content",
                    "permission_ids": editor_perm_ids,
                },
                {
                    "name": "viewer",
                    "description": "Read-only access",
                    "permission_ids": viewer_perm_ids,
                },
            ]

            print("\n📝 Creating roles...")
            for role_data in roles_to_create:
                response = await client.post(f"{API_BASE}/roles/", headers=headers, json=role_data)

                if response.status_code in [200, 201]:
                    role = response.json()
                    print(
                        f"   ✅ Created {role_data['name']} with {len(role_data['permission_ids'])} permissions"
                    )
                else:
                    print(f"   ⚠️  Failed to create {role_data['name']}: {response.text}")

            print("\n✅ Role seeding complete!")
            return True
        else:
            print(f"❌ Failed to fetch permissions: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await client.aclose()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python seed_roles.py <email> <password>")
        print("Example: python seed_roles.py admin@example.com password123")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    success = asyncio.run(seed_roles(email, password))
    sys.exit(0 if success else 1)
