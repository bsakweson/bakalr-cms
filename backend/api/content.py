"""
Content Management API endpoints
"""

import ast
import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

logger = logging.getLogger(__name__)


def parse_fields_schema(fields_schema) -> list:
    """
    Safely parse fields_schema which may be JSON, Python-style string, or already a list/dict.
    Returns a list of field definitions.
    """
    if not fields_schema:
        return []

    if isinstance(fields_schema, list):
        return fields_schema

    if isinstance(fields_schema, dict):
        return list(fields_schema.values()) if fields_schema else []

    if isinstance(fields_schema, str):
        try:
            return json.loads(fields_schema)
        except json.JSONDecodeError:
            # Try parsing as Python literal (handles True/False/None and single quotes)
            try:
                return ast.literal_eval(fields_schema)
            except (ValueError, SyntaxError):
                return []

    return []


from backend.api.schemas.content import (
    ContentEntryCreate,
    ContentEntryListResponse,
    ContentEntryPublish,
    ContentEntryResponse,
    ContentEntryUpdate,
    ContentTypeCreate,
    ContentTypeResponse,
    ContentTypeUpdate,
)
from backend.core.cache import invalidate_cache_pattern
from backend.core.dependencies import get_current_user, get_current_user_flexible
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.translation_service import get_translation_service
from backend.core.webhook_service import (
    publish_content_created_sync,
    publish_content_deleted_sync,
    publish_content_published_sync,
    publish_content_updated_sync,
)
from backend.db.session import get_db
from backend.models.content import ContentEntry, ContentType
from backend.models.translation import Locale, Translation
from backend.models.user import User

router = APIRouter(prefix="/content", tags=["Content Management"])


# Helper function to build ContentEntryResponse
def build_entry_response(entry: ContentEntry) -> ContentEntryResponse:
    """Helper to build ContentEntryResponse from ContentEntry model"""
    data = json.loads(entry.data) if entry.data else {}
    seo_data = json.loads(entry.seo_data) if entry.seo_data else {}

    # Build content_type object if relationship is loaded
    content_type_data = None
    # Debug: what is in entry.content_type?
    ct = entry.content_type
    if ct:
        content_type_data = {
            "id": ct.id,
            "name": ct.name,
            "api_id": ct.api_id,
        }
    else:
        # Log why it's None
        logger.warning(
            f"content_type is None for entry {entry.id}, content_type_id={entry.content_type_id}"
        )

    return ContentEntryResponse(
        id=entry.id,
        content_type_id=entry.content_type_id,
        content_type=content_type_data,
        author_id=entry.author_id,
        data=data,
        slug=entry.slug,
        status=entry.status,
        version=entry.version,
        published_at=entry.published_at,
        seo_title=seo_data.get("seo_title"),
        seo_description=seo_data.get("seo_description"),
        seo_keywords=seo_data.get("seo_keywords"),
        og_image=seo_data.get("og_image"),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def auto_translate_entry_background(entry_id: UUID, organization_id: UUID, db: Session):
    """
    Background task to automatically translate content entry to all enabled locales with auto_translate=True.
    Only translates fields marked with localized: true in the content type schema.
    """
    translation_service = get_translation_service()

    # Get entry with content type
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(ContentEntry.id == entry_id, ContentType.organization_id == organization_id)
        .first()
    )

    if not entry:
        return

    # Get content type to check schema for localized fields
    content_type = entry.content_type

    # Get all enabled locales with auto_translate enabled
    locales = (
        db.query(Locale)
        .filter(
            Locale.organization_id == organization_id,
            Locale.is_enabled.is_(True),
            Locale.auto_translate.is_(True),
        )
        .all()
    )

    if not locales:
        return

    # Parse entry data
    entry_data = json.loads(entry.data) if entry.data else {}

    # Extract translatable fields from content type schema
    # Only fields with localized: true (or not explicitly set to false) should be translated
    translatable_fields = None
    if content_type and content_type.fields_schema:
        schema_fields = parse_fields_schema(content_type.fields_schema)
        translatable_fields = []

        # Schema can be either a list of field objects or a dict
        if isinstance(schema_fields, list):
            # List format: [{"name": "field_name", "type": "text", "localized": true}, ...]
            for field in schema_fields:
                if isinstance(field, dict):
                    field_name = field.get("name")
                    if field_name and field.get("localized", True):
                        translatable_fields.append(field_name)
        elif isinstance(schema_fields, dict):
            # Dict format: {"field_name": {"type": "text", "localized": true}, ...}
            for field_name, field_config in schema_fields.items():
                if isinstance(field_config, dict):
                    if field_config.get("localized", True):
                        translatable_fields.append(field_name)
                else:
                    # If field config is not a dict, include it by default
                    translatable_fields.append(field_name)

        # If no fields are translatable, use None to translate all (backward compat)
        if not translatable_fields:
            translatable_fields = None

    for locale in locales:
        # Check if translation already exists
        existing = (
            db.query(Translation)
            .filter(Translation.content_entry_id == entry_id, Translation.locale_id == locale.id)
            .first()
        )

        if existing:
            continue  # Skip if already translated

        try:
            # Translate the content, respecting localized field settings
            translated_data = translation_service.translate_dict(
                entry_data,
                target_lang=locale.code.split("-")[0],  # Use base language code
                source_lang=None,
                translatable_fields=translatable_fields,
            )

            # Create translation record using actual provider
            translation = Translation(
                content_entry_id=entry_id,
                locale_id=locale.id,
                translated_data=json.dumps(translated_data),
                status="completed",
                translation_service=translation_service.provider,
                quality_score=0.95,
            )
            db.add(translation)

        except Exception as e:
            # Log error but don't fail the entire process
            print(f"Auto-translation failed for locale {locale.code}: {e}")
            continue

    db.commit()


