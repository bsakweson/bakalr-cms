"""
Role and Permission models for comprehensive RBAC
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin

# Association table for Role-Permission many-to-many relationship
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", GUID, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id", GUID, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    ),
)


class Permission(Base, IDMixin, TimestampMixin):
    """
    Permission model for granular access control
    Permissions are system-wide and can be assigned to roles
    """

    __tablename__ = "permissions"

    # Permission identifier (e.g., "content.create", "users.delete", "roles.manage")
    name = Column(String(100), unique=True, nullable=False, index=True)

    # Human-readable description
    description = Column(String(500), nullable=True)

    # Category for grouping (e.g., "content", "users", "settings")
    category = Column(String(50), nullable=True, index=True)

    # Resource type (e.g., "content_type", "user", "role") - for field-level permissions
    resource_type = Column(String(50), nullable=True)

    # Content type-specific permission (NULL = applies to all content types)
    content_type_id = Column(
        GUID, ForeignKey("content_types.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Field-level permission (NULL = applies to entire resource)
    # Format: "field_name" for specific field, or NULL for all fields
    field_name = Column(String(100), nullable=True, index=True)

    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    content_type = relationship(
        "ContentType", backref="permissions", foreign_keys=[content_type_id]
    )

    def __repr__(self):
        return f"<Permission(id={self.id}, name='{self.name}')>"


class Role(Base, IDMixin, TimestampMixin):
    """
    Role model for RBAC with tenant-scoped custom roles
    Each organization can create custom roles with specific permissions
    """

    __tablename__ = "roles"

    # Organization (Tenant) - roles are scoped to organizations
    organization_id = Column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Role Info
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # System roles (super_admin, org_admin, editor, contributor, viewer)
    # or custom roles created by organizations
    is_system_role = Column(Boolean, default=False, nullable=False)

    # Role hierarchy level (higher = more permissions)
    level = Column(Integer, default=0, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    users = relationship("User", secondary="user_roles", back_populates="roles")

    def __repr__(self):
        return f"<Role(id={self.id}, name='{self.name}', org_id={self.organization_id})>"
