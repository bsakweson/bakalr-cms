#!/usr/bin/env python3
"""
Script to seed wishlist and addresses API scopes for all organizations
and assign them to admin roles.

Run with: docker exec bakalr-backend python scripts/seed_wishlist_address_scopes.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import insert, select

from backend.db.session import SessionLocal
from backend.models.api_scope import ApiScope
from backend.models.organization import Organization
from backend.models.rbac import Role, role_api_scopes

# Scopes to add
WISHLIST_ADDRESS_SCOPES = [
    {
        "name": "wishlist.read",
        "label": "Read Wishlist",
        "description": "View wishlist items",
        "category": "customers",
        "platform": "boutique",
    },
    {
        "name": "wishlist.create",
        "label": "Create Wishlist Items",
        "description": "Add items to wishlist",
        "category": "customers",
        "platform": "boutique",
    },
    {
        "name": "wishlist.delete",
        "label": "Delete Wishlist Items",
        "description": "Remove items from wishlist",
        "category": "customers",
        "platform": "boutique",
    },
    {
        "name": "addresses.read",
        "label": "Read Addresses",
        "description": "View customer addresses",
        "category": "customers",
        "platform": "boutique",
    },
    {
        "name": "addresses.create",
        "label": "Create Addresses",
        "description": "Create new addresses",
        "category": "customers",
        "platform": "boutique",
    },
    {
        "name": "addresses.update",
        "label": "Update Addresses",
        "description": "Update existing addresses",
        "category": "customers",
        "platform": "boutique",
    },
    {
        "name": "addresses.delete",
        "label": "Delete Addresses",
        "description": "Delete addresses",
        "category": "customers",
        "platform": "boutique",
    },
]


def seed_scopes():
    """Seed wishlist and addresses scopes for all organizations."""
    db = SessionLocal()

    try:
        # Get all organizations
        orgs = db.query(Organization).all()
        print(f"Found {len(orgs)} organizations")

        for org in orgs:
            print(f"\n=== Processing organization: {org.name} (ID: {org.id}) ===")

            # Get admin role for this org
            admin_role = (
                db.query(Role).filter(Role.organization_id == org.id, Role.name == "admin").first()
            )

            if not admin_role:
                print(f"  ⚠️  No admin role found for org {org.name}")
                continue

            print(f"  Found admin role: {admin_role.id}")

            # Add each scope
            for scope_data in WISHLIST_ADDRESS_SCOPES:
                # Check if scope already exists
                existing = (
                    db.query(ApiScope)
                    .filter(ApiScope.name == scope_data["name"], ApiScope.organization_id == org.id)
                    .first()
                )

                if existing:
                    print(f"  ✓ Scope '{scope_data['name']}' already exists")
                    scope = existing
                else:
                    # Create the scope
                    scope = ApiScope(
                        name=scope_data["name"],
                        label=scope_data["label"],
                        description=scope_data["description"],
                        category=scope_data["category"],
                        platform=scope_data["platform"],
                        organization_id=org.id,
                        is_active=True,
                        is_system=True,
                    )
                    db.add(scope)
                    db.flush()  # Get the ID
                    print(f"  ✅ Created scope '{scope_data['name']}'")

                # Check if scope is already assigned to admin role
                existing_assignment = db.execute(
                    select(role_api_scopes).where(
                        role_api_scopes.c.role_id == admin_role.id,
                        role_api_scopes.c.api_scope_id == scope.id,
                    )
                ).first()

                if existing_assignment:
                    print("     → Already assigned to admin role")
                else:
                    # Assign to admin role
                    db.execute(
                        insert(role_api_scopes).values(role_id=admin_role.id, api_scope_id=scope.id)
                    )
                    print("     → Assigned to admin role")

        db.commit()
        print("\n✅ Done! All scopes seeded and assigned to admin roles.")

        # Verify
        print("\n=== Verification ===")
        for org in orgs:
            admin_role = (
                db.query(Role).filter(Role.organization_id == org.id, Role.name == "admin").first()
            )

            if admin_role:
                scopes = [
                    s.name
                    for s in admin_role.api_scopes
                    if "wishlist" in s.name or "addresses" in s.name
                ]
                print(f"{org.name}: {len(scopes)} wishlist/addresses scopes assigned")
                for s in sorted(scopes):
                    print(f"  - {s}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding wishlist and addresses API scopes...")
    print("=" * 50)
    seed_scopes()
