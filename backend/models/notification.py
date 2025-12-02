"""
Notification models for in-app notifications and email tracking.
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


class NotificationType(str, enum.Enum):
    """Notification types"""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CONTENT = "content"
    MEDIA = "media"
    USER = "user"
    SYSTEM = "system"


class NotificationPriority(str, enum.Enum):
    """Notification priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """
    In-app notifications for users.
    Supports real-time updates, read status tracking, and action links.
    """

    __tablename__ = "notifications"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(
        SQLEnum(NotificationType), nullable=False, default=NotificationType.INFO, index=True
    )
    priority = Column(
        SQLEnum(NotificationPriority), nullable=False, default=NotificationPriority.NORMAL
    )

    # Status tracking
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Action details
    action_url = Column(String(500), nullable=True)  # Link to related resource
    action_label = Column(String(100), nullable=True)  # "View Content", "Approve", etc.

    # Metadata
    meta_data = Column(JSON, nullable=True)  # Additional context (content_id, media_id, etc.)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-delete old notifications

    # Relationships
    user = relationship("User", back_populates="notifications")
    organization = relationship("Organization")

    def __repr__(self):
        return f"<Notification {self.id}: {self.title} for user {self.user_id}>"


class EmailStatus(str, enum.Enum):
    """Email delivery status"""

    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"


class EmailLog(Base):
    """
    Email delivery tracking and history.
    Logs all sent emails with status, errors, and engagement metrics.
    """

    __tablename__ = "email_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Email details
    to_email = Column(String(255), nullable=False, index=True)
    from_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    template_name = Column(String(100), nullable=True, index=True)

    # Delivery tracking
    status = Column(SQLEnum(EmailStatus), nullable=False, default=EmailStatus.PENDING, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Metadata
    meta_data = Column(JSON, nullable=True)  # Template variables, campaign info, etc.
    external_id = Column(String(255), nullable=True, index=True)  # Email service provider ID

    # Timestamps
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")

    def __repr__(self):
        return f"<EmailLog {self.id}: {self.subject} to {self.to_email} ({self.status})>"


class NotificationPreference(Base):
    """
    User notification preferences for different event types.
    Controls which notifications are sent via email vs in-app.
    """

    __tablename__ = "notification_preferences"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Preference settings
    event_type = Column(
        String(100), nullable=False, index=True
    )  # "content.created", "media.uploaded", etc.
    in_app_enabled = Column(Boolean, default=True, nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)

    # Digest settings
    digest_enabled = Column(Boolean, default=False, nullable=False)
    digest_frequency = Column(String(50), nullable=True)  # "daily", "weekly", "monthly"

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")

    def __repr__(self):
        return f"<NotificationPreference {self.id}: {self.event_type} for user {self.user_id}>"
