"""
API Scope model for dynamic API key permissions.

This allows organizations to define custom permission scopes that can be
assigned to API keys. These scopes are used by external platforms (like
Boutique) to protect their endpoints.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class ApiScope(Base, IDMixin, TimestampMixin):
    """
    API Scope for dynamic permission management.

    Scopes are organization-specific and can be created/managed through the UI.
    They are assigned to API keys and used by external platforms to authorize access.

    Example scopes:
    - inventory.read: View inventory items
    - orders.create: Create new orders
    - admin.full: Full administrative access
    """

    __tablename__ = "api_scopes"

    # Scope identifier (e.g., "inventory.read", "orders.create")
    # Format: {resource}.{action} is recommended but not enforced
    name = Column(String(100), nullable=False, index=True)

    # Human-readable label for UI display
    label = Column(String(200), nullable=False)

    # Detailed description of what this scope grants
    description = Column(Text, nullable=True)

    # Category for grouping in UI (e.g., "Inventory", "Orders", "Customers")
    category = Column(String(50), nullable=True, index=True)

    # Platform this scope belongs to (e.g., "boutique", "cms", "custom")
    # Allows filtering scopes by platform
    platform = Column(String(50), nullable=True, index=True, default="custom")

    # Whether this scope is active and can be assigned to new API keys
    is_active = Column(Boolean, default=True, nullable=False)

    # Whether this is a system scope (cannot be deleted by users)
    is_system = Column(Boolean, default=False, nullable=False)

    # Organization that owns this scope (NULL = global/system scope)
    organization_id = Column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Relationships
    organization = relationship("Organization", backref="api_scopes")

    def __repr__(self):
        return f"<ApiScope(id={self.id}, name='{self.name}', platform='{self.platform}')>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "platform": self.platform,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
