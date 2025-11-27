"""
Notification API schemas for requests and responses.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from backend.models.notification import NotificationType, NotificationPriority, EmailStatus


# Notification Schemas

class NotificationCreate(BaseModel):
    """Schema for creating a notification"""
    user_id: Optional[int] = Field(None, description="Target user ID (defaults to current user if not provided)")
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    message: str = Field(..., min_length=1, description="Notification message")
    notification_type: Optional[NotificationType] = Field(None, description="Notification type")
    type: Optional[str] = Field(None, description="Notification type (alias for notification_type)")
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL, description="Priority level")
    action_url: Optional[str] = Field(None, max_length=500, description="Action URL")
    action_label: Optional[str] = Field(None, max_length=100, description="Action button label")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    expires_in_days: Optional[int] = Field(30, ge=1, le=365, description="Days until expiration")
    send_email: bool = Field(False, description="Also send email notification")


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    id: int
    user_id: int
    organization_id: int
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    is_read: bool
    read_at: Optional[datetime]
    action_url: Optional[str]
    action_label: Optional[str]
    meta_data: Optional[Dict[str, Any]]
    created_at: datetime
    expires_at: Optional[datetime]

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list"""
    items: List[NotificationResponse]
    total: int
    page: int
    per_page: int
    unread_count: int


class NotificationMarkRead(BaseModel):
    """Schema for marking notifications as read"""
    notification_ids: List[int] = Field(..., description="List of notification IDs to mark as read")


class NotificationStats(BaseModel):
    """Schema for notification statistics"""
    total_count: int
    unread_count: int
    by_type: Dict[str, int]
    by_priority: Dict[str, int]


# Notification Preference Schemas

class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences"""
    event_type: str = Field(..., description="Event type (e.g., 'content.created')")
    in_app_enabled: bool = Field(True, description="Enable in-app notifications")
    email_enabled: bool = Field(True, description="Enable email notifications")
    digest_enabled: bool = Field(False, description="Enable digest emails")
    digest_frequency: Optional[str] = Field(None, description="Digest frequency: daily, weekly, monthly")


class NotificationPreferenceResponse(BaseModel):
    """Schema for notification preference response"""
    id: int
    user_id: int
    organization_id: int
    event_type: str
    in_app_enabled: bool
    email_enabled: bool
    digest_enabled: bool
    digest_frequency: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Email Log Schemas

class EmailLogResponse(BaseModel):
    """Schema for email log response"""
    id: int
    user_id: Optional[int]
    organization_id: int
    to_email: str
    from_email: str
    subject: str
    template_name: Optional[str]
    status: EmailStatus
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    clicked_at: Optional[datetime]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EmailLogListResponse(BaseModel):
    """Schema for paginated email log list"""
    items: List[EmailLogResponse]
    total: int
    page: int
    per_page: int


class EmailStats(BaseModel):
    """Schema for email statistics"""
    total_sent: int
    total_failed: int
    total_pending: int
    open_rate: float
    click_rate: float
    by_template: Dict[str, int]
