"""Models package initialization"""

# Import all models to ensure they're registered with SQLAlchemy
from backend.models.api_key import APIKey
from backend.models.audit_log import AuditLog
from backend.models.base import IDMixin, TimestampMixin
from backend.models.content import ContentEntry, ContentType
from backend.models.content_template import ContentTemplate
from backend.models.media import Media
from backend.models.notification import Notification
from backend.models.organization import Organization
from backend.models.rbac import Permission, Role
from backend.models.relationship import ContentRelationship
from backend.models.schedule import ContentSchedule
from backend.models.theme import Theme
from backend.models.translation import Locale, Translation, TranslationGlossary
from backend.models.user import User
from backend.models.user_organization import UserOrganization
from backend.models.webhook import (
    Webhook,
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEventType,
    WebhookStatus,
)

__all__ = [
    "IDMixin",
    "TimestampMixin",
    "Organization",
    "User",
    "UserOrganization",
    "Permission",
    "Role",
    "ContentType",
    "ContentEntry",
    "ContentRelationship",
    "Locale",
    "Translation",
    "TranslationGlossary",
    "Media",
    "APIKey",
    "AuditLog",
    "Webhook",
    "WebhookDelivery",
    "WebhookStatus",
    "WebhookEventType",
    "WebhookDeliveryStatus",
    "ContentSchedule",
    "Theme",
    "ContentTemplate",
    "Notification",
]
