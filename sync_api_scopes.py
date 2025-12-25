#!/usr/bin/env python3
"""Sync missing API scopes and roles for all organizations."""

from backend.core.seed_permissions import BOUTIQUE_SCOPES, ROLE_API_SCOPES_CONFIG
from backend.db.session import SessionLocal
from backend.models.api_scope import ApiScope
from backend.models.organization import Organization
from backend.models.rbac import Permission, Role

# Default roles configuration with their permissions
DEFAULT_ROLES = [
    {
        "name": "owner",
        "description": "Organization owner with full access to all features and settings",
        "is_system": True,
        "permissions": ["*"],  # All permissions
    },
    {
        "name": "admin",
        "description": "Full administrative access except owner management",
        "is_system": True,
        "permissions": [
            # Content Management
            "content.create",
            "content.read",
            "content.update",
            "content.delete",
            "content.publish",
            "content.unpublish",
            "content.manage",
            # Content Types
            "content.type.create",
            "content.type.read",
            "content.type.update",
            "content.type.delete",
            # Media Management
            "media.upload",
            "media.read",
            "media.update",
            "media.delete",
            # Translation
            "translation.create",
            "translation.read",
            "translation.update",
            "translation.delete",
            # Locales
            "locale.create",
            "locale.read",
            "locale.update",
            "locale.delete",
            # SEO
            "seo.read",
            "seo.update",
            # User Management (but NOT user.manage.full - owner only)
            "user.create",
            "user.read",
            "user.update",
            "user.delete",
            "user.manage",
            # Role Management (can manage roles but not elevate to owner)
            "role.create",
            "role.read",
            "role.update",
            "role.delete",
            "role.view",
            "role.manage",
            # Permissions
            "permission.read",
            "permission.manage",
            # Webhooks
            "webhook.create",
            "webhook.read",
            "webhook.update",
            "webhook.delete",
            # Notifications
            "notification.create",
            "notification.read",
            "notification.view",
            "notification.delete",
            # Analytics
            "analytics.view",
            "analytics.export",
            # Audit Logs
            "audit.view",
            "audit.logs",
            # Admin Metrics
            "admin.metrics",
            # Templates
            "template.create",
            "template.read",
            "template.update",
            "template.delete",
            # Themes
            "theme.create",
            "theme.read",
            "theme.update",
            "theme.delete",
            "theme.manage",
            # Organization (read/update only - NOT delete, NOT settings.manage)
            "organization.read",
            "organization.update",
            "organization.settings.view",
            # System settings (NOT system.admin - owner only)
            "system.settings",
            # Employees
            "employees.create",
            "employees.read",
            "employees.update",
            "employees.delete",
            "employees.manage",
            "employees.schedule",
            "employees.stats",
            "employees.self.read",
            "employees.self.update",
            # POS
            "pos.access",
            "pos.sell",
            "pos.discount",
            "pos.discount.manager",
            "pos.refund",
            "pos.void",
            "pos.cash.drawer",
            "pos.end.shift",
            "pos.reports",
            "pos.manage",
            # Inventory (full access)
            "inventory.read",
            "inventory.create",
            "inventory.update",
            "inventory.delete",
            "inventory.manage",
            "inventory.reports",
            "inventory.stock.adjust",
            "inventory.stock.transfer",
            # Products (full access)
            "products.read",
            "products.create",
            "products.update",
            "products.delete",
            "products.manage",
            "products.pricing",
            # Categories (full access)
            "categories.read",
            "categories.create",
            "categories.update",
            "categories.delete",
            "categories.manage",
            # Orders (full access)
            "orders.read",
            "orders.create",
            "orders.update",
            "orders.cancel",
            "orders.manage",
            "orders.refund",
            # Customers (full access)
            "customers.read",
            "customers.create",
            "customers.update",
            "customers.delete",
            "customers.manage",
        ],
    },
    {
        "name": "editor",
        "description": "Can create, edit, and publish content",
        "is_system": True,
        "permissions": [
            "content.create",
            "content.read",
            "content.update",
            "content.delete",
            "content.publish",
            "media.create",
            "media.read",
            "media.update",
            "media.delete",
            "translation.create",
            "translation.read",
            "translation.update",
        ],
    },
    {
        "name": "contributor",
        "description": "Can create and edit content, but cannot publish",
        "is_system": True,
        "permissions": [
            "content.create",
            "content.read",
            "content.update",
            "media.create",
            "media.read",
            "translation.read",
        ],
    },
    {
        "name": "viewer",
        "description": "Read-only access to content",
        "is_system": True,
        "permissions": [
            "content.read",
            "media.read",
            "translation.read",
        ],
    },
    {
        "name": "api_consumer",
        "description": "API access for external integrations",
        "is_system": True,
        "permissions": [
            "content.read",
            "media.read",
            "translation.read",
        ],
    },
]


