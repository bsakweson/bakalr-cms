"""
Device model for tracking user devices (mobile apps, browsers)
Migrated from boutique-platform keycloak-bff
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class DeviceStatus(str, enum.Enum):
    """Device status values"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    UNVERIFIED = "unverified"


class DevicePlatform(str, enum.Enum):
    """Device platform types"""

    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    DESKTOP = "desktop"
    OTHER = "other"


class Device(Base, IDMixin, TimestampMixin):
    """
    Device model for tracking user devices.

    Supports:
    - Mobile apps (iOS, Android)
    - Web browsers
    - Desktop apps
    - Device verification for security
    - Push notification tokens (FCM, APNS)
    """

    __tablename__ = "devices"

    # User association (nullable to allow device registration before user account)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    # Organization for multi-tenancy
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Device identification
    device_id = Column(String(255), nullable=False, index=True)  # Unique device identifier
    name = Column(String(255), nullable=True)  # User-friendly name (e.g., "John's iPhone")
    device_type = Column(String(50), nullable=True)  # phone, tablet, desktop, browser

    # Platform info
    platform = Column(Enum(DevicePlatform), default=DevicePlatform.OTHER, nullable=False)
    os = Column(String(100), nullable=True)  # e.g., "iOS 17.1", "Android 14"
    os_version = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)  # e.g., "iPhone 15 Pro", "Pixel 8"
    browser = Column(String(100), nullable=True)  # For web: "Chrome 120", "Safari 17"
    browser_version = Column(String(50), nullable=True)

    # App info
    app_version = Column(String(50), nullable=True)  # App version if mobile/desktop app

    # Push notifications
    fcm_token = Column(String(512), nullable=True)  # Firebase Cloud Messaging token
    apns_token = Column(String(512), nullable=True)  # Apple Push Notification Service token
    push_enabled = Column(Boolean, default=False, nullable=False)

    # Fingerprinting (for fraud detection)
    browser_fingerprint = Column(String(255), nullable=True)
    hardware_fingerprint = Column(String(255), nullable=True)
    screen_resolution = Column(String(50), nullable=True)  # e.g., "1920x1080"
    timezone = Column(String(100), nullable=True)  # e.g., "Europe/Amsterdam"

    # Device capabilities (JSON)
    capabilities = Column(Text, nullable=True)  # JSON: biometrics, camera, etc.

    # Status and verification
    status = Column(Enum(DeviceStatus), default=DeviceStatus.UNVERIFIED, nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_code = Column(String(10), nullable=True)  # 6-digit PIN
    verification_code_expires = Column(DateTime(timezone=True), nullable=True)

    # Activity tracking
    last_used_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    last_location = Column(String(255), nullable=True)  # City, Country

    # Trust and security
    is_trusted = Column(Boolean, default=False, nullable=False)  # User marked as trusted
    trust_score = Column(String(10), nullable=True)  # Calculated trust score

    # Suspension/blocking
    inactive_reason = Column(String(255), nullable=True)
    blocked_reason = Column(String(255), nullable=True)
    blocked_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="devices")
    organization = relationship("Organization", backref="devices")
    sessions = relationship("UserSession", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device(id={self.id}, device_id='{self.device_id}', platform={self.platform})>"

    @property
    def display_name(self) -> str:
        """Get a display-friendly device name"""
        if self.name:
            return self.name
        parts = []
        if self.model:
            parts.append(self.model)
        elif self.device_type:
            parts.append(self.device_type.title())
        if self.os:
            parts.append(self.os)
        return " - ".join(parts) if parts else f"Device {self.device_id[:8]}"

    @property
    def is_mobile(self) -> bool:
        """Check if device is a mobile device"""
        return self.platform in (DevicePlatform.IOS, DevicePlatform.ANDROID)

    @property
    def is_active(self) -> bool:
        """Check if device is in active status"""
        return self.status == DeviceStatus.ACTIVE

    def can_receive_push(self) -> bool:
        """Check if device can receive push notifications"""
        return self.push_enabled and (self.fcm_token or self.apns_token)
