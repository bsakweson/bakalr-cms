"""
Media/Asset Management Schemas
"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from enum import Enum


class MediaType(str, Enum):
    """Media type categories"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"


class MediaUploadResponse(BaseModel):
    """Response after successful upload"""
    id: int
    filename: str
    original_filename: str
    url: str
    mime_type: str
    file_size: int
    media_type: MediaType
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MediaUpdateRequest(BaseModel):
    """Request to update media metadata"""
    alt_text: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = None


class MediaResponse(BaseModel):
    """Full media response"""
    id: int
    organization_id: int
    uploaded_by_id: Optional[int]
    filename: str
    original_filename: str
    file_path: str
    url: str
    mime_type: str
    file_size: int
    file_extension: Optional[str]
    media_type: MediaType
    width: Optional[int]
    height: Optional[int]
    alt_text: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]
    cdn_url: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MediaListResponse(BaseModel):
    """Paginated media list"""
    items: List[MediaResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MediaFilterParams(BaseModel):
    """Media filtering parameters"""
    media_type: Optional[MediaType] = None
    mime_type: Optional[str] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    uploaded_by_id: Optional[int] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class MediaStats(BaseModel):
    """Media storage statistics"""
    total_files: int
    total_size: int
    by_type: dict  # {media_type: count}
    by_mime_type: dict  # {mime_type: count}
    storage_limit: Optional[int] = None
    storage_used_percent: Optional[float] = None


class ThumbnailRequest(BaseModel):
    """Request to generate thumbnail"""
    media_id: int
    width: Optional[int] = Field(None, ge=50, le=2000)
    height: Optional[int] = Field(None, ge=50, le=2000)
    quality: int = Field(85, ge=1, le=100)


class ThumbnailResponse(BaseModel):
    """Thumbnail generation response"""
    media_id: int
    thumbnail_url: str
    width: int
    height: int


class BulkDeleteRequest(BaseModel):
    """Request to delete multiple media files"""
    media_ids: List[int] = Field(..., min_length=1)


class BulkDeleteResponse(BaseModel):
    """Response from bulk delete"""
    deleted_count: int
    failed_ids: List[int] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
