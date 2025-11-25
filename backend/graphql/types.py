"""
GraphQL types for core models.
"""
from typing import Optional, List
from datetime import datetime
import strawberry


@strawberry.type
class OrganizationType:
    """Organization/Tenant GraphQL type."""
    id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class UserType:
    """User GraphQL type."""
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    organization: Optional[OrganizationType]


@strawberry.type
class ContentTypeType:
    """Content Type (schema) GraphQL type."""
    id: int
    name: str
    slug: str
    description: Optional[str]
    fields: strawberry.scalars.JSON
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ContentEntryType:
    """Content Entry GraphQL type."""
    id: int
    slug: str
    status: str
    content_data: strawberry.scalars.JSON
    seo_metadata: Optional[strawberry.scalars.JSON]
    version: int
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    content_type: Optional[ContentTypeType]
    author: Optional[UserType]


@strawberry.type
class MediaType:
    """Media/Asset GraphQL type."""
    id: int
    filename: str
    original_filename: str
    content_type: str
    size: int
    storage_path: str
    public_url: Optional[str]
    alt_text: Optional[str]
    caption: Optional[str]
    width: Optional[int]
    height: Optional[int]
    created_at: datetime
    uploaded_by: Optional[UserType]


@strawberry.type
class TranslationType:
    """Translation GraphQL type."""
    id: int
    locale: str
    field_name: str
    translated_value: str
    translation_status: str
    is_auto_translated: bool
    created_at: datetime


@strawberry.type
class LocaleType:
    """Locale GraphQL type."""
    id: int
    code: str
    name: str
    is_default: bool
    is_enabled: bool


@strawberry.type
class ThemeType:
    """Theme GraphQL type."""
    id: int
    name: str
    is_system_theme: bool
    is_active: bool
    colors: strawberry.scalars.JSON
    typography: Optional[strawberry.scalars.JSON]
    spacing: Optional[strawberry.scalars.JSON]
    created_at: datetime


@strawberry.type
class ContentTemplateType:
    """Content Template GraphQL type."""
    id: int
    name: str
    description: Optional[str]
    category: Optional[str]
    field_defaults: Optional[strawberry.scalars.JSON]
    field_config: Optional[strawberry.scalars.JSON]
    is_published: bool
    usage_count: int
    tags: Optional[str]
    created_at: datetime


@strawberry.type
class PaginationInfo:
    """Pagination information."""
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


@strawberry.type
class ContentEntryConnection:
    """Paginated content entries."""
    items: List[ContentEntryType]
    pagination: PaginationInfo


@strawberry.type
class MediaConnection:
    """Paginated media items."""
    items: List[MediaType]
    pagination: PaginationInfo
