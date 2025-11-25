"""
GraphQL resolvers for queries and mutations.
"""
from typing import Optional, List
import strawberry
from strawberry.types import Info

from backend.graphql.types import (
    ContentEntryType,
    ContentTypeType,
    MediaType,
    UserType,
    OrganizationType,
    TranslationType,
    LocaleType,
    ThemeType,
    ContentTemplateType,
    ContentEntryConnection,
    MediaConnection,
    PaginationInfo,
)
from backend.graphql.context import GraphQLContext
from backend.models.content import ContentEntry, ContentType
from backend.models.media import Media
from backend.models.user import User
from backend.models.organization import Organization
from backend.models.translation import Translation, Locale
from backend.models.theme import Theme
from backend.models.content_template import ContentTemplate


def to_content_entry_type(entry: ContentEntry) -> ContentEntryType:
    """Convert SQLAlchemy model to GraphQL type."""
    return ContentEntryType(
        id=entry.id,
        slug=entry.slug,
        status=entry.status,
        content_data=entry.content_data,
        seo_metadata=entry.seo_metadata,
        version=entry.version,
        published_at=entry.published_at,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        content_type=to_content_type_type(entry.content_type) if entry.content_type else None,
        author=to_user_type(entry.author) if entry.author else None,
    )


def to_content_type_type(ct: ContentType) -> ContentTypeType:
    """Convert ContentType to GraphQL type."""
    return ContentTypeType(
        id=ct.id,
        name=ct.name,
        slug=ct.slug,
        description=ct.description,
        fields=ct.fields,
        created_at=ct.created_at,
        updated_at=ct.updated_at,
    )


def to_media_type(media: Media) -> MediaType:
    """Convert Media to GraphQL type."""
    return MediaType(
        id=media.id,
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
    return UserType(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
        organization=to_organization_type(user.organization) if user.organization else None,
    )


def to_organization_type(org: Organization) -> OrganizationType:
    """Convert Organization to GraphQL type."""
    return OrganizationType(
        id=org.id,
        name=org.name,
        slug=org.slug,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def to_translation_type(trans: Translation) -> TranslationType:
    """Convert Translation to GraphQL type."""
    return TranslationType(
        id=trans.id,
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
        id=locale.id,
        code=locale.code,
        name=locale.name,
        is_default=locale.is_default,
        is_enabled=locale.is_enabled,
    )


def to_theme_type(theme: Theme) -> ThemeType:
    """Convert Theme to GraphQL type."""
    return ThemeType(
        id=theme.id,
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
        id=template.id,
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
    def content_entry(self, info: Info[GraphQLContext, None], id: int) -> Optional[ContentEntryType]:
        """Get content entry by ID."""
        context: GraphQLContext = info.context
        context.require_permission("content.read")
        
        entry = context.db.query(ContentEntry).filter(
            ContentEntry.id == id,
            ContentEntry.organization_id == context.organization_id
        ).first()
        
        return to_content_entry_type(entry) if entry else None
    
    @strawberry.field
    def content_entries(
        self,
        info: Info[GraphQLContext, None],
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        content_type_slug: Optional[str] = None,
    ) -> ContentEntryConnection:
        """List content entries with pagination and filters."""
        context: GraphQLContext = info.context
        context.require_permission("content.read")
        
        query = context.db.query(ContentEntry).filter(
            ContentEntry.organization_id == context.organization_id
        )
        
        if status:
            query = query.filter(ContentEntry.status == status)
        
        if content_type_slug:
            query = query.join(ContentType).filter(ContentType.slug == content_type_slug)
        
        total = query.count()
        entries = query.order_by(ContentEntry.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        total_pages = (total + per_page - 1) // per_page
        
        return ContentEntryConnection(
            items=[to_content_entry_type(e) for e in entries],
            pagination=PaginationInfo(
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            )
        )
    
    @strawberry.field
    def content_types(self, info: Info[GraphQLContext, None]) -> List[ContentTypeType]:
        """List all content types for current organization."""
        context: GraphQLContext = info.context
        context.require_permission("content.read")
        
        types = context.db.query(ContentType).filter(
            ContentType.organization_id == context.organization_id
        ).all()
        
        return [to_content_type_type(ct) for ct in types]
    
    @strawberry.field
    def media(
        self,
        info: Info[GraphQLContext, None],
        page: int = 1,
        per_page: int = 20,
    ) -> MediaConnection:
        """List media files with pagination."""
        context: GraphQLContext = info.context
        context.require_permission("media.read")
        
        query = context.db.query(Media).filter(
            Media.organization_id == context.organization_id
        )
        
        total = query.count()
        items = query.order_by(Media.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        total_pages = (total + per_page - 1) // per_page
        
        return MediaConnection(
            items=[to_media_type(m) for m in items],
            pagination=PaginationInfo(
                total=total,
                page=page,
                per_page=per_page,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            )
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
        
        locales = context.db.query(Locale).filter(
            Locale.organization_id == context.organization_id,
            Locale.is_enabled == True
        ).all()
        
        return [to_locale_type(l) for l in locales]
    
    @strawberry.field
    def themes(self, info: Info[GraphQLContext, None]) -> List[ThemeType]:
        """List themes for current organization."""
        context: GraphQLContext = info.context
        context.require_auth()
        
        themes = context.db.query(Theme).filter(
            Theme.organization_id == context.organization_id
        ).all()
        
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
    def publish_content(self, info: Info[GraphQLContext, None], id: int) -> ContentEntryType:
        """Publish a content entry."""
        context: GraphQLContext = info.context
        context.require_permission("content.publish")
        
        entry = context.db.query(ContentEntry).filter(
            ContentEntry.id == id,
            ContentEntry.organization_id == context.organization_id
        ).first()
        
        if not entry:
            raise Exception("Content entry not found")
        
        from datetime import datetime
        entry.status = "published"
        entry.published_at = datetime.utcnow()
        context.db.commit()
        context.db.refresh(entry)
        
        return to_content_entry_type(entry)
    
    @strawberry.field
    def unpublish_content(self, info: Info[GraphQLContext, None], id: int) -> ContentEntryType:
        """Unpublish a content entry."""
        context: GraphQLContext = info.context
        context.require_permission("content.update")
        
        entry = context.db.query(ContentEntry).filter(
            ContentEntry.id == id,
            ContentEntry.organization_id == context.organization_id
        ).first()
        
        if not entry:
            raise Exception("Content entry not found")
        
        entry.status = "draft"
        context.db.commit()
        context.db.refresh(entry)
        
        return to_content_entry_type(entry)


# Create the schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
