"""
Automatic permission seeding on application startup

This module ensures that essential permissions exist in the database
before the application starts handling requests. This prevents errors
when creating roles and ensures consistent permission structure across
all deployments.
"""

from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.models.rbac import Permission, Role


def seed_default_permissions(db: Session) -> None:
    """
    Seed default permissions if they don't exist.

    This runs automatically on application startup to ensure all
    expected permissions are available for role assignment.
    """
    permissions_data = [
        # Content permissions
        ("content.read", "Read content entries", "content"),
        ("content.create", "Create content entries", "content"),
        ("content.update", "Update content entries", "content"),
        ("content.delete", "Delete content entries", "content"),
        ("content.publish", "Publish content entries", "content"),
        ("content.unpublish", "Unpublish content entries", "content"),
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
        ("user.manage", "Manage user roles and permissions", "user"),
        # Role permissions
        ("role.read", "Read roles", "role"),
        ("role.create", "Create roles", "role"),
        ("role.update", "Update roles", "role"),
        ("role.delete", "Delete roles", "role"),
        # Permission permissions
        ("permission.read", "Read permissions", "permission"),
        ("permission.manage", "Manage permissions", "permission"),
        # Translation permissions
        ("translation.read", "Read translations", "translation"),
        ("translation.create", "Create translations", "translation"),
        ("translation.update", "Update translations", "translation"),
        ("translation.delete", "Delete translations", "translation"),
        # Locale permissions
        ("locale.read", "Read locales", "locale"),
        ("locale.create", "Create locales", "locale"),
        ("locale.update", "Update locales", "locale"),
        ("locale.delete", "Delete locales", "locale"),
        # Webhook permissions
        ("webhook.read", "Read webhooks", "webhook"),
        ("webhook.create", "Create webhooks", "webhook"),
        ("webhook.update", "Update webhooks", "webhook"),
        ("webhook.delete", "Delete webhooks", "webhook"),
        # SEO permissions
        ("seo.read", "Read SEO metadata", "seo"),
        ("seo.update", "Update SEO metadata", "seo"),
        # Analytics permissions
        ("analytics.view", "View analytics", "analytics"),
        ("analytics.export", "Export analytics data", "analytics"),
        # Audit permissions
        ("audit.view", "View audit logs", "audit"),
        # Organization permissions
        ("organization.read", "Read organization details", "organization"),
        ("organization.update", "Update organization settings", "organization"),
        ("organization.delete", "Delete organization", "organization"),
        # Theme permissions
        ("theme.read", "Read themes", "theme"),
        ("theme.create", "Create themes", "theme"),
        ("theme.update", "Update themes", "theme"),
        ("theme.delete", "Delete themes", "theme"),
        # Template permissions
        ("template.read", "Read content templates", "template"),
        ("template.create", "Create content templates", "template"),
        ("template.update", "Update content templates", "template"),
        ("template.delete", "Delete content templates", "template"),
        # Notification permissions
        ("notification.read", "Read notifications", "notification"),
        ("notification.create", "Create notifications", "notification"),
        ("notification.delete", "Delete notifications", "notification"),
        # System permissions (typically for super admins only)
        ("system.admin", "Full system administration", "system"),
        ("system.settings", "Manage system settings", "system"),
    ]

    created_count = 0
    existing_count = 0

    for name, description, category in permissions_data:
        # Use get-or-create pattern with immediate commit to avoid race conditions
        existing = db.query(Permission).filter(Permission.name == name).first()
        if not existing:
            try:
                permission = Permission(name=name, description=description, category=category)
                db.add(permission)
                db.commit()
                created_count += 1
            except Exception:
                # Another process may have created it concurrently
                db.rollback()
                existing_count += 1
        else:
            existing_count += 1

    if created_count > 0:
        print(f"✅ Seeded {created_count} new permissions")
    if existing_count > 0:
        print(f"ℹ️  {existing_count} permissions already exist")


def init_permissions():
    """
    Initialize permissions on application startup.

    This function is called from the FastAPI lifespan event.
    """
    db = SessionLocal()
    try:
        seed_default_permissions(db)
        assign_default_role_permissions(db)
    finally:
        db.close()


