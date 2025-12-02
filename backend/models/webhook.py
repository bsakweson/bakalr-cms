"""
Webhook models for event-driven integrations
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID


class WebhookStatus(str, enum.Enum):
    """Webhook status"""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class WebhookEventType(str, enum.Enum):
    """Available webhook event types"""

    # Content events
    CONTENT_CREATED = "content.created"
    CONTENT_UPDATED = "content.updated"
    CONTENT_DELETED = "content.deleted"
    CONTENT_PUBLISHED = "content.published"
    CONTENT_UNPUBLISHED = "content.unpublished"

    # Media events
    MEDIA_UPLOADED = "media.uploaded"
    MEDIA_UPDATED = "media.updated"
    MEDIA_DELETED = "media.deleted"

    # Translation events
    TRANSLATION_CREATED = "translation.created"
    TRANSLATION_UPDATED = "translation.updated"

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"

    # Organization events
    ORGANIZATION_CREATED = "organization.created"
    ORGANIZATION_UPDATED = "organization.updated"


class WebhookDeliveryStatus(str, enum.Enum):
    """Webhook delivery status"""

    PENDING = "pending"
    DELIVERING = "delivering"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


class Webhook(Base):
    """Webhook configuration"""

    __tablename__ = "webhooks"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Webhook configuration
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(2048), nullable=False)
    secret = Column(String(255), nullable=False)  # For HMAC signature

    # Event subscriptions
    events = Column(JSON, nullable=False)  # List of subscribed event types

    # Status and configuration
    status = Column(SQLEnum(WebhookStatus), nullable=False, default=WebhookStatus.ACTIVE)
    is_active = Column(Boolean, default=True, nullable=False)

    # Retry configuration
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay = Column(Integer, default=60, nullable=False)  # seconds

    # Headers to include in webhook requests
    headers = Column(JSON, nullable=True)  # Custom headers as key-value pairs

    # Statistics
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)
    last_triggered_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="webhooks")
    deliveries = relationship(
        "WebhookDelivery", back_populates="webhook", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Webhook(id={self.id}, name='{self.name}', url='{self.url}')>"


class WebhookDelivery(Base):
    """Webhook delivery attempt log"""

    __tablename__ = "webhook_deliveries"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    webhook_id = Column(
        GUID(), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Event information
    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(String(255), nullable=False, index=True)  # UUID of the event

    # Payload
    payload = Column(JSON, nullable=False)

    # Delivery information
    status = Column(
        SQLEnum(WebhookDeliveryStatus),
        nullable=False,
        default=WebhookDeliveryStatus.PENDING,
        index=True,
    )
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    # Response information
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    response_headers = Column(JSON, nullable=True)

    # Error information
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    first_attempted_at = Column(DateTime, nullable=True)
    last_attempted_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    webhook = relationship("Webhook", back_populates="deliveries")

    def __repr__(self):
        return f"<WebhookDelivery(id={self.id}, webhook_id={self.webhook_id}, event_type='{self.event_type}', status='{self.status}')>"
