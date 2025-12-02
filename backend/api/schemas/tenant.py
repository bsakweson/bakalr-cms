"""
Tenant/Organization switching schemas
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from backend.api.schemas.base import UUIDMixin


class OrganizationMembership(UUIDMixin):
    """User's organization membership details"""

    organization_id: str
    organization_name: str
    organization_slug: str
    is_default: bool
    is_active: bool
    roles: List[str]
    joined_at: str

    model_config = ConfigDict(from_attributes=True)


class UserOrganizationsResponse(UUIDMixin):
    """List of organizations user belongs to"""

    current_organization_id: str
    organizations: List[OrganizationMembership]
    total: int


class SwitchOrganizationRequest(BaseModel):
    """Request to switch to a different organization"""

    organization_id: str


class SwitchOrganizationResponse(UUIDMixin):
    """Response after switching organizations"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    organization_id: str
    organization_name: str
    roles: List[str]
    message: str


class InviteUserToOrganizationRequest(BaseModel):
    """Invite user to join organization"""

    email: str
    role_names: Optional[List[str]] = None  # Roles to assign in this org


class InviteUserToOrganizationResponse(UUIDMixin):
    """Response after inviting user"""

    user_id: str
    email: str
    organization_id: str
    organization_name: str
    invitation_sent: bool
    message: str


class SetDefaultOrganizationRequest(BaseModel):
    """Set default organization for user"""

    organization_id: str


class SetDefaultOrganizationResponse(UUIDMixin):
    """Response after setting default organization"""

    organization_id: str
    organization_name: str
    is_default: bool
    message: str
