"""
User Session model for tracking active login sessions
Migrated from boutique-platform keycloak-bff
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class UserSession(Base, IDMixin, TimestampMixin):
    """
    User Session model for tracking active login sessions.

    Each session represents an authenticated login from a specific device.
    Sessions can be individually revoked or bulk-revoked for security.
    """

    __tablename__ = "user_sessions"

    # User association
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Organization for multi-tenancy
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Device association (optional - web sessions may not have device)
    device_id = Column(
        GUID(), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Token info
    refresh_token_hash = Column(String(255), nullable=True, index=True)  # Hashed for lookup
    access_token_jti = Column(String(255), nullable=True, unique=True)  # JWT ID for revocation

    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)  # Full user agent string

    # Parsed user agent info
    browser = Column(String(100), nullable=True)
    browser_version = Column(String(50), nullable=True)
    os = Column(String(100), nullable=True)
    os_version = Column(String(50), nullable=True)
    device_type = Column(String(50), nullable=True)  # mobile, tablet, desktop

    # Location (from IP geolocation)
    country = Column(String(100), nullable=True)
    country_code = Column(String(10), nullable=True)
    city = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    latitude = Column(String(20), nullable=True)
    longitude = Column(String(20), nullable=True)

    # Session lifecycle
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Session status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    termination_reason = Column(String(255), nullable=True)  # logout, revoked, expired, security

    # Security flags
    is_suspicious = Column(Boolean, default=False, nullable=False)
    suspicious_reason = Column(String(255), nullable=True)
    requires_verification = Column(Boolean, default=False, nullable=False)

    # Login context
    login_method = Column(String(50), nullable=True)  # password, 2fa, api_key, refresh
    mfa_verified = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", backref="sessions")
    organization = relationship("Organization", backref="sessions")
    device = relationship("Device", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

    @property
    def location_display(self) -> str:
        """Get a display-friendly location string"""
        parts = []
        if self.city:
            parts.append(self.city)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts) if parts else "Unknown location"

    @property
    def device_display(self) -> str:
        """Get a display-friendly device string"""
        parts = []
        if self.browser:
            browser_str = self.browser
            if self.browser_version:
                browser_str += f" {self.browser_version}"
            parts.append(browser_str)
        if self.os:
            os_str = self.os
            if self.os_version:
                os_str += f" {self.os_version}"
            parts.append(os_str)
        return " on ".join(parts) if parts else "Unknown device"

    def terminate(self, reason: str = "logout"):
        """Terminate this session"""
        from datetime import datetime, timezone

        self.is_active = False
        self.terminated_at = datetime.now(timezone.utc)
        self.termination_reason = reason


class RefreshTokenRecord(Base, IDMixin, TimestampMixin):
    """
    Refresh Token tracking for token rotation and revocation.

    Stores hashed tokens for validation without exposing the actual token.
    Supports token families for rotation chain tracking.
    """

    __tablename__ = "refresh_tokens"

    # User association
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Session association
    session_id = Column(
        GUID(), ForeignKey("user_sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Device association
    device_id = Column(
        GUID(), ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Token data
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    token_family = Column(String(255), nullable=True, index=True)  # For rotation chain

    # Lifecycle
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Revocation
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(255), nullable=True)  # logout, rotation, security, admin

    # Usage tracking
    used_at = Column(DateTime(timezone=True), nullable=True)
    use_count = Column(String(10), default="0", nullable=False)  # Number of times used

    # Relationships
    user = relationship("User", backref="refresh_tokens")
    session = relationship("UserSession", backref="refresh_tokens")

    def __repr__(self):
        return (
            f"<RefreshTokenRecord(id={self.id}, user_id={self.user_id}, revoked={self.is_revoked})>"
        )

    def revoke(self, reason: str = "logout"):
        """Revoke this token"""
        from datetime import datetime, timezone

        self.is_revoked = True
        self.revoked_at = datetime.now(timezone.utc)
        self.revoked_reason = reason
