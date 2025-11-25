"""
Pydantic schemas for field-level and content type-specific permissions.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class FieldPermissionCreate(BaseModel):
    """Schema for creating a field-level permission."""
    role_id: int = Field(..., description="Role ID to grant permission to")
    permission_name: str = Field(..., description="Permission name (e.g., 'content.read', 'content.write')")
    content_type_id: int = Field(..., description="Content type ID")
    field_name: str = Field(..., description="Field name to grant permission for")
    description: Optional[str] = Field(None, description="Optional description")


class FieldPermissionBulkCreate(BaseModel):
    """Schema for creating multiple field permissions at once."""
    role_id: int = Field(..., description="Role ID to grant permissions to")
    permission_name: str = Field(..., description="Permission name")
    content_type_id: int = Field(..., description="Content type ID")
    field_names: List[str] = Field(..., description="List of field names")


class ContentTypePermissionCreate(BaseModel):
    """Schema for creating content type-specific permission."""
    role_id: int = Field(..., description="Role ID to grant permission to")
    permission_name: str = Field(..., description="Permission name")
    content_type_id: int = Field(..., description="Content type ID")
    description: Optional[str] = Field(None, description="Optional description")


class PermissionResponse(BaseModel):
    """Schema for permission response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    resource_type: Optional[str] = None
    content_type_id: Optional[int] = None
    field_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class FieldPermissionResponse(BaseModel):
    """Response schema for field permission with details."""
    permission: PermissionResponse
    content_type_name: str
    field_name: str


class AccessibleFieldsResponse(BaseModel):
    """Response schema for accessible fields check."""
    content_type_id: int
    content_type_name: str
    permission_name: str
    accessible_fields: List[str]
    restricted_fields: List[str]


class PermissionCheckRequest(BaseModel):
    """Request schema for checking field permissions."""
    permission_name: str = Field(..., description="Permission to check")
    content_type_id: int = Field(..., description="Content type ID")
    field_names: List[str] = Field(..., description="Fields to check")


class PermissionCheckResponse(BaseModel):
    """Response schema for permission check."""
    has_permission: bool
    accessible_fields: List[str]
    denied_fields: List[str]
