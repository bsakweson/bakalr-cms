"""
User model with organization/tenant association
"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin

# Association table for User-Role many-to-many relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", GUID(), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base, IDMixin, TimestampMixin):
    """
    User model with multi-tenancy support
    Users belong to an organization and can have multiple roles
    """

    __tablename__ = "users"

    # Organization (Tenant) - each user belongs to one organization
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Basic Info
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)

    # Profile
    avatar_url = Column(String(500), nullable=True)
    bio = Column(String(500), nullable=True)

    # Preferences (stored as JSON string)
    preferences = Column(String, nullable=True)  # JSON: theme, language, notifications, etc.

    # Security
    last_login = Column(String, nullable=True)  # ISO datetime string
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(String, nullable=True)  # ISO datetime string

    # Email Verification
    email_verification_token = Column(String(255), nullable=True)
    email_verification_expires = Column(String, nullable=True)  # ISO datetime string

    # 2FA
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)
    two_factor_backup_codes = Column(String, nullable=True)  # JSON string of hashed backup codes

    # External Identity Provider (Keycloak, etc.)
    external_id = Column(
        String(255), unique=True, nullable=True, index=True
    )  # External IdP user ID (e.g., Keycloak sub claim)
    external_provider = Column(
        String(50), nullable=True
    )  # Provider name: 'keycloak', 'auth0', etc.

    # Relationships
    organization = relationship(
        "Organization", foreign_keys=[organization_id], back_populates="users"
    )  # Primary/legacy organization
    user_organizations = relationship(
        "UserOrganization",
        foreign_keys="UserOrganization.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', org_id={self.organization_id})>"
