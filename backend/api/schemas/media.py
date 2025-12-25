"""
Media/Asset Management Schemas
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.api.schemas.base import UUIDMixin


class MediaType(str, Enum):
    """Media type categories"""

    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"


class MediaUploadResponse(UUIDMixin):
    """Response after successful upload"""

    id: str
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


class MediaResponse(UUIDMixin):
    """Full media response"""

    id: str
    organization_id: str
    uploaded_by_id: Optional[str]
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
    size: int
    pages: int


class MediaFilterParams(BaseModel):
    """Media filtering parameters"""

    media_type: Optional[MediaType] = None
    mime_type: Optional[str] = None
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    uploaded_by_id: Optional[str] = None
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

    media_id: str
    width: Optional[int] = Field(None, ge=50, le=2000)
    height: Optional[int] = Field(None, ge=50, le=2000)
    quality: int = Field(85, ge=1, le=100)


class ThumbnailResponse(BaseModel):
    """Thumbnail generation response"""

    media_id: str
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
