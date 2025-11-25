"""
Pydantic schemas for webhook API
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, field_validator

from backend.models.webhook import WebhookStatus, WebhookEventType, WebhookDeliveryStatus


# Webhook schemas
class WebhookCreate(BaseModel):
    """Create webhook request"""
    name: str = Field(..., min_length=1, max_length=255, description="Webhook name")
    description: Optional[str] = Field(None, description="Webhook description")
    url: HttpUrl = Field(..., description="Webhook endpoint URL")
    events: List[WebhookEventType] = Field(..., min_items=1, description="Event types to subscribe to")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers to include in requests")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay: int = Field(60, ge=1, description="Retry delay in seconds")
    
    @field_validator("events")
    @classmethod
    def validate_events(cls, v):
        """Validate event types"""
        if not v:
            raise ValueError("At least one event type must be specified")
        # Remove duplicates
        return list(set(v))


class WebhookUpdate(BaseModel):
    """Update webhook request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    url: Optional[HttpUrl] = None
    events: Optional[List[WebhookEventType]] = None
    headers: Optional[Dict[str, str]] = None
    status: Optional[WebhookStatus] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_delay: Optional[int] = Field(None, ge=1)
    
    @field_validator("events")
    @classmethod
    def validate_events(cls, v):
        """Validate event types"""
        if v is not None and len(v) == 0:
            raise ValueError("At least one event type must be specified")
        if v:
            # Remove duplicates
            return list(set(v))
        return v


class WebhookResponse(BaseModel):
    """Webhook response"""
    id: int
    organization_id: int
    name: str
    description: Optional[str]
    url: str
    events: List[str]
    status: WebhookStatus
    is_active: bool
    headers: Optional[Dict[str, str]]
    max_retries: int
    retry_delay: int
    success_count: int
    failure_count: int
    last_triggered_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class WebhookListResponse(BaseModel):
    """List of webhooks"""
    total: int
    webhooks: List[WebhookResponse]


class WebhookSecretResponse(BaseModel):
    """Webhook secret (only returned on creation)"""
    id: int
    secret: str
    message: str = "Store this secret securely. It will not be shown again."


# Webhook delivery schemas
class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery response"""
    id: int
    webhook_id: int
    event_type: str
    event_id: str
    status: WebhookDeliveryStatus
    attempt_count: int
    max_attempts: int
    response_status: Optional[int]
    response_body: Optional[str] = Field(None, max_length=1000)  # Truncate for response
    error_message: Optional[str]
    created_at: datetime
    first_attempted_at: Optional[datetime]
    last_attempted_at: Optional[datetime]
    completed_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class WebhookDeliveryListResponse(BaseModel):
    """List of webhook deliveries"""
    total: int
    deliveries: List[WebhookDeliveryResponse]


class WebhookDeliveryDetailResponse(BaseModel):
    """Detailed webhook delivery response with full payload"""
    id: int
    webhook_id: int
    event_type: str
    event_id: str
    payload: Dict[str, Any]
    status: WebhookDeliveryStatus
    attempt_count: int
    max_attempts: int
    response_status: Optional[int]
    response_body: Optional[str]
    response_headers: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    first_attempted_at: Optional[datetime]
    last_attempted_at: Optional[datetime]
    completed_at: Optional[datetime]
    next_retry_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Webhook test schemas
class WebhookTestRequest(BaseModel):
    """Test webhook request"""
    event_type: WebhookEventType = Field(WebhookEventType.CONTENT_CREATED, description="Event type to test")
    custom_payload: Optional[Dict[str, Any]] = Field(None, description="Custom payload for testing")


class WebhookTestResponse(BaseModel):
    """Test webhook response"""
    success: bool
    delivery_id: int
    status_code: Optional[int]
    response_body: Optional[str]
    error: Optional[str]
    message: str


# Webhook event schemas
class WebhookEventPayload(BaseModel):
    """Base webhook event payload"""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event type")
    timestamp: datetime = Field(..., description="Event timestamp")
    organization_id: int = Field(..., description="Organization ID")
    data: Dict[str, Any] = Field(..., description="Event data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_1234567890",
                "event_type": "content.created",
                "timestamp": "2025-11-24T12:00:00Z",
                "organization_id": 1,
                "data": {
                    "id": 42,
                    "type": "blog_post",
                    "title": "New Blog Post",
                    "status": "draft"
                }
            }
        }
