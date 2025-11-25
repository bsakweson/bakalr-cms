"""
Pydantic schemas for API key management.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class APIKeyCreateSchema(BaseModel):
    """Schema for creating an API key."""
    name: str = Field(..., min_length=1, max_length=100, description="Name/description for the API key")
    scopes: list[str] = Field(default_factory=list, description="List of permission scopes (e.g., ['read:content', 'write:media'])")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration datetime (null = no expiration)")


class APIKeyUpdateSchema(BaseModel):
    """Schema for updating an API key."""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="New name for the API key")
    scopes: Optional[list[str]] = Field(None, description="New list of permission scopes")
    is_active: Optional[bool] = Field(None, description="Whether the key is active")


class APIKeyResponseSchema(BaseModel):
    """Schema for API key response (without secret)."""
    id: int
    name: str
    key_prefix: str = Field(..., description="First 8 characters of the key for identification")
    scopes: list[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    organization_id: int
    
    model_config = {"from_attributes": True}


class APIKeyWithSecretSchema(BaseModel):
    """Schema for API key response with full secret (only returned on creation)."""
    id: int
    name: str
    key: str = Field(..., description="Full API key (only shown once)")
    key_prefix: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    organization_id: int
    
    model_config = {"from_attributes": True}


class APIKeyListResponseSchema(BaseModel):
    """Schema for paginated list of API keys."""
    items: list[APIKeyResponseSchema]
    total: int
    page: int
    page_size: int
