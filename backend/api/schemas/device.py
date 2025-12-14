"""
Pydantic schemas for Device API
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.models.device import DevicePlatform, DeviceStatus

# ============ Request Schemas ============


class DeviceRegisterRequest(BaseModel):
    """Request to register a new device"""

    device_id: str = Field(
        ..., min_length=1, max_length=255, description="Unique device identifier"
    )
    name: Optional[str] = Field(None, max_length=255, description="User-friendly device name")
    device_type: Optional[str] = Field(
        None, max_length=50, description="Device type: phone, tablet, desktop, browser"
    )
    platform: DevicePlatform = Field(DevicePlatform.OTHER, description="Device platform")
    os: Optional[str] = Field(None, max_length=100, description="Operating system")
    os_version: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=100, description="Device model")
    browser: Optional[str] = Field(None, max_length=100, description="Browser name (for web)")
    browser_version: Optional[str] = Field(None, max_length=50)
    app_version: Optional[str] = Field(None, max_length=50, description="App version")
    fcm_token: Optional[str] = Field(
        None, max_length=512, description="Firebase Cloud Messaging token"
    )
    apns_token: Optional[str] = Field(
        None, max_length=512, description="Apple Push Notification token"
    )
    browser_fingerprint: Optional[str] = Field(None, max_length=255)
    hardware_fingerprint: Optional[str] = Field(None, max_length=255)
    screen_resolution: Optional[str] = Field(None, max_length=50)
    timezone: Optional[str] = Field(None, max_length=100)
    capabilities: Optional[str] = Field(None, description="JSON string of device capabilities")


class DeviceUpdateRequest(BaseModel):
    """Request to update device info"""

    name: Optional[str] = Field(None, max_length=255)
    fcm_token: Optional[str] = Field(None, max_length=512)
    apns_token: Optional[str] = Field(None, max_length=512)
    push_enabled: Optional[bool] = None
    app_version: Optional[str] = Field(None, max_length=50)
    os: Optional[str] = Field(None, max_length=100)
    os_version: Optional[str] = Field(None, max_length=50)


class DevicePushTokenRequest(BaseModel):
    """Request to update push token"""

    fcm_token: Optional[str] = Field(None, max_length=512)
    apns_token: Optional[str] = Field(None, max_length=512)
    push_enabled: bool = True


class DeviceVerifyRequest(BaseModel):
    """Request to verify a device with PIN code"""

    verification_code: str = Field(
        ..., min_length=6, max_length=6, description="6-digit verification PIN"
    )


class DeviceTrustRequest(BaseModel):
    """Request to mark device as trusted/untrusted"""

    is_trusted: bool


class DeviceSuspendRequest(BaseModel):
    """Request to suspend or block a device"""

    action: str = Field(..., pattern="^(suspend|block|activate)$")
    reason: Optional[str] = Field(None, max_length=255)


# ============ Response Schemas ============


class DeviceResponse(BaseModel):
    """Device response"""

    id: UUID
    device_id: str
    name: Optional[str]
    device_type: Optional[str]
    platform: DevicePlatform
    os: Optional[str]
    os_version: Optional[str]
    model: Optional[str]
    browser: Optional[str]
    browser_version: Optional[str]
    app_version: Optional[str]
    status: DeviceStatus
    verified: bool
    verified_at: Optional[datetime]
    is_trusted: bool
    push_enabled: bool
    last_used_at: datetime
    last_ip_address: Optional[str]
    last_location: Optional[str]
    created_at: datetime

    # Computed properties
    display_name: str
    is_mobile: bool
    can_receive_push: bool

    model_config = ConfigDict(from_attributes=True)


class DeviceListResponse(BaseModel):
    """List of devices response"""

    devices: list[DeviceResponse]
    total: int


class DeviceRegistrationResponse(BaseModel):
    """Response after device registration"""

    device: DeviceResponse
    verification_required: bool
    message: str


class DeviceVerificationResponse(BaseModel):
    """Response after device verification"""

    success: bool
    message: str
    device: Optional[DeviceResponse] = None


class DeviceVerificationCodeSentResponse(BaseModel):
    """Response when verification code is sent"""

    success: bool
    message: str
    expires_at: datetime


class MessageResponse(BaseModel):
    """Simple message response"""

    success: bool
    message: str