def auto_update_translations_background(entry_id: UUID, organization_id: UUID, db: Session):
    """
    Background task to automatically update translations when content is modified.
    Re-translates content for all enabled locales with auto_translate=True.
    """
    translation_service = get_translation_service()

    # Get entry with content type
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(ContentEntry.id == entry_id, ContentType.organization_id == organization_id)
        .first()
    )

    if not entry:
        return

    # Get content type to check schema for localized fields
    content_type = entry.content_type

    # Get all enabled locales with auto_translate enabled
    locales = (
        db.query(Locale)
        .filter(
            Locale.organization_id == organization_id,
            Locale.is_enabled.is_(True),
            Locale.auto_translate.is_(True),
        )
        .all()
    )

    if not locales:
        return

    # Parse entry data
    entry_data = json.loads(entry.data) if entry.data else {}

    # Extract translatable fields from content type schema
    translatable_fields = None
    if content_type and content_type.fields_schema:
        schema_fields = parse_fields_schema(content_type.fields_schema)
        translatable_fields = []

        if isinstance(schema_fields, list):
            for field in schema_fields:
                if isinstance(field, dict):
                    field_name = field.get("name")
                    if field_name and field.get("localized", True):
                        translatable_fields.append(field_name)
        elif isinstance(schema_fields, dict):
            for field_name, field_config in schema_fields.items():
                if isinstance(field_config, dict):
                    if field_config.get("localized", True):
                        translatable_fields.append(field_name)
                else:
                    translatable_fields.append(field_name)

        if not translatable_fields:
            translatable_fields = None

    for locale in locales:
        try:
            # Translate the content
            translated_data = translation_service.translate_dict(
                entry_data,
                target_lang=locale.code.split("-")[0],
                source_lang=None,
                translatable_fields=translatable_fields,
            )

            # Check if translation exists
            existing = (
                db.query(Translation)
                .filter(
                    Translation.content_entry_id == entry_id, Translation.locale_id == locale.id
                )
                .first()
            )

            if existing:
                # Update existing translation
                existing.translated_data = json.dumps(translated_data)
                existing.status = "completed"
                existing.translation_service = translation_service.provider
                existing.version = (existing.version or 1) + 1
            else:
                # Create new translation
                translation = Translation(
                    content_entry_id=entry_id,
                    locale_id=locale.id,
                    translated_data=json.dumps(translated_data),
                    status="completed",
                    translation_service=translation_service.provider,
                    quality_score=0.95,
                )
                db.add(translation)

        except Exception as e:
            print(f"Auto-translation update failed for locale {locale.code}: {e}")
            continue

    db.commit()