def assign_default_role_permissions(db: Session) -> None:
    """
    Ensure all organizations have the three default roles (admin, editor, viewer)
    with appropriate permissions assigned.

    This creates missing roles and assigns/updates permissions for existing roles.

    Permission Strategy:
    - Admin: All permissions except system.*
    - Editor: Content, media, translation, SEO permissions (no user/role management)
    - Viewer: Read-only permissions across all categories
    """

    # Define role configurations
    role_configs = {
        "admin": {
            "description": "Organization administrator with full management access",
            "level": 80,
            "permissions": [
                # Content management (full control)
                "content.read",
                "content.create",
                "content.update",
                "content.delete",
                "content.publish",
                "content.unpublish",
                "content_type.read",
                "content_type.create",
                "content_type.update",
                "content_type.delete",
                # Media management (full control)
                "media.read",
                "media.upload",
                "media.update",
                "media.delete",
                # User management (full control)
                "user.read",
                "user.create",
                "user.update",
                "user.delete",
                "user.manage",
                # Role management (full control)
                "role.read",
                "role.create",
                "role.update",
                "role.delete",
                "permission.read",
                "permission.assign",
                # Organization management
                "organization.read",
                "organization.update",
                "organization.settings",
                # Translation management
                "translation.read",
                "translation.create",
                "translation.update",
                "translation.delete",
                "locale.read",
                "locale.create",
                "locale.update",
                "locale.delete",
                # SEO management
                "seo.read",
                "seo.update",
                # Webhook management
                "webhook.read",
                "webhook.create",
                "webhook.update",
                "webhook.delete",
                # Analytics access
                "analytics.read",
                # API key management
                "api_key.read",
                "api_key.create",
                "api_key.delete",
                # Audit logs
                "audit_log.read",
                # Theme management
                "theme.read",
                "theme.create",
                "theme.update",
                "theme.delete",
                # Template management
                "template.read",
                "template.create",
                "template.update",
                "template.delete",
                # Notification management
                "notification.read",
                "notification.create",
                "notification.delete",
            ],
        },
        "editor": {
            "description": "Content editor with content and media management access",
            "level": 50,
            "permissions": [
                # Content management (full control)
                "content.read",
                "content.create",
                "content.update",
                "content.delete",
                "content.publish",
                "content.unpublish",
                "content_type.read",
                # Media management (full control)
                "media.read",
                "media.upload",
                "media.update",
                "media.delete",
                # Translation management
                "translation.read",
                "translation.create",
                "translation.update",
                "translation.delete",
                "locale.read",
                # SEO management
                "seo.read",
                "seo.update",
                # Template usage
                "template.read",
                # Notifications (read only)
                "notification.read",
                # Analytics (read only)
                "analytics.read",
            ],
        },
        "viewer": {
            "description": "Read-only access to content and media",
            "level": 20,
            "permissions": [
                # Read-only access to content
                "content.read",
                "content_type.read",
                # Read-only access to media
                "media.read",
                # Read-only access to translations
                "translation.read",
                "locale.read",
                # Read-only access to SEO
                "seo.read",
                # Read-only access to templates
                "template.read",
                # Read-only access to notifications
                "notification.read",
                # Read-only access to analytics
                "analytics.read",
            ],
        },
    }

    # Get all organizations
    from backend.models.organization import Organization

    organizations = db.query(Organization).all()

    roles_created = 0
    roles_updated = 0

    for org in organizations:
        for role_name, config in role_configs.items():
            # Get or create role
            role = (
                db.query(Role)
                .filter(Role.name == role_name, Role.organization_id == org.id)
                .first()
            )

            if not role:
                # Create the role
                role = Role(
                    organization_id=org.id,
                    name=role_name,
                    description=config["description"],
                    is_system_role=True,
                    level=config["level"],
                )
                db.add(role)
                db.flush()
                roles_created += 1

            # Get all permissions that should be assigned
            permissions = (
                db.query(Permission).filter(Permission.name.in_(config["permissions"])).all()
            )

            # Update permissions if different from current
            current_permission_names = {p.name for p in role.permissions}
            expected_permission_names = set(config["permissions"])

            if current_permission_names != expected_permission_names:
                # Clear existing permissions and add new ones safely
                role.permissions.clear()
                db.flush()
                for perm in permissions:
                    role.permissions.append(perm)
                roles_updated += 1

    if roles_created > 0 or roles_updated > 0:
        db.commit()
        if roles_created > 0:
            print(f"✅ Created {roles_created} default roles")
        if roles_updated > 0:
            print(f"✅ Updated permissions for {roles_updated} roles")
    else:
        print("ℹ️  All roles already configured correctly")
