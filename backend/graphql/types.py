"""
GraphQL types for core models.
"""
from typing import Optional, List
from datetime import datetime
import strawberry
from uuid import UUID


@strawberry.type
class OrganizationType:
    """Organization/Tenant GraphQL type."""
    id: strawberry.ID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class UserType:
    """User GraphQL type."""
    id: strawberry.ID
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    organization: Optional[OrganizationType]


@strawberry.type
class ContentTypeType:
    """Content Type (schema) GraphQL type."""
    id: strawberry.ID
    name: str
    slug: str
    description: Optional[str]
    fields: strawberry.scalars.JSON
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ContentEntryType:
    """Content Entry GraphQL type."""
    id: strawberry.ID
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
    id: strawberry.ID
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
    id: strawberry.ID
    locale: str
    field_name: str
    translated_value: str
    translation_status: str
    is_auto_translated: bool
    created_at: datetime


@strawberry.type
class LocaleType:
    """Locale GraphQL type."""
    id: strawberry.ID
    code: str
    name: str
    is_default: bool
    is_enabled: bool


@strawberry.type
class ThemeType:
    """Theme GraphQL type."""
    id: strawberry.ID
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
    id: strawberry.ID
    name: str
    description: Optional[str]
    category: Optional[str]
    field_defaults: Optional[strawberry.scalars.JSON]
    field_config: Optional[strawberry.scalars.JSON]
    is_published: bool
    usage_count: int
    tags: Optional[str]
    created_at: datetime


@strawberry.input
class Pageable:
    """
    Input type for pagination parameters (Spring-style Pageable pattern).

    Attributes:
        page: Zero-based page number (default: 0)
        size: Number of items per page (default: 20, max: 100)
        sort: Optional sort field
        direction: Sort direction ('asc' or 'desc')
    """
    page: int = 0  # Zero-based page number (Spring convention)
    size: int = 20
    sort: Optional[str] = None
    direction: str = "desc"

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 0:
            self.page = 0
        if self.size < 1:
            self.size = 1
        if self.size > 100:
            self.size = 100  # Max limit to prevent abuse
        if self.direction not in ("asc", "desc"):
            self.direction = "desc"

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return self.page * self.size


@strawberry.type
class PageInfo:
    """
    Pagination metadata for a Page response (Spring-style Page pattern).

    Attributes:
        total_elements: Total number of elements across all pages
        total_pages: Total number of pages
        size: Number of elements per page
        number: Current page number (zero-based)
        number_of_elements: Number of elements in current page
        first: Whether this is the first page
        last: Whether this is the last page
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
        sort: Sort field used
        direction: Sort direction used
    """
    total_elements: int
    total_pages: int
    size: int
    number: int  # Current page number (zero-based)
    number_of_elements: int
    first: bool
    last: bool
    has_next: bool
    has_previous: bool
    sort: Optional[str] = None
    direction: str = "desc"

    @staticmethod
    def from_pageable(pageable: Pageable, total_elements: int, number_of_elements: int) -> "PageInfo":
        """Create PageInfo from a Pageable request and query results."""
        total_pages = (total_elements + pageable.size - 1) // pageable.size if pageable.size > 0 else 0
        return PageInfo(
            total_elements=total_elements,
            total_pages=total_pages,
            size=pageable.size,
            number=pageable.page,
            number_of_elements=number_of_elements,
            first=pageable.page == 0,
            last=pageable.page >= total_pages - 1 if total_pages > 0 else True,
            has_next=pageable.page < total_pages - 1 if total_pages > 0 else False,
            has_previous=pageable.page > 0,
            sort=pageable.sort,
            direction=pageable.direction,
        )


# Backward compatibility aliases
PageRequest = Pageable
PaginationInfo = PageInfo


@strawberry.type
class ContentEntryConnection:
    """Paginated content entries (Page<ContentEntry>)."""
    content: List[ContentEntryType]  # Spring uses 'content' not 'items'
    page_info: PageInfo

    # Backward compatibility
    @strawberry.field
    def items(self) -> List[ContentEntryType]:
        """Alias for content (backward compatibility)."""
        return self.content


@strawberry.type
class MediaConnection:
    """Paginated media items (Page<Media>)."""
    content: List[MediaType]  # Spring uses 'content' not 'items'
    page_info: PageInfo

    # Backward compatibility
    @strawberry.field
    def items(self) -> List[MediaType]:
        """Alias for content (backward compatibility)."""
        return self.content
