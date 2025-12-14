"""
Pydantic schemas for Session API
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============ Response Schemas ============


class SessionResponse(BaseModel):
    """Active session response"""

    id: UUID
    device_id: Optional[UUID]
    ip_address: Optional[str]
    browser: Optional[str]
    browser_version: Optional[str]
    os: Optional[str]
    os_version: Optional[str]
    device_type: Optional[str]
    country: Optional[str]
    city: Optional[str]
    is_active: bool
    is_current: bool = False  # True if this is the requesting session
    login_method: Optional[str]
    mfa_verified: bool
    is_suspicious: bool
    created_at: datetime
    last_active_at: datetime
    expires_at: datetime

    # Computed properties
    location_display: str
    device_display: str

    model_config = ConfigDict(from_attributes=True)


class SessionListResponse(BaseModel):
    """List of active sessions"""

    sessions: list[SessionResponse]
    total: int
    current_session_id: Optional[UUID] = None


class SessionRevokeResponse(BaseModel):
    """Response after revoking session(s)"""

    success: bool
    message: str
    revoked_count: int


class SessionRevokeRequest(BaseModel):
    """Request to revoke sessions"""

    session_ids: Optional[list[UUID]] = Field(None, description="Specific session IDs to revoke")
    revoke_all_except_current: bool = Field(False, description="Revoke all sessions except current")
    reason: Optional[str] = Field(None, max_length=255)


# ============ Security Activity Schemas ============


class LoginActivityResponse(BaseModel):
    """Login activity record"""

    id: UUID
    ip_address: Optional[str]
    location_display: str
    device_display: str
    login_method: Optional[str]
    mfa_verified: bool
    is_suspicious: bool
    suspicious_reason: Optional[str]
    created_at: datetime
    terminated_at: Optional[datetime]
    termination_reason: Optional[str]
    session_duration_minutes: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class LoginActivityListResponse(BaseModel):
    """List of login activities"""

    activities: list[LoginActivityResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class SecurityOverviewResponse(BaseModel):
    """Security overview for user account"""

    total_devices: int
    verified_devices: int
    trusted_devices: int
    active_sessions: int
    suspicious_sessions: int
    recent_logins_count: int  # Last 30 days
    two_factor_enabled: bool
    last_password_change: Optional[datetime]
    account_created_at: datetime
