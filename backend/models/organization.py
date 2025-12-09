"""
Organization/Tenant model for multi-tenancy
"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class Organization(Base, IDMixin, TimestampMixin):
    """
    Organization (Tenant) model for multi-tenancy isolation
    Each organization has its own isolated data space
    """

    __tablename__ = "organizations"

    # Basic Info
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Ownership - Track the organization owner/creator
    owner_id = Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True)

    # Contact & Settings
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    logo_url = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Subscription/Tier (for future use)
    plan_type = Column(String(50), default="free", nullable=False)  # free, basic, pro, enterprise

    # External Identity Provider Integration
    external_id = Column(
        String(255), unique=True, nullable=True, index=True
    )  # External tenant ID (e.g., Keycloak tenant/shop ID)
    external_provider = Column(
        String(50), nullable=True
    )  # Provider name: 'keycloak', 'boutique-platform', etc.

    # Settings (stored as JSON)
    settings = Column(Text, nullable=True)  # JSON string

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], post_update=True)  # Organization owner
    users = relationship(
        "User",
        foreign_keys="User.organization_id",
        back_populates="organization",
        cascade="all, delete-orphan",
    )  # Primary/legacy users
    user_organizations = relationship(
        "UserOrganization", back_populates="organization", cascade="all, delete-orphan"
    )
    roles = relationship("Role", back_populates="organization", cascade="all, delete-orphan")
    content_types = relationship(
        "ContentType", back_populates="organization", cascade="all, delete-orphan"
    )
    locales = relationship("Locale", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="organization", cascade="all, delete-orphan")
    webhooks = relationship("Webhook", back_populates="organization", cascade="all, delete-orphan")
    themes = relationship("Theme", back_populates="organization", cascade="all, delete-orphan")
    content_templates = relationship(
        "ContentTemplate", back_populates="organization", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}')>"