def sync_roles(db, org: Organization) -> dict:
    """
    Sync default roles for an organization.

    Creates any missing roles and updates existing ones if needed.
    Returns a dict with counts of roles created and updated.
    """
    print(f"🔐 Syncing roles for {org.name}...")

    roles_created = 0
    roles_updated = 0
    role_map = {}

    for role_data in DEFAULT_ROLES:
        existing_role = (
            db.query(Role)
            .filter(
                Role.organization_id == org.id,
                Role.name == role_data["name"],
            )
            .first()
        )

        if not existing_role:
            # Create new role
            role = Role(
                organization_id=org.id,
                name=role_data["name"],
                description=role_data["description"],
                is_system_role=role_data.get("is_system", False),
            )
            db.add(role)
            db.flush()
            role_map[role_data["name"]] = role
            roles_created += 1
            print(f"   + Created role: {role_data['name']}")
        else:
            # Update existing role description if different
            if existing_role.description != role_data["description"]:
                existing_role.description = role_data["description"]
                roles_updated += 1
            role_map[role_data["name"]] = existing_role

    # Assign permissions to roles
    permissions_assigned = 0
    permissions_removed = 0
    all_permissions = db.query(Permission).all()
    permission_map = {p.name: p for p in all_permissions}

    for role_data in DEFAULT_ROLES:
        role = role_map.get(role_data["name"])
        if not role:
            continue

        current_permission_names = (
            {p.name for p in role.permissions} if hasattr(role, "permissions") else set()
        )

        # Handle wildcard permissions (owner gets all)
        if "*" in role_data["permissions"]:
            expected_permissions = set(permission_map.keys())
        else:
            expected_permissions = set(role_data["permissions"])

        # Add missing permissions
        for perm_name in expected_permissions:
            if perm_name not in current_permission_names and perm_name in permission_map:
                role.permissions.append(permission_map[perm_name])
                permissions_assigned += 1

        # Remove extra permissions (not in expected list)
        for perm_name in current_permission_names:
            if perm_name not in expected_permissions:
                perm_to_remove = permission_map.get(perm_name)
                if perm_to_remove and perm_to_remove in role.permissions:
                    role.permissions.remove(perm_to_remove)
                    permissions_removed += 1

    print(f"   ✓ Created {roles_created} new roles")
    print(f"   ✓ Updated {roles_updated} existing roles")
    print(f"   ✓ Assigned {permissions_assigned} permissions")
    print(f"   ✓ Removed {permissions_removed} permissions")

    return {
        "roles_created": roles_created,
        "roles_updated": roles_updated,
        "permissions_assigned": permissions_assigned,
        "permissions_removed": permissions_removed,
        "role_map": role_map,
    }


