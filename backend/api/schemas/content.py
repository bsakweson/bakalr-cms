"""
Pydantic schemas for content management
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ContentType Schemas

class ContentTypeFieldSchema(BaseModel):
    """Schema for a single field in a content type"""
    name: str
    type: str  # text, textarea, number, boolean, date, datetime, json, reference, media
    required: bool = False
    unique: bool = False
    localized: bool = False
    default: Optional[Any] = None
    validation: Optional[Dict[str, Any]] = None
    help_text: Optional[str] = None


class ContentTypeCreate(BaseModel):
    """Schema for creating a content type"""
    name: str = Field(..., min_length=1, max_length=100)
    api_id: str = Field(..., min_length=1, max_length=100, pattern="^[a-z][a-z0-9_]*$")
    description: Optional[str] = None
    fields: List[ContentTypeFieldSchema] = []
    display_field: Optional[str] = None


class ContentTypeUpdate(BaseModel):
    """Schema for updating a content type"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    fields: Optional[List[ContentTypeFieldSchema]] = None
    display_field: Optional[str] = None
    is_active: Optional[bool] = None


class ContentTypeResponse(BaseModel):
    """Schema for content type response"""
    id: int
    organization_id: int
    name: str
    api_id: str
    description: Optional[str]
    fields: List[Dict[str, Any]]
    display_field: Optional[str]
    is_active: bool
    entry_count: int = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ContentEntry Schemas

class ContentEntryCreate(BaseModel):
    """Schema for creating a content entry"""
    content_type_id: int
    data: Dict[str, Any]
    slug: Optional[str] = None
    status: str = "draft"  # draft, published, archived
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    og_image: Optional[str] = None


class ContentEntryUpdate(BaseModel):
    """Schema for updating a content entry"""
    data: Optional[Dict[str, Any]] = None
    slug: Optional[str] = None
    status: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    og_image: Optional[str] = None


class ContentEntryPublish(BaseModel):
    """Schema for publishing a content entry"""
    publish_at: Optional[datetime] = None


class ContentEntryResponse(BaseModel):
    """Schema for content entry response"""
    id: int
    content_type_id: int
    author_id: int
    data: Dict[str, Any]
    slug: Optional[str]
    status: str
    version: int
    published_at: Optional[datetime]
    seo_title: Optional[str]
    seo_description: Optional[str]
    seo_keywords: Optional[str]
    og_image: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ContentEntryListResponse(BaseModel):
    """Schema for paginated content entry list"""
    items: List[ContentEntryResponse]
    total: int
    page: int
    page_size: int
    pages: int
