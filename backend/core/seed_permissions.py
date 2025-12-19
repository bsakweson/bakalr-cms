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


# Define role configurations as module-level constant for reuse
DEFAULT_ROLE_CONFIGS = {
    "owner": {
        "description": "Store owner with full access to everything",
        "level": 100,
        "permissions": [
            # Full system access
            "system.admin",
            "system.settings",
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
            "permission.manage",
            # Organization management (full control)
            "organization.read",
            "organization.update",
            "organization.delete",
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
            "analytics.view",
            "analytics.export",
            # Audit logs
            "audit.view",
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
    "manager": {
        "description": "Store manager with daily operations, employee, and inventory management",
        "level": 70,
        "permissions": [
            # Content management
            "content.read",
            "content.create",
            "content.update",
            "content.publish",
            "content.unpublish",
            "content_type.read",
            # Media management
            "media.read",
            "media.upload",
            "media.update",
            # User management (limited)
            "user.read",
            "user.create",
            "user.update",
            # Role read only
            "role.read",
            # Translation management
            "translation.read",
            "translation.create",
            "translation.update",
            "locale.read",
            # SEO management
            "seo.read",
            "seo.update",
            # Analytics access
            "analytics.view",
            "analytics.export",
            # Template usage
            "template.read",
            # Notifications
            "notification.read",
        ],
    },
    "inventory_manager": {
        "description": "Inventory manager with product, category, and stock management",
        "level": 50,
        "permissions": [
            # Content management (products/inventory focused)
            "content.read",
            "content.create",
            "content.update",
            "content.publish",
            "content_type.read",
            # Media management
            "media.read",
            "media.upload",
            "media.update",
            # Translation (read)
            "translation.read",
            "locale.read",
            # Analytics (read)
            "analytics.view",
            # Template usage
            "template.read",
            # Notifications
            "notification.read",
        ],
    },
    "sales": {
        "description": "Sales associate with order processing and customer assistance",
        "level": 40,
        "permissions": [
            # Content read only
            "content.read",
            "content_type.read",
            # Media read only
            "media.read",
            # Translation read only
            "translation.read",
            "locale.read",
            # Analytics read only
            "analytics.view",
            # Template read only
            "template.read",
            # Notifications
            "notification.read",
        ],
    },
    "employee": {
        "description": "General employee with basic view access",
        "level": 30,
        "permissions": [
            # Read-only access to content
            "content.read",
            "content_type.read",
            # Read-only access to media
            "media.read",
            # Read-only access to translations
            "translation.read",
            "locale.read",
            # Notifications
            "notification.read",
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
            "analytics.view",
        ],
    },
}


def seed_organization_roles(db: Session, organization_id: int) -> dict:
    """
    Seed default roles for a specific organization.

    Roles seeded: owner, admin, editor, manager, inventory_manager, sales, employee, viewer

    This should be called when creating a new organization to ensure
    all default roles are available immediately.

    Args:
        db: Database session
        organization_id: The ID of the organization to seed roles for

    Returns:
        Dictionary with created role IDs mapping role names to their IDs
    """
    created_roles = {}

    for role_name, config in DEFAULT_ROLE_CONFIGS.items():
        # Check if role already exists
        existing_role = (
            db.query(Role)
            .filter(Role.name == role_name, Role.organization_id == organization_id)
            .first()
        )

        if existing_role:
            created_roles[role_name] = existing_role.id
            continue

        # Create the role
        role = Role(
            organization_id=organization_id,
            name=role_name,
            description=config["description"],
            is_system_role=True,
            level=config["level"],
        )
        db.add(role)
        db.flush()

        # Get all permissions that should be assigned
        permissions = db.query(Permission).filter(Permission.name.in_(config["permissions"])).all()

        # Assign permissions to role
        for perm in permissions:
            role.permissions.append(perm)

        created_roles[role_name] = role.id

    db.flush()
    print(
        f"✅ Seeded default roles for organization {organization_id}: {list(created_roles.keys())}"
    )

    return created_roles


# Boutique platform API scope definitions
# These must match the scope names used in ROLE_API_SCOPES_CONFIG
BOUTIQUE_SCOPES = [
    # Admin
    {
        "name": "admin.full",
        "label": "Full Admin Access",
        "description": "Full administrative access to all platform features",
        "category": "admin",
    },
    # Inventory Scopes
    {
        "name": "inventory.read",
        "label": "Read Inventory",
        "description": "View inventory items and stock levels",
        "category": "inventory",
    },
    {
        "name": "inventory.create",
        "label": "Create Inventory",
        "description": "Create new inventory items",
        "category": "inventory",
    },
    {
        "name": "inventory.update",
        "label": "Update Inventory",
        "description": "Update inventory items and stock",
        "category": "inventory",
    },
    {
        "name": "inventory.delete",
        "label": "Delete Inventory",
        "description": "Delete inventory items",
        "category": "inventory",
    },
    {
        "name": "inventory.stats",
        "label": "Inventory Statistics",
        "description": "View inventory statistics",
        "category": "inventory",
    },
    {
        "name": "inventory.reserve",
        "label": "Reserve Inventory",
        "description": "Reserve inventory stock",
        "category": "inventory",
    },
    {
        "name": "inventory.release",
        "label": "Release Inventory",
        "description": "Release reserved inventory",
        "category": "inventory",
    },
    # Orders Scopes
    {
        "name": "orders.read",
        "label": "Read Orders",
        "description": "View orders and order details",
        "category": "orders",
    },
    {
        "name": "orders.create",
        "label": "Create Orders",
        "description": "Create new orders",
        "category": "orders",
    },
    {
        "name": "orders.update",
        "label": "Update Orders",
        "description": "Update order status and details",
        "category": "orders",
    },
    {
        "name": "orders.cancel",
        "label": "Cancel Orders",
        "description": "Cancel orders",
        "category": "orders",
    },
    {
        "name": "orders.stats",
        "label": "Order Statistics",
        "description": "View order statistics",
        "category": "orders",
    },
    # Customer Scopes
    {
        "name": "customers.read",
        "label": "Read Customers",
        "description": "View customer information",
        "category": "customers",
    },
    {
        "name": "customers.create",
        "label": "Create Customers",
        "description": "Create new customers",
        "category": "customers",
    },
    {
        "name": "customers.update",
        "label": "Update Customers",
        "description": "Update customer information",
        "category": "customers",
    },
    {
        "name": "customers.delete",
        "label": "Delete Customers",
        "description": "Delete customers",
        "category": "customers",
    },
    # Wishlist Scopes
    {
        "name": "wishlist.read",
        "label": "Read Wishlist",
        "description": "View wishlist items",
        "category": "customers",
    },
    {
        "name": "wishlist.create",
        "label": "Create Wishlist",
        "description": "Add items to wishlist",
        "category": "customers",
    },
    {
        "name": "wishlist.delete",
        "label": "Delete Wishlist",
        "description": "Remove items from wishlist",
        "category": "customers",
    },
    # Addresses Scopes
    {
        "name": "addresses.read",
        "label": "Read Addresses",
        "description": "View customer addresses",
        "category": "customers",
    },
    {
        "name": "addresses.create",
        "label": "Create Addresses",
        "description": "Create customer addresses",
        "category": "customers",
    },
    {
        "name": "addresses.update",
        "label": "Update Addresses",
        "description": "Update customer addresses",
        "category": "customers",
    },
    {
        "name": "addresses.delete",
        "label": "Delete Addresses",
        "description": "Delete customer addresses",
        "category": "customers",
    },
    # Products Scopes
    {
        "name": "products.read",
        "label": "Read Products",
        "description": "View products and catalog",
        "category": "products",
    },
    {
        "name": "products.create",
        "label": "Create Products",
        "description": "Create new products",
        "category": "products",
    },
    {
        "name": "products.update",
        "label": "Update Products",
        "description": "Update product information",
        "category": "products",
    },
    {
        "name": "products.delete",
        "label": "Delete Products",
        "description": "Delete products",
        "category": "products",
    },
    # Payments Scopes
    {
        "name": "payments.read",
        "label": "Read Payments",
        "description": "View payment information",
        "category": "payments",
    },
    {
        "name": "payments.create",
        "label": "Create Payments",
        "description": "Process payments",
        "category": "payments",
    },
    {
        "name": "payments.refund",
        "label": "Refund Payments",
        "description": "Process refunds",
        "category": "payments",
    },
    # Shipping Scopes
    {
        "name": "shipping.read",
        "label": "Read Shipping",
        "description": "View shipping information",
        "category": "shipping",
    },
    {
        "name": "shipping.create",
        "label": "Create Shipping",
        "description": "Create shipments",
        "category": "shipping",
    },
    {
        "name": "shipping.update",
        "label": "Update Shipping",
        "description": "Update shipment status",
        "category": "shipping",
    },
    {
        "name": "shipping.track",
        "label": "Track Shipping",
        "description": "Track shipments",
        "category": "shipping",
    },
]


def seed_organization_boutique_scopes(db: Session, organization_id: int) -> dict:
    """
    Seed boutique platform API scopes for a specific organization.

    This creates all boutique API scopes and assigns them to roles based on
    the ROLE_API_SCOPES_CONFIG mapping.

    Args:
        db: Database session
        organization_id: The ID of the organization to seed scopes for

    Returns:
        Dictionary with 'scopes_created' and 'mappings_created' counts
    """
    from backend.models.api_key import ApiScope

    result = {"scopes_created": 0, "mappings_created": 0}
    scope_map = {}

    # Create API scopes
    for scope_data in BOUTIQUE_SCOPES:
        existing = (
            db.query(ApiScope)
            .filter(
                ApiScope.organization_id == organization_id,
                ApiScope.name == scope_data["name"],
                ApiScope.platform == "boutique",
            )
            .first()
        )

        if not existing:
            scope = ApiScope(
                organization_id=organization_id,
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
            result["scopes_created"] += 1
        else:
            scope_map[scope_data["name"]] = existing

    # Assign scopes to roles
    roles = db.query(Role).filter(Role.organization_id == organization_id).all()

    for role in roles:
        if role.name not in ROLE_API_SCOPES_CONFIG:
            continue

        expected_scope_names = ROLE_API_SCOPES_CONFIG[role.name]
        current_scope_names = (
            {s.name for s in role.api_scopes} if hasattr(role, "api_scopes") else set()
        )

        for scope_name in expected_scope_names:
            if scope_name in scope_map and scope_name not in current_scope_names:
                role.api_scopes.append(scope_map[scope_name])
                result["mappings_created"] += 1

    db.flush()

    if result["scopes_created"] > 0:
        print(
            f"✅ Seeded {result['scopes_created']} boutique API scopes for organization {organization_id}"
        )
    if result["mappings_created"] > 0:
        print(
            f"✅ Created {result['mappings_created']} role-scope mappings for organization {organization_id}"
        )

    return result


# Define scopes for the boutique platform API key
# These are the scopes needed for anonymous/public access and logged-in customers
BOUTIQUE_API_KEY_SCOPES = [
    # Products - public catalog browsing
    "products.read",
    # Inventory - check stock availability
    "inventory.read",
    # Orders - placing orders
    "orders.create",
    "orders.read",
    # Customers - registration and profile
    "customers.create",
    "customers.read",
    "customers.update",
    # Wishlist - customer wishlist management
    "wishlist.read",
    "wishlist.create",
    "wishlist.delete",
    # Addresses - customer address management
    "addresses.read",
    "addresses.create",
    "addresses.update",
    "addresses.delete",
    # Payments - processing payments
    "payments.create",
    "payments.read",
    # Shipping - tracking shipments
    "shipping.read",
    "shipping.track",
]


def create_organization_boutique_api_key(
    db: Session, organization_id, created_by_id=None, key_name: str = "Boutique Platform API Key"
) -> dict:
    """
    Create a boutique platform API key for a new organization.

    This API key is used by the boutique frontend to access the platform services
    for both anonymous browsing and authenticated customer operations.

    Args:
        db: Database session
        organization_id: The ID of the organization
        created_by_id: The ID of the user creating the key (optional, for system keys)
        key_name: Name for the API key (default: "Boutique Platform API Key")

    Returns:
        Dictionary with 'api_key' (the full key - only shown once) and 'key_id'
    """
    from backend.core.security import generate_api_key, hash_api_key
    from backend.models.api_key import APIKey

    # Check if a boutique API key already exists for this organization
    existing_key = (
        db.query(APIKey)
        .filter(
            APIKey.organization_id == organization_id,
            APIKey.name == key_name,
            APIKey.is_active == True,
        )
        .first()
    )

    if existing_key:
        print(f"ℹ️  Boutique API key already exists for organization {organization_id}")
        return {
            "api_key": None,  # Can't retrieve the original key
            "key_id": existing_key.id,
            "key_prefix": existing_key.key_prefix,
            "already_existed": True,
        }

    # Generate new API key
    full_key = generate_api_key()
    key_prefix = full_key[:8]
    key_hash = hash_api_key(full_key)

    # Create the API key with boutique scopes
    api_key = APIKey(
        name=key_name,
        description="Auto-generated API key for boutique platform access. Grants permissions for public catalog browsing, customer operations, and order management.",
        key_hash=key_hash,
        key_prefix=key_prefix,
        permissions=",".join(BOUTIQUE_API_KEY_SCOPES),
        organization_id=organization_id,
        created_by_id=created_by_id,
        is_active=True,
        expires_at=None,  # Never expires by default
    )

    db.add(api_key)
    db.flush()

    print(f"✅ Created boutique platform API key for organization {organization_id}")
    print(f"   Key prefix: {key_prefix}...")
    print(f"   Scopes: {len(BOUTIQUE_API_KEY_SCOPES)} permissions granted")

    return {
        "api_key": full_key,  # Only returned on creation!
        "key_id": api_key.id,
        "key_prefix": key_prefix,
        "already_existed": False,
    }


def assign_default_role_permissions(db: Session) -> None:
    """
    Ensure all organizations have default roles with appropriate permissions assigned.

    Roles: owner, admin, editor, manager, inventory_manager, sales, employee, viewer

    This creates missing roles and assigns/updates permissions for existing roles.

    Permission Strategy:
    - Owner: Full system access including all permissions
    - Admin: All permissions except system.* (billing handled separately)
    - Editor: Content, media, translation, SEO permissions (no user/role management)
    - Manager: Operations, employee, inventory management
    - Inventory Manager: Products, categories, stock management
    - Sales: Orders, customers (read and process)
    - Employee: Basic view access
    - Viewer: Read-only permissions across all categories
    """
    # Get all organizations
    from backend.models.organization import Organization

    organizations = db.query(Organization).all()

    roles_created = 0
    roles_updated = 0

    for org in organizations:
        for role_name, config in DEFAULT_ROLE_CONFIGS.items():
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
                try:
                    # Use direct SQL to avoid StaleDataError in multi-worker environments
                    from sqlalchemy import text

                    db.execute(
                        text("DELETE FROM role_permissions WHERE role_id = :role_id"),
                        {"role_id": role.id},
                    )
                    # Expire the role to refresh its permissions collection
                    db.expire(role)
                    for perm in permissions:
                        role.permissions.append(perm)
                    roles_updated += 1
                except Exception as e:
                    # If another worker already updated, skip this role
                    print(
                        f"ℹ️  Skipping role {role_name} update (likely handled by another worker): {e}"
                    )
                    db.rollback()
                    continue

    if roles_created > 0 or roles_updated > 0:
        db.commit()
        if roles_created > 0:
            print(f"✅ Created {roles_created} default roles")
        if roles_updated > 0:
            print(f"✅ Updated permissions for {roles_updated} roles")
    else:
        print("ℹ️  All roles already configured correctly")


# Define which API scopes each boutique role should have
# This maps role names to their boutique platform API scopes
ROLE_API_SCOPES_CONFIG = {
    "owner": [
        # Full access to everything
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
        "wishlist.read",
        "wishlist.create",
        "wishlist.delete",
        "addresses.read",
        "addresses.create",
        "addresses.update",
        "addresses.delete",
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
        # Full access (same as owner for boutique operations)
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
        "wishlist.read",
        "wishlist.create",
        "wishlist.delete",
        "addresses.read",
        "addresses.create",
        "addresses.update",
        "addresses.delete",
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
        # Operations management - can do most things except admin
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
        "wishlist.read",
        "wishlist.create",
        "wishlist.delete",
        "addresses.read",
        "addresses.create",
        "addresses.update",
        "addresses.delete",
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
        # Inventory and product management
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
        "orders.read",  # Read orders to see what's needed
    ],
    "sales": [
        # Sales operations - orders, customers, payments
        "orders.read",
        "orders.create",
        "orders.update",
        "customers.read",
        "customers.create",
        "customers.update",
        "wishlist.read",
        "addresses.read",
        "addresses.create",
        "addresses.update",
        "products.read",  # Read products to help customers
        "inventory.read",  # Check stock availability
        "payments.read",
        "payments.create",
        "shipping.read",
        "shipping.track",
    ],
    "employee": [
        # Basic read access
        "inventory.read",
        "products.read",
        "orders.read",
        "customers.read",
        "wishlist.read",
        "addresses.read",
    ],
    "viewer": [
        # Read-only access
        "inventory.read",
        "products.read",
        "orders.read",
        "customers.read",
        "wishlist.read",
        "addresses.read",
        "payments.read",
        "shipping.read",
    ],
    "editor": [
        # Content-focused role - limited boutique access
        "products.read",
        "inventory.read",
    ],
}


def assign_role_api_scopes(db: Session) -> None:
    """
    Assign boutique platform API scopes to roles.

    This creates the role -> api_scope mappings that allow users
    with certain roles to have corresponding boutique permissions.
    """
    from sqlalchemy import text

    from backend.models.api_scope import ApiScope
    from backend.models.organization import Organization

    organizations = db.query(Organization).all()

    scopes_assigned = 0

    for org in organizations:
        # Get all API scopes for this organization
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
            print(f"ℹ️  No boutique API scopes found for organization {org.name}")
            continue

        scope_by_name = {s.name: s for s in scopes}

        # Get all roles for this organization
        roles = db.query(Role).filter(Role.organization_id == org.id).all()

        for role in roles:
            if role.name not in ROLE_API_SCOPES_CONFIG:
                continue

            expected_scope_names = set(ROLE_API_SCOPES_CONFIG[role.name])
            current_scope_names = (
                {s.name for s in role.api_scopes} if hasattr(role, "api_scopes") else set()
            )

            # Only update if different
            if current_scope_names != expected_scope_names:
                try:
                    # Clear existing api_scopes for this role
                    db.execute(
                        text("DELETE FROM role_api_scopes WHERE role_id = :role_id"),
                        {"role_id": role.id},
                    )
                    db.expire(role)

                    # Add the expected scopes
                    for scope_name in expected_scope_names:
                        if scope_name in scope_by_name:
                            role.api_scopes.append(scope_by_name[scope_name])
                            scopes_assigned += 1
                except Exception as e:
                    print(f"⚠️  Error updating API scopes for role {role.name}: {e}")
                    db.rollback()
                    continue

    if scopes_assigned > 0:
        db.commit()
        print(f"✅ Assigned {scopes_assigned} API scopes to roles")
    else:
        print("ℹ️  All role API scopes already configured correctly")


def init_permissions():
    """
    Initialize permissions on application startup.

    This function is called from the FastAPI lifespan event.
    """
    db = SessionLocal()
    try:
        seed_default_permissions(db)
        assign_default_role_permissions(db)
        assign_role_api_scopes(db)  # Also assign boutique API scopes to roles
    finally:
        db.close()