# ContentType Endpoints


@router.post("/types", response_model=ContentTypeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def create_content_type(
    request: Request,
    content_type_data: ContentTypeCreate,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Create a new content type

    Requires appropriate permissions to create content types.
    Content types are scoped to the user's organization.
    """
    # Check if api_id is unique within organization
    existing = (
        db.query(ContentType)
        .filter(
            ContentType.organization_id == current_user.organization_id,
            ContentType.api_id == content_type_data.api_id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type with api_id '{content_type_data.api_id}' already exists",
        )

    # Create content type
    content_type = ContentType(
        organization_id=current_user.organization_id,
        name=content_type_data.name,
        api_id=content_type_data.api_id,
        description=content_type_data.description,
        fields_schema=json.dumps([field.model_dump() for field in content_type_data.fields]),
    )

    db.add(content_type)
    db.commit()
    db.refresh(content_type)

    # Parse fields_schema back to list
    fields = parse_fields_schema(content_type.fields_schema)

    return ContentTypeResponse(
        id=content_type.id,
        organization_id=content_type.organization_id,
        name=content_type.name,
        api_id=content_type.api_id,
        description=content_type.description,
        fields=fields,
        display_field=None,  # Not stored in DB yet
        is_active=content_type.is_published,
        entry_count=0,
        created_at=content_type.created_at,
        updated_at=content_type.updated_at,
    )


@router.get("/types", response_model=List[ContentTypeResponse])
@limiter.limit(get_rate_limit())
async def list_content_types(
    request: Request,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """
    List all content types for the current organization.
    Supports both JWT and API key authentication.
    """
    content_types = (
        db.query(ContentType)
        .filter(ContentType.organization_id == current_user.organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for ct in content_types:
        fields = parse_fields_schema(ct.fields_schema)
        entry_count = (
            db.query(func.count(ContentEntry.id))
            .filter(ContentEntry.content_type_id == ct.id)
            .scalar()
        )

        results.append(
            ContentTypeResponse(
                id=ct.id,
                organization_id=ct.organization_id,
                name=ct.name,
                api_id=ct.api_id,
                description=ct.description,
                fields=fields,
                display_field=None,
                is_active=ct.is_published,
                entry_count=entry_count,
                created_at=ct.created_at,
                updated_at=ct.updated_at,
            )
        )

    return results


@router.get("/types/{content_type_id}", response_model=ContentTypeResponse)
@limiter.limit(get_rate_limit())
async def get_content_type(
    request: Request,
    content_type_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific content type by ID
    """
    content_type = (
        db.query(ContentType)
        .filter(
            ContentType.id == content_type_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content type not found")

    fields = parse_fields_schema(content_type.fields_schema)
    entry_count = (
        db.query(func.count(ContentEntry.id))
        .filter(ContentEntry.content_type_id == content_type.id)
        .scalar()
    )

    return ContentTypeResponse(
        id=content_type.id,
        organization_id=content_type.organization_id,
        name=content_type.name,
        api_id=content_type.api_id,
        description=content_type.description,
        fields=fields,
        display_field=None,
        is_active=content_type.is_published,
        entry_count=entry_count,
        created_at=content_type.created_at,
        updated_at=content_type.updated_at,
    )


@router.put("/types/{content_type_id}", response_model=ContentTypeResponse)
@limiter.limit(get_rate_limit())
async def update_content_type(
    request: Request,
    content_type_id: UUID,
    content_type_update: ContentTypeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a content type
    """
    content_type = (
        db.query(ContentType)
        .filter(
            ContentType.id == content_type_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content type not found")

    # Update fields
    if content_type_update.name is not None:
        content_type.name = content_type_update.name
    if content_type_update.description is not None:
        content_type.description = content_type_update.description
    if content_type_update.fields is not None:
        content_type.fields_schema = str(
            [field.model_dump() for field in content_type_update.fields]
        )
    if content_type_update.is_active is not None:
        content_type.is_published = content_type_update.is_active

    db.commit()
    db.refresh(content_type)

    fields = parse_fields_schema(content_type.fields_schema)
    entry_count = (
        db.query(func.count(ContentEntry.id))
        .filter(ContentEntry.content_type_id == content_type.id)
        .scalar()
    )

    return ContentTypeResponse(
        id=content_type.id,
        organization_id=content_type.organization_id,
        name=content_type.name,
        api_id=content_type.api_id,
        description=content_type.description,
        fields=fields,
        display_field=None,
        is_active=content_type.is_published,
        entry_count=entry_count,
        created_at=content_type.created_at,
        updated_at=content_type.updated_at,
    )


@router.patch("/types/{content_type_id}", response_model=ContentTypeResponse)
@limiter.limit(get_rate_limit())
async def patch_content_type(
    request: Request,
    content_type_id: UUID,
    content_type_update: ContentTypeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partially update a content type (PATCH)

    Only updates the fields that are provided in the request body.
    Requires admin privileges.
    """
    content_type = (
        db.query(ContentType)
        .filter(
            ContentType.id == content_type_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content type not found")

    # Only update fields that are explicitly provided (not None)
    if content_type_update.name is not None:
        content_type.name = content_type_update.name
    if content_type_update.description is not None:
        content_type.description = content_type_update.description
    if content_type_update.fields is not None:
        content_type.fields_schema = str(
            [field.model_dump() for field in content_type_update.fields]
        )
    if content_type_update.is_active is not None:
        content_type.is_published = content_type_update.is_active

    db.commit()
    db.refresh(content_type)

    fields = parse_fields_schema(content_type.fields_schema)
    entry_count = (
        db.query(func.count(ContentEntry.id))
        .filter(ContentEntry.content_type_id == content_type.id)
        .scalar()
    )

    return ContentTypeResponse(
        id=content_type.id,
        organization_id=content_type.organization_id,
        name=content_type.name,
        api_id=content_type.api_id,
        description=content_type.description,
        fields=fields,
        display_field=None,
        is_active=content_type.is_published,
        entry_count=entry_count,
        created_at=content_type.created_at,
        updated_at=content_type.updated_at,
    )


@router.delete("/types/{content_type_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_content_type(
    request: Request,
    content_type_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a content type

    Note: This will also delete all entries of this type
    """
    content_type = (
        db.query(ContentType)
        .filter(
            ContentType.id == content_type_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content type not found")

    db.delete(content_type)
    db.commit()


# ContentEntry Endpoints


@router.post("/entries", response_model=ContentEntryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def create_content_entry(
    request: Request,
    entry_data: ContentEntryCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Create a new content entry with automatic translation
    """
    import re

    # Verify content type exists and belongs to organization
    content_type = (
        db.query(ContentType)
        .filter(
            ContentType.id == entry_data.content_type_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content type not found")

    # Generate slug if not provided

    slug = entry_data.slug
    if not slug:
        # Generate from first text field or use default
        slug = f"entry-{content_type.api_id}"
        slug = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")

    # Check if slug already exists within the same content type and organization
    existing_entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(
            ContentEntry.slug == slug, ContentType.organization_id == current_user.organization_id
        )
        .first()
    )

    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An entry with slug '{slug}' already exists in this organization",
        )

    # Extract title from data for the title column
    title = entry_data.data.get("title", f"Entry {content_type.api_id}")

    # Build SEO data
    seo_data = {}
    if entry_data.seo_title:
        seo_data["seo_title"] = entry_data.seo_title
    if entry_data.seo_description:
        seo_data["seo_description"] = entry_data.seo_description
    if entry_data.seo_keywords:
        seo_data["seo_keywords"] = entry_data.seo_keywords
    if entry_data.og_image:
        seo_data["og_image"] = entry_data.og_image

    # Create entry
    # For API key auth, author_id may be None if user.id is not a valid UUID
    author_id = None
    try:
        from uuid import UUID as UUIDType

        if isinstance(current_user.id, str):
            UUIDType(current_user.id)  # Validate it's a UUID
            author_id = current_user.id
        else:
            author_id = current_user.id
    except (ValueError, AttributeError):
        # API key auth uses virtual user with non-UUID id
        author_id = None

    entry = ContentEntry(
        content_type_id=entry_data.content_type_id,
        author_id=author_id,
        title=title,
        data=json.dumps(entry_data.data),
        slug=slug,
        status=entry_data.status,
        version=1,
        seo_data=json.dumps(seo_data) if seo_data else None,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Trigger automatic translation in background
    background_tasks.add_task(
        auto_translate_entry_background, entry.id, current_user.organization_id, db
    )

    # Publish webhook event
    background_tasks.add_task(
        publish_content_created_sync,
        entry.id,
        current_user.organization_id,
        db,
    )

    # Index in search engine
    try:
        from backend.core.search_service import search_service

        background_tasks.add_task(search_service.index_content_entry, entry, db)
    except Exception as e:
        # Log error but don't fail content creation
        print(f"Failed to index content entry: {e}")

    return build_entry_response(entry)


@router.get("/entries", response_model=ContentEntryListResponse)
@limiter.limit(get_rate_limit())
async def list_content_entries(
    request: Request,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
    content_type_id: Optional[UUID] = Query(None),
    content_type_slug: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    category_id: Optional[str] = Query(
        None, description="Filter by category_id in data JSON field"
    ),
    brand_id: Optional[str] = Query(None, description="Filter by brand_id in data JSON field"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    List content entries with pagination and filters.
    Supports both JWT and API key authentication.

    Additional filters:
    - category_id: Filter entries where data->category_id matches
    - brand_id: Filter entries where data->brand_id matches
    """
    logger.info(f"========== LIST ENTRIES CALLED - Page {page} ==========")

    # Build subquery to filter by organization
    from sqlalchemy import select

    content_type_subquery = (
        select(ContentType.id)
        .where(ContentType.organization_id == current_user.organization_id)
        .scalar_subquery()
    )

    # If filtering by slug, we need to get the content type first
    filter_content_type_id = content_type_id
    if content_type_slug:
        content_type = (
            db.query(ContentType)
            .filter(
                ContentType.api_id == content_type_slug,
                ContentType.organization_id == current_user.organization_id,
            )
            .first()
        )
        if content_type:
            filter_content_type_id = content_type.id
        else:
            # No matching content type found, return empty result
            return ContentEntryListResponse(
                items=[], total=0, page=page, page_size=page_size, pages=0
            )

    query = (
        db.query(ContentEntry)
        .filter(ContentEntry.content_type_id.in_(content_type_subquery))
        .options(selectinload(ContentEntry.content_type))
    )
    logger.info("Query configured with selectinload and scalar_subquery")

    if filter_content_type_id:
        query = query.filter(ContentEntry.content_type_id == filter_content_type_id)

    if status:
        query = query.filter(ContentEntry.status == status)

    # Filter by category_id in JSON data field (data is stored as Text, cast to JSON)
    if category_id:
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSON

        query = query.filter(cast(ContentEntry.data, JSON)["category_id"].astext == category_id)
        logger.info(f"Filtering by category_id: {category_id}")

    # Filter by brand_id in JSON data field (data is stored as Text, cast to JSON)
    if brand_id:
        from sqlalchemy import cast
        from sqlalchemy.dialects.postgresql import JSON

        query = query.filter(cast(ContentEntry.data, JSON)["brand_id"].astext == brand_id)
        logger.info(f"Filtering by brand_id: {brand_id}")

    total = query.count()
    logger.info(f"Total entries: {total}")
    entries = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for entry in entries:
        data = json.loads(entry.data) if entry.data else {}
        seo_data = json.loads(entry.seo_data) if entry.seo_data else {}

        # FORCE fetch content type from database
        ct_from_db = db.query(ContentType).filter(ContentType.id == entry.content_type_id).first()
        content_type_data = None
        if ct_from_db:
            content_type_data = {
                "id": ct_from_db.id,
                "name": ct_from_db.name,
                "api_id": ct_from_db.api_id,
            }

        item = ContentEntryResponse(
            id=entry.id,
            content_type_id=entry.content_type_id,
            content_type=content_type_data,  # Add inline
            author_id=entry.author_id,
            data=data,
            slug=entry.slug,
            status=entry.status,
            version=entry.version,
            published_at=entry.published_at,
            seo_title=seo_data.get("seo_title"),
            seo_description=seo_data.get("seo_description"),
            seo_keywords=seo_data.get("seo_keywords"),
            og_image=seo_data.get("og_image"),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        items.append(item)

    pages = (total + page_size - 1) // page_size

    return ContentEntryListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )


@router.get("/products/by-category/{category_id}", response_model=ContentEntryListResponse)
@limiter.limit(get_rate_limit())
async def get_products_by_category(
    request: Request,
    category_id: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
    status: Optional[str] = Query("published"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    Get products filtered by category_id with pagination.
    Filters products where data->category_id matches the provided category_id.
    """
    logger.info(f"Getting products by category_id: {category_id}")

    # Get product content type
    product_type = (
        db.query(ContentType)
        .filter(
            ContentType.api_id == "product",
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not product_type:
        return ContentEntryListResponse(items=[], total=0, page=page, page_size=page_size, pages=0)

    # Query products with category_id filter using PostgreSQL JSON
    from sqlalchemy import text

    query = db.query(ContentEntry).filter(
        ContentEntry.content_type_id == product_type.id,
        text("data::json->>'category_id' = :cat_id").bindparams(cat_id=category_id),
    )

    if status:
        query = query.filter(ContentEntry.status == status)

    total = query.count()
    entries = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for entry in entries:
        data = json.loads(entry.data) if entry.data else {}
        seo_data = json.loads(entry.seo_data) if entry.seo_data else {}

        ct_from_db = db.query(ContentType).filter(ContentType.id == entry.content_type_id).first()
        content_type_data = None
        if ct_from_db:
            content_type_data = {
                "id": ct_from_db.id,
                "name": ct_from_db.name,
                "api_id": ct_from_db.api_id,
            }

        item = ContentEntryResponse(
            id=entry.id,
            content_type_id=entry.content_type_id,
            content_type=content_type_data,
            author_id=entry.author_id,
            data=data,
            slug=entry.slug,
            status=entry.status,
            version=entry.version,
            published_at=entry.published_at,
            seo_title=seo_data.get("seo_title"),
            seo_description=seo_data.get("seo_description"),
            seo_keywords=seo_data.get("seo_keywords"),
            og_image=seo_data.get("og_image"),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        items.append(item)

    pages = (total + page_size - 1) // page_size
    logger.info(f"Found {total} products for category {category_id}")

    return ContentEntryListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )


@router.get("/products/by-brand/{brand_id}", response_model=ContentEntryListResponse)
@limiter.limit(get_rate_limit())
async def get_products_by_brand(
    request: Request,
    brand_id: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
    status: Optional[str] = Query("published"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    Get products filtered by brand_id with pagination.
    Filters products where data->brand_id matches the provided brand_id.
    """
    logger.info(f"Getting products by brand_id: {brand_id}")

    # Get product content type
    product_type = (
        db.query(ContentType)
        .filter(
            ContentType.api_id == "product",
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not product_type:
        return ContentEntryListResponse(items=[], total=0, page=page, page_size=page_size, pages=0)

    # Query products with brand_id filter using PostgreSQL JSON
    from sqlalchemy import text

    query = db.query(ContentEntry).filter(
        ContentEntry.content_type_id == product_type.id,
        text("data::json->>'brand_id' = :brand_id").bindparams(brand_id=brand_id),
    )

    if status:
        query = query.filter(ContentEntry.status == status)

    total = query.count()
    entries = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for entry in entries:
        data = json.loads(entry.data) if entry.data else {}
        seo_data = json.loads(entry.seo_data) if entry.seo_data else {}

        ct_from_db = db.query(ContentType).filter(ContentType.id == entry.content_type_id).first()
        content_type_data = None
        if ct_from_db:
            content_type_data = {
                "id": ct_from_db.id,
                "name": ct_from_db.name,
                "api_id": ct_from_db.api_id,
            }

        item = ContentEntryResponse(
            id=entry.id,
            content_type_id=entry.content_type_id,
            content_type=content_type_data,
            author_id=entry.author_id,
            data=data,
            slug=entry.slug,
            status=entry.status,
            version=entry.version,
            published_at=entry.published_at,
            seo_title=seo_data.get("seo_title"),
            seo_description=seo_data.get("seo_description"),
            seo_keywords=seo_data.get("seo_keywords"),
            og_image=seo_data.get("og_image"),
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        items.append(item)

    pages = (total + page_size - 1) // page_size
    logger.info(f"Found {total} products for brand {brand_id}")

    return ContentEntryListResponse(
        items=items, total=total, page=page, page_size=page_size, pages=pages
    )


@router.get("/entries/{entry_id}", response_model=ContentEntryResponse)
@limiter.limit(get_rate_limit())
async def get_content_entry(
    request: Request,
    entry_id: UUID,
    locale: Optional[str] = Query(
        None, description="Locale code to return translated content (e.g., 'fr', 'es', 'de')"
    ),
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get a specific content entry by ID.
    Supports both JWT and API key authentication.

    If locale parameter is provided, returns the entry with translated data merged in.
    Only fields marked as 'localized: true' in the content type schema will be translated.
    """
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .options(selectinload(ContentEntry.content_type))
        .filter(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # If locale is requested, merge translation data
    if locale:
        from backend.models.translation import Locale, Translation

        # Find the locale
        locale_obj = (
            db.query(Locale)
            .filter(
                Locale.code == locale,
                Locale.organization_id == current_user.organization_id,
            )
            .first()
        )

        if locale_obj:
            # Get the translation for this entry and locale
            translation = (
                db.query(Translation)
                .filter(
                    Translation.content_entry_id == entry_id,
                    Translation.locale_id == locale_obj.id,
                )
                .first()
            )

            if translation and translation.translated_data:
                # Merge translated data into the entry
                original_data = json.loads(entry.data) if entry.data else {}
                translated_data = (
                    json.loads(translation.translated_data)
                    if isinstance(translation.translated_data, str)
                    else translation.translated_data
                )

                # Merge: translated data takes precedence
                merged_data = {**original_data, **translated_data}

                # Create a temporary copy of entry with merged data
                entry.data = json.dumps(merged_data)

    return build_entry_response(entry)


@router.put("/entries/{entry_id}", response_model=ContentEntryResponse)
@router.patch("/entries/{entry_id}", response_model=ContentEntryResponse)
@limiter.limit(get_rate_limit())
async def update_content_entry(
    request: Request,
    entry_id: UUID,
    entry_data: ContentEntryUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Update a content entry.
    Supports both JWT and API key authentication.
    """
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Update fields
    if entry_data.data is not None:
        entry.data = json.dumps(entry_data.data)
        # Update title if present in data
        if "title" in entry_data.data:
            entry.title = entry_data.data["title"]
        entry.version += 1
    if entry_data.slug is not None:
        entry.slug = entry_data.slug
    if entry_data.status is not None:
        entry.status = entry_data.status

    # Update SEO data
    seo_changed = False
    if any(
        [
            entry_data.seo_title,
            entry_data.seo_description,
            entry_data.seo_keywords,
            entry_data.og_image,
        ]
    ):
        seo_data = json.loads(entry.seo_data) if entry.seo_data else {}
        if entry_data.seo_title is not None:
            seo_data["seo_title"] = entry_data.seo_title
            seo_changed = True
        if entry_data.seo_description is not None:
            seo_data["seo_description"] = entry_data.seo_description
            seo_changed = True
        if entry_data.seo_keywords is not None:
            seo_data["seo_keywords"] = entry_data.seo_keywords
            seo_changed = True
        if entry_data.og_image is not None:
            seo_data["og_image"] = entry_data.og_image
            seo_changed = True

        if seo_changed:
            entry.seo_data = json.dumps(seo_data)

    db.commit()
    db.refresh(entry)

    # Invalidate caches
    await invalidate_cache_pattern(f"content:entry:{current_user.organization_id}:{entry_id}*")
    await invalidate_cache_pattern(f"content:list:{current_user.organization_id}*")
    await invalidate_cache_pattern(f"seo:*:{current_user.organization_id}:{entry_id}*")

    # Auto-update translations if content data changed
    if entry_data.data is not None:
        background_tasks.add_task(
            auto_update_translations_background, entry.id, current_user.organization_id, db
        )

    # Publish webhook event
    background_tasks.add_task(
        publish_content_updated_sync,
        entry.id,
        current_user.organization_id,
        db,
    )

    # Update search index
    try:
        from backend.core.search_service import search_service

        background_tasks.add_task(search_service.index_content_entry, entry, db)
    except Exception as e:
        print(f"Failed to update search index: {e}")

    return build_entry_response(entry)


@router.post("/entries/{entry_id}/publish", response_model=ContentEntryResponse)
@limiter.limit(get_rate_limit())
async def publish_content_entry(
    request: Request,
    entry_id: UUID,
    publish_data: ContentEntryPublish,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Publish a content entry
    """
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    from datetime import datetime, timezone

    entry.status = "published"
    entry.published_at = publish_data.publish_at or datetime.now(timezone.utc)

    db.commit()
    db.refresh(entry)

    # Invalidate caches
    await invalidate_cache_pattern(f"content:entry:{current_user.organization_id}:{entry_id}*")
    await invalidate_cache_pattern(f"content:list:{current_user.organization_id}*")
    await invalidate_cache_pattern(f"seo:sitemap:{current_user.organization_id}*")

    # Publish webhook event
    background_tasks.add_task(
        publish_content_published_sync,
        entry.id,
        current_user.organization_id,
        db,
    )

    # Update search index (published content)
    try:
        from backend.core.search_service import search_service

        background_tasks.add_task(search_service.index_content_entry, entry, db)
    except Exception as e:
        print(f"Failed to update search index: {e}")

    return build_entry_response(entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_content_entry(
    request: Request,
    entry_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a content entry
    """
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Store ID and org for webhook before deletion
    content_id = entry.id
    org_id = current_user.organization_id

    db.delete(entry)
    db.commit()

    # Invalidate caches
    await invalidate_cache_pattern(f"content:entry:{current_user.organization_id}:{entry_id}*")
    await invalidate_cache_pattern(f"content:list:{current_user.organization_id}*")
    await invalidate_cache_pattern(f"translation:*:{current_user.organization_id}*")
    await invalidate_cache_pattern(f"seo:*:{current_user.organization_id}*")

    # Publish webhook event
    background_tasks.add_task(
        publish_content_deleted_sync,
        content_id,
        org_id,
        db,
    )

    # Remove from search index
    try:
        from backend.core.search_service import search_service

        background_tasks.add_task(search_service.delete_content_entry, content_id)
    except Exception as e:
        print(f"Failed to remove from search index: {e}")


@router.post("/entries/{entry_id}/duplicate", response_model=ContentEntryResponse)
@limiter.limit(get_rate_limit())
async def duplicate_content_entry(
    request: Request,
    entry_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Duplicate/clone a content entry with all its data, translations, and relationships.
    The duplicated entry will be created as a draft with " (Copy)" appended to the title.
    """
    # Get original entry
    original_entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
        .first()
    )

    if not original_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Create new entry as copy
    new_title = f"{original_entry.title} (Copy)"
    new_slug = f"{original_entry.slug}-copy"

    # Ensure slug is unique
    counter = 1
    while db.query(ContentEntry).filter(ContentEntry.slug == new_slug).first():
        new_slug = f"{original_entry.slug}-copy-{counter}"
        counter += 1

    # Create duplicate entry
    new_entry = ContentEntry(
        content_type_id=original_entry.content_type_id,
        title=new_title,
        slug=new_slug,
        data=original_entry.data,  # Copy all field data
        status="draft",  # Always start as draft
        author_id=current_user.id,
        version=1,  # Reset version
        seo_data=original_entry.seo_data,  # Copy SEO data
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    # Copy translations if they exist
    original_translations = (
        db.query(Translation).filter(Translation.content_entry_id == original_entry.id).all()
    )

    for trans in original_translations:
        new_translation = Translation(
            content_entry_id=new_entry.id,
            locale_id=trans.locale_id,
            field_name=trans.field_name,
            translated_text=trans.translated_text,
            translation_status=trans.translation_status,
            source_text=trans.source_text,
            quality_score=trans.quality_score,
        )
        db.add(new_translation)

    db.commit()

    # Invalidate caches
    await invalidate_cache_pattern(f"content:list:{current_user.organization_id}*")

    return build_entry_response(new_entry)
