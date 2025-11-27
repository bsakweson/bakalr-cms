"""
Database seeding script for Bakalr CMS

Creates default roles, permissions, sample content types, and admin user.
Run with: poetry run python scripts/seed_database.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from backend.core.security import get_password_hash
from backend.db.session import SessionLocal
from backend.models.content import ContentType
from backend.models.organization import Organization
from backend.models.rbac import Permission, Role
from backend.models.translation import Locale
from backend.models.user import User
from backend.models.user_organization import UserOrganization
from backend.models.notification import Notification


def create_default_permissions(db: Session) -> dict[str, Permission]:
    """Create default permissions"""
    print("Creating default permissions...")

    permissions_data = [
        # Content permissions
        ("content.read", "Read content entries", "content"),
        ("content.create", "Create content entries", "content"),
        ("content.update", "Update content entries", "content"),
        ("content.delete", "Delete content entries", "content"),
        ("content.publish", "Publish content entries", "content"),
        # Content type permissions
        ("content_type.read", "Read content types", "content_type"),
        ("content_type.create", "Create content types", "content_type"),
        ("content_type.update", "Update content types", "content_type"),
        ("content_type.delete", "Delete content types", "content_type"),
        # Media permissions
        ("media.read", "Read media files", "media"),
        ("media.upload", "Upload media files", "media"),
        ("media.update", "Update media metadata", "media"),
        ("media.delete", "Delete media files", "media"),
        # User permissions
        ("user.read", "Read users", "user"),
        ("user.create", "Create users", "user"),
        ("user.update", "Update users", "user"),
        ("user.delete", "Delete users", "user"),
        # Role permissions
        ("role.read", "Read roles", "role"),
        ("role.create", "Create roles", "role"),
        ("role.update", "Update roles", "role"),
        ("role.delete", "Delete roles", "role"),
        # Translation permissions
        ("translation.read", "Read translations", "translation"),
        ("translation.create", "Create translations", "translation"),
        ("translation.update", "Update translations", "translation"),
        ("translation.delete", "Delete translations", "translation"),
        # Webhook permissions
        ("webhook.read", "Read webhooks", "webhook"),
        ("webhook.create", "Create webhooks", "webhook"),
        ("webhook.update", "Update webhooks", "webhook"),
        ("webhook.delete", "Delete webhooks", "webhook"),
        # System permissions
        ("system.admin", "Full system administration", "system"),
        ("analytics.view", "View analytics", "analytics"),
        ("audit.view", "View audit logs", "audit"),
    ]

    permissions = {}
    for name, description, category in permissions_data:
        perm = db.query(Permission).filter(Permission.name == name).first()
        if not perm:
            perm = Permission(name=name, description=description, category=category)
            db.add(perm)
            print(f"  ✓ Created permission: {name}")
        permissions[name] = perm

    db.commit()
    return permissions


def create_default_roles(
    db: Session, permissions: dict[str, Permission], org: Organization
) -> dict[str, Role]:
    """Create default roles with permissions"""
    print("\nCreating default roles...")

    roles_data = {
        "super_admin": {
            "description": "Full system access",
            "level": 100,
            "permissions": list(permissions.keys()),
        },
        "admin": {
            "description": "Organization administrator",
            "level": 80,
            "permissions": [
                "content.read",
                "content.create",
                "content.update",
                "content.delete",
                "content.publish",
                "content_type.read",
                "content_type.create",
                "content_type.update",
                "content_type.delete",
                "media.read",
                "media.upload",
                "media.update",
                "media.delete",
                "user.read",
                "user.create",
                "user.update",
                "translation.read",
                "translation.create",
                "translation.update",
                "translation.delete",
                "webhook.read",
                "webhook.create",
                "webhook.update",
                "webhook.delete",
                "analytics.view",
                "audit.view",
            ],
        },
        "editor": {
            "description": "Content editor",
            "level": 60,
            "permissions": [
                "content.read",
                "content.create",
                "content.update",
                "content.publish",
                "content_type.read",
                "media.read",
                "media.upload",
                "media.update",
                "translation.read",
                "translation.create",
                "translation.update",
            ],
        },
        "author": {
            "description": "Content author",
            "level": 40,
            "permissions": [
                "content.read",
                "content.create",
                "content.update",
                "content_type.read",
                "media.read",
                "media.upload",
            ],
        },
        "viewer": {
            "description": "Read-only access",
            "level": 20,
            "permissions": ["content.read", "content_type.read", "media.read"],
        },
    }

    roles = {}
    for role_name, role_info in roles_data.items():
        role = db.query(Role).filter(Role.name == role_name, Role.organization_id == org.id).first()
        if not role:
            role = Role(
                name=role_name,
                description=role_info["description"],
                level=role_info["level"],
                organization_id=org.id,
            )
            db.add(role)
            db.flush()

            # Add permissions
            for perm_name in role_info["permissions"]:
                if perm_name in permissions:
                    role.permissions.append(permissions[perm_name])

            print(f"  ✓ Created role: {role_name} ({len(role_info['permissions'])} permissions)")
        roles[role_name] = role

    db.commit()
    return roles


def create_admin_user(db: Session, roles: dict[str, Role]) -> tuple[User, Organization]:
    """Create default admin user and organization"""
    print("\nCreating admin user and organization...")

    # Check if admin already exists
    admin = db.query(User).filter(User.email == "admin@bakalr.cms").first()
    if admin:
        print("  ℹ Admin user already exists")
        org = db.query(Organization).filter(Organization.id == admin.organization_id).first()
        return admin, org

    # Create organization
    org = Organization(
        name="Bakalr CMS",
        slug="bakalr-cms",
        description="Default organization",
        plan_type="enterprise",
        is_active=True,
    )
    db.add(org)
    db.flush()

    # Create default locale for organization
    locale = Locale(
        code="en", name="English", organization_id=org.id, is_default=True, is_active=True
    )
    db.add(locale)
    db.flush()

    # Create admin user
    admin = User(
        email="admin@bakalr.cms",
        full_name="System Administrator",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_verified=True,
        organization_id=org.id,
        current_organization_id=org.id,
    )
    db.add(admin)
    db.flush()

    # Assign super_admin role
    if "super_admin" in roles:
        admin.roles.append(roles["super_admin"])

    db.commit()

    print(f"  ✓ Created organization: {org.name}")
    print(f"  ✓ Created admin user: {admin.email}")
    print("  ⚠ Default password: admin123 (CHANGE THIS!)")

    return admin, org


def create_sample_content_types(db: Session, org: Organization):
    """Create sample content types"""
    print("\nCreating sample content types...")

    content_types_data = [
        {
            "name": "Blog Post",
            "api_id": "blog_post",
            "description": "Blog post content type",
            "fields_schema": {
                "fields": [
                    {"name": "title", "type": "text", "required": True, "localized": True},
                    {"name": "slug", "type": "text", "required": True, "unique": True},
                    {"name": "excerpt", "type": "textarea", "required": False, "localized": True},
                    {"name": "content", "type": "richtext", "required": True, "localized": True},
                    {"name": "featured_image", "type": "media", "required": False},
                    {"name": "author", "type": "text", "required": True},
                    {"name": "published_date", "type": "datetime", "required": False},
                    {"name": "tags", "type": "array", "required": False},
                ]
            },
        },
        {
            "name": "Page",
            "api_id": "page",
            "description": "Static page content type",
            "fields_schema": {
                "fields": [
                    {"name": "title", "type": "text", "required": True, "localized": True},
                    {"name": "slug", "type": "text", "required": True, "unique": True},
                    {"name": "content", "type": "richtext", "required": True, "localized": True},
                    {"name": "meta_title", "type": "text", "required": False, "localized": True},
                    {
                        "name": "meta_description",
                        "type": "textarea",
                        "required": False,
                        "localized": True,
                    },
                ]
            },
        },
        {
            "name": "Product",
            "api_id": "product",
            "description": "E-commerce product content type",
            "fields_schema": {
                "fields": [
                    {"name": "name", "type": "text", "required": True, "localized": True},
                    {"name": "sku", "type": "text", "required": True, "unique": True},
                    {
                        "name": "description",
                        "type": "richtext",
                        "required": True,
                        "localized": True,
                    },
                    {"name": "price", "type": "number", "required": True},
                    {"name": "images", "type": "array", "required": False},
                    {"name": "category", "type": "text", "required": False},
                    {"name": "in_stock", "type": "boolean", "required": True},
                ]
            },
        },
    ]

    import json

    for ct_data in content_types_data:
        ct = (
            db.query(ContentType)
            .filter(ContentType.api_id == ct_data["api_id"], ContentType.organization_id == org.id)
            .first()
        )

        if not ct:
            ct = ContentType(
                name=ct_data["name"],
                api_id=ct_data["api_id"],
                description=ct_data["description"],
                fields_schema=json.dumps(ct_data["fields_schema"]),
                organization_id=org.id,
            )
            db.add(ct)
            print(f"  ✓ Created content type: {ct_data['name']}")

    db.commit()


def main():
    """Main seeding function"""
    print("=" * 60)
    print("Bakalr CMS Database Seeding")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Create permissions (system-wide, no org needed)
        permissions = create_default_permissions(db)

        # Create admin user and organization FIRST
        # This will create a temporary admin before roles exist
        print("\nCreating admin user and organization...")

        # Check if admin already exists
        admin = db.query(User).filter(User.email == "admin@bakalr.cms").first()
        if admin:
            print("  ℹ Admin user already exists")
            org = db.query(Organization).filter(Organization.id == admin.organization_id).first()
        else:
            # Create organization
            org = Organization(
                name="Bakalr CMS",
                slug="bakalr-cms",
                description="Default organization",
                plan_type="enterprise",
                is_active=True,
            )
            db.add(org)
            db.flush()

            # Create default locale for organization
            locale = Locale(
                code="en", name="English", organization_id=org.id, is_default=True, is_enabled=True
            )
            db.add(locale)
            db.flush()

            # Create admin user (without role for now)
            admin = User(
                email="admin@bakalr.cms",
                username="admin",
                first_name="System",
                last_name="Administrator",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_email_verified=True,
                organization_id=org.id,
            )
            db.add(admin)
            db.flush()  # Flush to get admin.id before creating UserOrganization

            # Create user-organization association
            user_org = UserOrganization(user_id=admin.id, organization_id=org.id, is_active=True)
            db.add(user_org)
            db.commit()

            print(f"  ✓ Created organization: {org.name}")
            print(f"  ✓ Created admin user: {admin.email}")

        # Now create roles with the organization
        roles = create_default_roles(db, permissions, org)

        # Assign super_admin role to admin if not already assigned
        if "super_admin" in roles and roles["super_admin"] not in admin.roles:
            admin.roles.append(roles["super_admin"])
            db.commit()
            print(f"  ✓ Assigned super_admin role to {admin.email}")

        # Create sample content types
        create_sample_content_types(db, org)

        print("\n" + "=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        print("\n📝 Admin Credentials:")
        print("   Email: admin@bakalr.cms")
        print("   Password: admin123")
        print("\n⚠️  IMPORTANT: Change the admin password immediately!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
