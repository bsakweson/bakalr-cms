"""
API Key model for headless access
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class APIKey(Base, IDMixin, TimestampMixin):
    """
    API Key model for programmatic access to the CMS
    """

    __tablename__ = "api_keys"

    # Organization (Tenant)
    organization_id = Column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Created by
    created_by_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # API Key Info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # The actual key (hashed)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Key prefix (for identification in logs) - stored in plain text
    key_prefix = Column(String(20), nullable=False)

    # Permissions (stored as JSON array of permission names)
    permissions = Column(Text, nullable=True)  # JSON array

    # Scopes/Restrictions
    allowed_ips = Column(Text, nullable=True)  # JSON array of IP addresses
    rate_limit = Column(Integer, nullable=True)  # Requests per minute

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Expiration
    expires_at = Column(String, nullable=True)  # ISO datetime string

    # Usage tracking
    last_used_at = Column(String, nullable=True)  # ISO datetime string
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}')>"