def sync_api_scopes(db, org: Organization, role_map: dict = None) -> dict:
    """
    Sync API scopes for an organization.

    Creates any missing scopes and assigns them to roles.
    Returns a dict with counts of scopes and mappings created.
    """
    print(f"🌱 Syncing API scopes for {org.name}...")

    scopes_created = 0
    scope_map = {}

    # Create missing scopes
    for scope_data in BOUTIQUE_SCOPES:
        existing = (
            db.query(ApiScope)
            .filter(
                ApiScope.organization_id == org.id,
                ApiScope.name == scope_data["name"],
                ApiScope.platform == "boutique",
            )
            .first()
        )

        if not existing:
            scope = ApiScope(
                organization_id=org.id,
                name=scope_data["name"],
                label=scope_data["label"],
                description=scope_data["description"],
                category=scope_data["category"],
                platform="boutique",
                is_active=True,
            )
            db.add(scope)
            db.flush()
            scope_map[scope_data["name"]] = scope
            scopes_created += 1
        else:
            scope_map[scope_data["name"]] = existing

    print(f"   ✓ Created {scopes_created} new scopes")

    # Assign scopes to roles
    if role_map is None:
        roles = db.query(Role).filter(Role.organization_id == org.id).all()
        role_map = {r.name: r for r in roles}

    mappings_created = 0

    for role_name, role in role_map.items():
        if role_name not in ROLE_API_SCOPES_CONFIG:
            continue

        expected_scope_names = ROLE_API_SCOPES_CONFIG[role_name]
        current_scope_names = (
            {s.name for s in role.api_scopes} if hasattr(role, "api_scopes") else set()
        )

        for scope_name in expected_scope_names:
            if scope_name not in current_scope_names and scope_name in scope_map:
                role.api_scopes.append(scope_map[scope_name])
                mappings_created += 1

    print(f"   ✓ Created {mappings_created} role-scope mappings")

    return {
        "scopes_created": scopes_created,
        "mappings_created": mappings_created,
        "scope_map": scope_map,
    }


def sync_all(sync_roles_flag: bool = True, sync_scopes_flag: bool = True):
    """
    Sync roles and API scopes for all organizations.

    Args:
        sync_roles_flag: Whether to sync roles
        sync_scopes_flag: Whether to sync API scopes
    """
    db = SessionLocal()

    try:
        orgs = db.query(Organization).all()

        total_stats = {
            "roles_created": 0,
            "roles_updated": 0,
            "permissions_assigned": 0,
            "permissions_removed": 0,
            "scopes_created": 0,
            "mappings_created": 0,
        }

        for org in orgs:
            role_map = None

            # Sync roles first
            if sync_roles_flag:
                role_result = sync_roles(db, org)
                role_map = role_result.get("role_map", {})
                total_stats["roles_created"] += role_result["roles_created"]
                total_stats["roles_updated"] += role_result["roles_updated"]
                total_stats["permissions_assigned"] += role_result["permissions_assigned"]
                total_stats["permissions_removed"] += role_result["permissions_removed"]

            # Then sync API scopes
            if sync_scopes_flag:
                scope_result = sync_api_scopes(db, org, role_map)
                total_stats["scopes_created"] += scope_result["scopes_created"]
                total_stats["mappings_created"] += scope_result["mappings_created"]

            print()

        db.commit()

        print("=" * 50)
        print("✅ Sync complete!")
        print(f"   Total roles created: {total_stats['roles_created']}")
        print(f"   Total roles updated: {total_stats['roles_updated']}")
        print(f"   Total permissions assigned: {total_stats['permissions_assigned']}")
        print(f"   Total permissions removed: {total_stats['permissions_removed']}")
        print(f"   Total scopes created: {total_stats['scopes_created']}")
        print(f"   Total role-scope mappings: {total_stats['mappings_created']}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during sync: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync roles and API scopes for all organizations")
    parser.add_argument("--roles-only", action="store_true", help="Only sync roles")
    parser.add_argument("--scopes-only", action="store_true", help="Only sync API scopes")
    args = parser.parse_args()

    if args.roles_only:
        sync_all(sync_roles_flag=True, sync_scopes_flag=False)
    elif args.scopes_only:
        sync_all(sync_roles_flag=False, sync_scopes_flag=True)
    else:
        sync_all()
