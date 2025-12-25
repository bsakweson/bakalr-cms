"""
GraphQL resolvers for queries and mutations.
"""

from typing import List, Optional

import strawberry
from sqlalchemy.orm import joinedload
from strawberry.types import Info

from backend.graphql.context import GraphQLContext
from backend.graphql.types import (
    ContentEntryConnection,
    ContentEntryType,
    ContentTemplateType,
    ContentTypeType,
    LocaleType,
    MediaConnection,
    MediaType,
    OrganizationType,
    Pageable,
    PageInfo,
    ThemeType,
    TranslationType,
    UserType,
)
from backend.models.content import ContentEntry, ContentType
from backend.models.content_template import ContentTemplate
from backend.models.media import Media
from backend.models.organization import Organization
from backend.models.theme import Theme
from backend.models.translation import Locale, Translation
from backend.models.user import User


def to_content_entry_type(entry: ContentEntry) -> ContentEntryType:
    """Convert SQLAlchemy model to GraphQL type."""
    import json
    from datetime import datetime

    # Parse JSON fields
    content_data = json.loads(entry.data) if entry.data else {}
    seo_metadata = json.loads(entry.seo_data) if entry.seo_data else None

    # Parse published_at if it's a string
    published_at = None
    if entry.published_at:
        if isinstance(entry.published_at, str):
            try:
                published_at = datetime.fromisoformat(entry.published_at.replace('Z', '+00:00'))
            except ValueError:
                published_at = None
        else:
            published_at = entry.published_at

    return ContentEntryType(
        id=str(entry.id),
        slug=entry.slug,
        status=entry.status,
        content_data=content_data,
        seo_metadata=seo_metadata,
        version=entry.version,
        published_at=published_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        content_type=to_content_type_type(entry.content_type) if entry.content_type else None,
        author=to_user_type(entry.author) if entry.author else None,
    )


def to_content_type_type(ct: ContentType) -> ContentTypeType:
    """Convert ContentType to GraphQL type."""
    import json
    # Parse fields_schema from JSON string
    fields = json.loads(ct.fields_schema) if ct.fields_schema else []
    return ContentTypeType(
        id=str(ct.id),
        name=ct.name,
        slug=ct.api_id,  # Model uses api_id instead of slug
        description=ct.description,
        fields=fields,  # Parse JSON string to dict/list
        created_at=ct.created_at,
        updated_at=ct.updated_at,
    )


def to_media_type(media: Media) -> MediaType:
    """Convert Media to GraphQL type."""
    return MediaType(
        id=str(media.id),
        filename=media.filename,
        original_filename=media.original_filename,
        content_type=media.content_type,
        size=media.size,
        storage_path=media.storage_path,
        public_url=media.public_url,
        alt_text=media.alt_text,
        caption=media.caption,
        width=media.width,
        height=media.height,
        created_at=media.created_at,
        uploaded_by=to_user_type(media.uploaded_by) if media.uploaded_by else None,
    )


def to_user_type(user: User) -> UserType:
    """Convert User to GraphQL type."""
    # Construct full_name from first_name and last_name
    full_name = None
    if user.first_name or user.last_name:
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()

    return UserType(
        id=str(user.id),
        email=user.email,
        full_name=full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        organization=to_organization_type(user.organization) if user.organization else None,
    )


