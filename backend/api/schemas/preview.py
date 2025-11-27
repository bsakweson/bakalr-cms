"""
Pydantic schemas for content preview system.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PreviewTokenRequest(BaseModel):
    """Request schema for generating preview token."""
    
    content_entry_id: int = Field(..., description="ID of the content entry to preview")
    expires_in_hours: int = Field(
        default=24,
        ge=1,
        le=168,  # Max 7 days
        description="Number of hours until token expires (1-168)"
    )


class PreviewTokenResponse(BaseModel):
    """Response schema with generated preview token and URL."""
    
    preview_url: str = Field(..., description="Full preview URL with signed token")
    token: str = Field(..., description="Signed preview token")
    expires_at: datetime = Field(..., description="Token expiration timestamp")
    content_entry_id: int = Field(..., description="ID of the content entry")
    
    model_config = ConfigDict(from_attributes=True)


class PreviewAccessRequest(BaseModel):
    """Request to access content via preview token."""
    
    token: str = Field(..., description="Signed preview token")


class PreviewContentResponse(BaseModel):
    """Content response for preview mode (includes draft content)."""
    
    id: int
    content_type_id: int
    organization_id: int
    title: str
    slug: str
    status: str  # Can be 'draft' or 'published'
    fields: dict
    version: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_preview: bool = Field(default=True, description="Indicates this is preview mode")
    
    model_config = ConfigDict(from_attributes=True)
