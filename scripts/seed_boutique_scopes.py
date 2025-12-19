#!/usr/bin/env python3
"""
Seed boutique platform API scopes for all organizations.

This script:
1. Creates the standard boutique API scopes for each organization
2. Assigns API scopes to roles based on the role configuration

Usage:
    poetry run python scripts/seed_boutique_scopes.py

    # Or with Docker:
    docker exec bakalr-backend python scripts/seed_boutique_scopes.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from backend.db.session import SessionLocal
from backend.models.api_scope import ApiScope
from backend.models.organization import Organization
from backend.models.rbac import Role

# Standard boutique platform scopes
BOUTIQUE_SCOPES = [
    # Admin
    {
        "name": "admin.full",
        "label": "Admin: Full Access",
        "description": "Full administrative access to all platform features",
        "category": "Admin",
    },
    # Inventory
    {
        "name": "inventory.read",
        "label": "Inventory: Read",
        "description": "View inventory items and stock levels",
        "category": "Inventory",
    },
    {
        "name": "inventory.create",
        "label": "Inventory: Create",
        "description": "Create new inventory items",
        "category": "Inventory",
    },
    {
        "name": "inventory.update",
        "label": "Inventory: Update",
        "description": "Update inventory items and stock",
        "category": "Inventory",
    },
    {
        "name": "inventory.delete",
        "label": "Inventory: Delete",
        "description": "Delete inventory items",
        "category": "Inventory",
    },
    {
        "name": "inventory.stats",
        "label": "Inventory: Stats",
        "description": "View inventory statistics",
        "category": "Inventory",
    },
    {
        "name": "inventory.reserve",
        "label": "Inventory: Reserve",
        "description": "Reserve inventory stock",
        "category": "Inventory",
    },
    {
        "name": "inventory.release",
        "label": "Inventory: Release",
        "description": "Release reserved inventory",
        "category": "Inventory",
    },
    # Orders
    {
        "name": "orders.read",
        "label": "Orders: Read",
        "description": "View orders and order details",
        "category": "Orders",
    },
    {
        "name": "orders.create",
        "label": "Orders: Create",
        "description": "Create new orders",
        "category": "Orders",
    },
    {
        "name": "orders.update",
        "label": "Orders: Update",
        "description": "Update order status and details",
        "category": "Orders",
    },
    {
        "name": "orders.cancel",
        "label": "Orders: Cancel",
        "description": "Cancel orders",
        "category": "Orders",
    },
    {
        "name": "orders.stats",
        "label": "Orders: Stats",
        "description": "View order statistics",
        "category": "Orders",
    },
    # Customers
    {
        "name": "customers.read",
        "label": "Customers: Read",
        "description": "View customer information",
        "category": "Customers",
    },
    {
        "name": "customers.create",
        "label": "Customers: Create",
        "description": "Create new customers",
        "category": "Customers",
    },
    {
        "name": "customers.update",
        "label": "Customers: Update",
        "description": "Update customer information",
        "category": "Customers",
    },
    {
        "name": "customers.delete",
        "label": "Customers: Delete",
        "description": "Delete customers",
        "category": "Customers",
    },
    # Products
    {
        "name": "products.read",
        "label": "Products: Read",
        "description": "View products and catalog",
        "category": "Products",
    },
    {
        "name": "products.create",
        "label": "Products: Create",
        "description": "Create new products",
        "category": "Products",
    },
    {
        "name": "products.update",
        "label": "Products: Update",
        "description": "Update product information",
        "category": "Products",
    },
    {
        "name": "products.delete",
        "label": "Products: Delete",
        "description": "Delete products",
        "category": "Products",
    },
    # Payments
    {
        "name": "payments.read",
        "label": "Payments: Read",
        "description": "View payment information",
        "category": "Payments",
    },
    {
        "name": "payments.create",
        "label": "Payments: Create",
        "description": "Process payments",
        "category": "Payments",
    },
    {
        "name": "payments.refund",
        "label": "Payments: Refund",
        "description": "Process refunds",
        "category": "Payments",
    },
    # Shipping
    {
        "name": "shipping.read",
        "label": "Shipping: Read",
        "description": "View shipping information",
        "category": "Shipping",
    },
    {
        "name": "shipping.create",
        "label": "Shipping: Create",
        "description": "Create shipments",
        "category": "Shipping",
    },
    {
        "name": "shipping.update",
        "label": "Shipping: Update",
        "description": "Update shipment status",
        "category": "Shipping",
    },
    {
        "name": "shipping.track",
        "label": "Shipping: Track",
        "description": "Track shipments",
        "category": "Shipping",
    },
]


# Role to API scopes mapping
ROLE_API_SCOPES = {
    "owner": [
        "admin.full",
        "inventory.read",
        "inventory.create",
        "inventory.update",
        "inventory.delete",
        "inventory.stats",
        "inventory.reserve",
        "inventory.release",
        "orders.read",
        "orders.create",
        "orders.update",
        "orders.cancel",
        "orders.stats",
        "customers.read",
        "customers.create",
        "customers.update",
        "customers.delete",
        "products.read",
        "products.create",
        "products.update",
        "products.delete",
        "payments.read",
        "payments.create",
        "payments.refund",
        "shipping.read",
        "shipping.create",
        "shipping.update",
        "shipping.track",
    ],
    "admin": [
        "admin.full",
        "inventory.read",
        "inventory.create",
        "inventory.update",
        "inventory.delete",
        "inventory.stats",
        "inventory.reserve",
        "inventory.release",
        "orders.read",
        "orders.create",
        "orders.update",
        "orders.cancel",
        "orders.stats",
        "customers.read",
        "customers.create",
        "customers.update",
        "customers.delete",
        "products.read",
        "products.create",
        "products.update",
        "products.delete",
        "payments.read",
        "payments.create",
        "payments.refund",
        "shipping.read",
        "shipping.create",
        "shipping.update",
        "shipping.track",
    ],
    "manager": [
        "inventory.read",
        "inventory.create",
        "inventory.update",
        "inventory.stats",
        "inventory.reserve",
        "inventory.release",
        "orders.read",
        "orders.create",
        "orders.update",
        "orders.stats",
        "customers.read",
        "customers.create",
        "customers.update",
        "products.read",
        "products.create",
        "products.update",
        "payments.read",
        "payments.create",
        "shipping.read",
        "shipping.create",
        "shipping.update",
        "shipping.track",
    ],
    "inventory_manager": [
        "inventory.read",
        "inventory.create",
        "inventory.update",
        "inventory.delete",
        "inventory.stats",
        "inventory.reserve",
        "inventory.release",
        "products.read",
        "products.create",
        "products.update",
        "products.delete",
        "orders.read",
    ],
    "sales": [
        "orders.read",
        "orders.create",
        "orders.update",
        "customers.read",
        "customers.create",
        "customers.update",
        "products.read",
        "inventory.read",
        "payments.read",
        "payments.create",
        "shipping.read",
        "shipping.track",
    ],
    "employee": [
        "inventory.read",
        "products.read",
        "orders.read",
        "customers.read",
    ],
    "viewer": [
        "inventory.read",
        "products.read",
        "orders.read",
        "customers.read",
        "payments.read",
        "shipping.read",
    ],
    "editor": [
        "products.read",
        "inventory.read",
    ],
}


def seed_scopes_for_organization(db, org: Organization) -> int:
    """
    Seed boutique API scopes for a single organization.

    Returns the number of scopes created.
    """
    created = 0

    for scope_data in BOUTIQUE_SCOPES:
        # Check if scope already exists
        existing = (
            db.query(ApiScope)
            .filter(ApiScope.organization_id == org.id, ApiScope.name == scope_data["name"])
            .first()
        )

        if not existing:
            scope = ApiScope(
                name=scope_data["name"],
                label=scope_data["label"],
                description=scope_data["description"],
                category=scope_data["category"],
                platform="boutique",
                is_active=True,
                is_system=False,
                organization_id=org.id,
            )
            db.add(scope)
            created += 1

    if created > 0:
        db.commit()

    return created


def assign_scopes_to_roles(db, org: Organization) -> int:
    """
    Assign API scopes to roles for a single organization.

    Returns the number of scope assignments created.
    """
    assigned = 0

    # Get all scopes for this organization
    scopes = (
        db.query(ApiScope)
        .filter(
            ApiScope.organization_id == org.id,
            ApiScope.platform == "boutique",
            ApiScope.is_active == True,
        )
        .all()
    )

    if not scopes:
        print(f"  ⚠️  No boutique scopes found for {org.name}")
        return 0

    scope_by_name = {s.name: s for s in scopes}

    # Get all roles for this organization
    roles = db.query(Role).filter(Role.organization_id == org.id).all()

    for role in roles:
        if role.name not in ROLE_API_SCOPES:
            continue

        expected_scope_names = set(ROLE_API_SCOPES[role.name])
        current_scope_names = (
            {s.name for s in role.api_scopes} if hasattr(role, "api_scopes") else set()
        )

        # Only update if different
        if current_scope_names != expected_scope_names:
            # Clear existing
            db.execute(
                text("DELETE FROM role_api_scopes WHERE role_id = :role_id"),
                {"role_id": role.id},
            )
            db.expire(role)

            # Add expected scopes
            for scope_name in expected_scope_names:
                if scope_name in scope_by_name:
                    role.api_scopes.append(scope_by_name[scope_name])
                    assigned += 1

    if assigned > 0:
        db.commit()

    return assigned


def seed_all_organizations():
    """
    Seed boutique API scopes for all organizations.
    """
    db = SessionLocal()

    try:
        organizations = db.query(Organization).all()

        print(f"\n🏢 Found {len(organizations)} organization(s)\n")

        for org in organizations:
            print(f"📦 Processing: {org.name}")

            # Step 1: Create scopes
            scopes_created = seed_scopes_for_organization(db, org)
            if scopes_created > 0:
                print(f"  ✅ Created {scopes_created} boutique API scopes")
            else:
                print(f"  ℹ️  All {len(BOUTIQUE_SCOPES)} scopes already exist")

            # Step 2: Assign scopes to roles
            scopes_assigned = assign_scopes_to_roles(db, org)
            if scopes_assigned > 0:
                print(f"  ✅ Assigned {scopes_assigned} scope-role mappings")
            else:
                print("  ℹ️  Role-scope mappings already configured")

            print()

        print("✅ Done!")

    finally:
        db.close()


if __name__ == "__main__":
    seed_all_organizations()