def to_organization_type(org: Organization) -> OrganizationType:
    """Convert Organization to GraphQL type."""
    return OrganizationType(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def to_translation_type(trans: Translation) -> TranslationType:
    """Convert Translation to GraphQL type."""
    return TranslationType(
        id=str(trans.id),
        locale=trans.locale,
        field_name=trans.field_name,
        translated_value=trans.translated_value,
        translation_status=trans.translation_status,
        is_auto_translated=trans.is_auto_translated,
        created_at=trans.created_at,
    )


def to_locale_type(locale: Locale) -> LocaleType:
    """Convert Locale to GraphQL type."""
    return LocaleType(
        id=str(locale.id),
        code=locale.code,
        name=locale.name,
        is_default=locale.is_default,
        is_enabled=locale.is_enabled,
    )


def to_theme_type(theme: Theme) -> ThemeType:
    """Convert Theme to GraphQL type."""
    return ThemeType(
        id=str(theme.id),
        name=theme.name,
        is_system_theme=theme.is_system_theme,
        is_active=theme.is_active,
        colors=theme.colors,
        typography=theme.typography,
        spacing=theme.spacing,
        created_at=theme.created_at,
    )


def to_content_template_type(template: ContentTemplate) -> ContentTemplateType:
    """Convert ContentTemplate to GraphQL type."""
    return ContentTemplateType(
        id=str(template.id),
        name=template.name,
        description=template.description,
        category=template.category,
        field_defaults=template.field_defaults,
        field_config=template.field_config,
        is_published=template.is_published,
        usage_count=template.usage_count,
        tags=template.tags,
        created_at=template.created_at,
    )


@strawberry.type
class Query:
    """GraphQL Query type with all read operations."""

    @strawberry.field
    def content_entry(
        self, info: Info[GraphQLContext, None], id: strawberry.ID
    ) -> Optional[ContentEntryType]:
        """Get content entry by ID."""
        context: GraphQLContext = info.context
        context.require_permission("content.read")

        # ContentEntry doesn't have organization_id directly - filter through ContentType
        # Use joinedload to eagerly load relationships
        entry = (
            context.db.query(ContentEntry)
            .options(
                joinedload(ContentEntry.content_type),
                joinedload(ContentEntry.author)
            )
            .join(ContentType)
            .filter(
                ContentEntry.id == id,
                ContentType.organization_id == context.organization_id
            )
            .first()
        )

        return to_content_entry_type(entry) if entry else None

    @strawberry.field
    def content_entries(
        self,
        info: Info[GraphQLContext, None],
        pageable: Optional[Pageable] = None,
        # Backward compatibility params
        page: Optional[int] = None,
        size: Optional[int] = None,
        per_page: Optional[int] = None,  # Deprecated alias for size
        status: Optional[str] = None,
        content_type_slug: Optional[str] = None,
    ) -> ContentEntryConnection:
        """List content entries with pagination and filters.

        Args:
            pageable: Pageable input for pagination (recommended)
            page: Page number (zero-based, for backward compatibility)
            size: Page size (for backward compatibility)
            per_page: Deprecated alias for size
            status: Filter by content status
            content_type_slug: Filter by content type
        """
        context: GraphQLContext = info.context
        context.require_permission("content.read")

        # Build Pageable from input or backward-compatible params
        if pageable is None:
            # Handle backward compatibility: per_page -> size
            effective_size = size if size is not None else (per_page if per_page is not None else 20)
            # Convert 1-based page to 0-based if old convention used
            effective_page = page if page is not None else 0
            pageable = Pageable(page=effective_page, size=effective_size)

        # ContentEntry doesn't have organization_id directly - filter through ContentType
        # Use joinedload to eagerly load relationships for efficient serialization
        query = (
            context.db.query(ContentEntry)
            .options(
                joinedload(ContentEntry.content_type),
                joinedload(ContentEntry.author)
            )
            .join(ContentType)
            .filter(ContentType.organization_id == context.organization_id)
        )

        if status:
            query = query.filter(ContentEntry.status == status)

        if content_type_slug:
            # ContentType already joined above, just filter by api_id (slug)
            query = query.filter(ContentType.api_id == content_type_slug)

        # Apply sorting
        if pageable.sort:
            sort_column = getattr(ContentEntry, pageable.sort, None)
            if sort_column is not None:
                if pageable.direction == "asc":
                    query = query.order_by(sort_column.asc())
                else:
                    query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(ContentEntry.created_at.desc())

        total = query.count()
        entries = query.offset(pageable.offset).limit(pageable.size).all()

        return ContentEntryConnection(
            content=[to_content_entry_type(e) for e in entries],
            page_info=PageInfo.from_pageable(pageable, total, len(entries)),
        )

    @strawberry.field
    def content_types(self, info: Info[GraphQLContext, None]) -> List[ContentTypeType]:
        """List all content types for current organization."""
        context: GraphQLContext = info.context
        context.require_permission("content.read")

        types = (
            context.db.query(ContentType)
            .filter(ContentType.organization_id == context.organization_id)
            .all()
        )

        return [to_content_type_type(ct) for ct in types]

    @strawberry.field
    def media(
        self,
        info: Info[GraphQLContext, None],
        pageable: Optional[Pageable] = None,
        # Backward compatibility params
        page: Optional[int] = None,
        size: Optional[int] = None,
        per_page: Optional[int] = None,  # Deprecated alias for size
    ) -> MediaConnection:
        """List media files with pagination.

        Args:
            pageable: Pageable input for pagination (recommended)
            page: Page number (zero-based, for backward compatibility)
            size: Page size (for backward compatibility)
            per_page: Deprecated alias for size
        """
        context: GraphQLContext = info.context
        context.require_permission("media.read")

        # Build Pageable from input or backward-compatible params
        if pageable is None:
            effective_size = size if size is not None else (per_page if per_page is not None else 20)
            effective_page = page if page is not None else 0
            pageable = Pageable(page=effective_page, size=effective_size)

        query = context.db.query(Media).filter(Media.organization_id == context.organization_id)

        # Apply sorting
        if pageable.sort:
            sort_column = getattr(Media, pageable.sort, None)
            if sort_column is not None:
                if pageable.direction == "asc":
                    query = query.order_by(sort_column.asc())
                else:
                    query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(Media.created_at.desc())

        total = query.count()
        items = query.offset(pageable.offset).limit(pageable.size).all()

        return MediaConnection(
            content=[to_media_type(m) for m in items],
            page_info=PageInfo.from_pageable(pageable, total, len(items)),
        )

    @strawberry.field
    def me(self, info: Info[GraphQLContext, None]) -> Optional[UserType]:
        """Get current authenticated user."""
        context: GraphQLContext = info.context
        user = context.user
        return to_user_type(user) if user else None

    @strawberry.field
    def locales(self, info: Info[GraphQLContext, None]) -> List[LocaleType]:
        """List enabled locales for current organization."""
        context: GraphQLContext = info.context
        context.require_auth()

        locales = (
            context.db.query(Locale)
            .filter(Locale.organization_id == context.organization_id, Locale.is_enabled == True)
            .all()
        )

        return [to_locale_type(l) for l in locales]

    @strawberry.field
    def themes(self, info: Info[GraphQLContext, None]) -> List[ThemeType]:
        """List themes for current organization."""
        context: GraphQLContext = info.context
        context.require_auth()

        themes = (
            context.db.query(Theme).filter(Theme.organization_id == context.organization_id).all()
        )

        return [to_theme_type(t) for t in themes]

    @strawberry.field
    def content_templates(
        self,
        info: Info[GraphQLContext, None],
        published_only: bool = True,
    ) -> List[ContentTemplateType]:
        """List content templates."""
        context: GraphQLContext = info.context
        context.require_permission("content.read")

        query = context.db.query(ContentTemplate).filter(
            ContentTemplate.organization_id == context.organization_id
        )

        if published_only:
            query = query.filter(ContentTemplate.is_published == True)

        templates = query.all()
        return [to_content_template_type(t) for t in templates]


@strawberry.type
class Mutation:
    """GraphQL Mutation type for write operations."""

    @strawberry.field
    def publish_content(self, info: Info[GraphQLContext, None], id: strawberry.ID) -> ContentEntryType:
        """Publish a content entry."""
        context: GraphQLContext = info.context
        context.require_permission("content.publish")

        # ContentEntry doesn't have organization_id directly - filter through ContentType
        # Use joinedload to eagerly load relationships
        entry = (
            context.db.query(ContentEntry)
            .options(
                joinedload(ContentEntry.content_type),
                joinedload(ContentEntry.author)
            )
            .join(ContentType)
            .filter(
                ContentEntry.id == id,
                ContentType.organization_id == context.organization_id
            )
            .first()
        )

        if not entry:
            raise Exception("Content entry not found")

        from datetime import datetime, timezone

        entry.status = "published"
        entry.published_at = datetime.now(timezone.utc).isoformat()
        context.db.commit()
        context.db.refresh(entry)

        return to_content_entry_type(entry)

    @strawberry.field
    def unpublish_content(self, info: Info[GraphQLContext, None], id: strawberry.ID) -> ContentEntryType:
        """Unpublish a content entry."""
        context: GraphQLContext = info.context
        context.require_permission("content.update")

        # ContentEntry doesn't have organization_id directly - filter through ContentType
        # Use joinedload to eagerly load relationships
        entry = (
            context.db.query(ContentEntry)
            .options(
                joinedload(ContentEntry.content_type),
                joinedload(ContentEntry.author)
            )
            .join(ContentType)
            .filter(
                ContentEntry.id == id,
                ContentType.organization_id == context.organization_id
            )
            .first()
        )

        if not entry:
            raise Exception("Content entry not found")

        entry.status = "draft"
        context.db.commit()
        context.db.refresh(entry)

        return to_content_entry_type(entry)


from backend.core.config import settings

# Import validators for schema extensions
from backend.graphql.validators import QueryComplexityLimiter, QueryDepthLimiter, QueryTimeout

# Create the schema with security extensions
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        QueryDepthLimiter(max_depth=settings.GRAPHQL_MAX_DEPTH),
        QueryComplexityLimiter(max_complexity=settings.GRAPHQL_MAX_COMPLEXITY),
        QueryTimeout(timeout_seconds=settings.GRAPHQL_TIMEOUT_SECONDS),
    ],
)
