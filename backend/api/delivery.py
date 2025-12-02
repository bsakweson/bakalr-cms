"""
Content Delivery API - optimized endpoints for frontend consumption.
CDN-friendly with minimal payloads and edge caching support.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.delivery import (
    DeliveryContentDetailResponse,
    DeliveryContentListResponse,
    DeliveryContentResponse,
)
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.content import ContentEntry, ContentType

router = APIRouter(prefix="/delivery", tags=["delivery"])


@router.get("/content/slug/{slug}", response_model=DeliveryContentDetailResponse)
@limiter.limit(get_rate_limit())
async def get_content_by_slug(
    request: Request,
    slug: str,
    content_type: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Get published content by slug (CDN-friendly).

    Query params:
    - content_type: API ID of the content type
    """
    # Get content type first
    ct_result = await db.execute(select(ContentType).where(ContentType.api_id == content_type))
    content_type_obj = ct_result.scalar_one_or_none()

    if not content_type_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content type not found")

    # Get published content entry
    result = await db.execute(
        select(ContentEntry).where(
            ContentEntry.slug == slug,
            ContentEntry.content_type_id == content_type_obj.id,
            ContentEntry.status == "published",
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    # Set cache headers for CDN (1 hour cache)
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["CDN-Cache-Control"] = "public, max-age=86400"  # 24 hours for CDN

    # Parse fields
    fields = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
    seo_data = (
        json.loads(entry.seo_data) if entry.seo_data and isinstance(entry.seo_data, str) else {}
    )

    return DeliveryContentDetailResponse(
        id=entry.id,
        slug=entry.slug,
        title=entry.title,
        fields=fields,
        published_at=entry.published_at,
        updated_at=entry.updated_at,
        seo_title=seo_data.get("title"),
        seo_description=seo_data.get("description"),
        seo_keywords=seo_data.get("keywords"),
        canonical_url=seo_data.get("canonical_url"),
    )


@router.get("/content/{content_id}", response_model=DeliveryContentDetailResponse)
@limiter.limit(get_rate_limit())
async def get_content_by_id(
    request: Request, content_id: UUID, response: Response, db: AsyncSession = Depends(get_db)
):
    """
    Get published content by ID (CDN-friendly).
    """
    result = await db.execute(
        select(ContentEntry).where(
            ContentEntry.id == content_id, ContentEntry.status == "published"
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    # Set cache headers
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["CDN-Cache-Control"] = "public, max-age=86400"

    # Parse fields
    fields = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
    seo_data = (
        json.loads(entry.seo_data) if entry.seo_data and isinstance(entry.seo_data, str) else {}
    )

    return DeliveryContentDetailResponse(
        id=entry.id,
        slug=entry.slug,
        title=entry.title,
        fields=fields,
        published_at=entry.published_at,
        updated_at=entry.updated_at,
        seo_title=seo_data.get("title"),
        seo_description=seo_data.get("description"),
        seo_keywords=seo_data.get("keywords"),
        canonical_url=seo_data.get("canonical_url"),
    )


@router.get("/content", response_model=DeliveryContentListResponse)
@limiter.limit(get_rate_limit())
async def list_content(
    request: Request,
    content_type: str,
    page: int = 1,
    page_size: int = 20,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List published content by type (CDN-friendly).

    Query params:
    - content_type: API ID of the content type
    - page: Page number (default 1)
    - page_size: Items per page (default 20, max 100)
    """
    # Limit page size
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    # Get content type
    ct_result = await db.execute(select(ContentType).where(ContentType.api_id == content_type))
    content_type_obj = ct_result.scalar_one_or_none()

    if not content_type_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content type not found")

    # Get total count
    count_result = await db.execute(
        select(ContentEntry).where(
            ContentEntry.content_type_id == content_type_obj.id, ContentEntry.status == "published"
        )
    )
    total = len(list(count_result.scalars().all()))

    # Get paginated entries
    result = await db.execute(
        select(ContentEntry)
        .where(
            ContentEntry.content_type_id == content_type_obj.id, ContentEntry.status == "published"
        )
        .order_by(ContentEntry.published_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    entries = result.scalars().all()

    # Set cache headers
    if response:
        response.headers["Cache-Control"] = "public, max-age=1800"  # 30 minutes
        response.headers["CDN-Cache-Control"] = "public, max-age=3600"  # 1 hour for CDN

    # Build response
    items = []
    for entry in entries:
        fields = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
        items.append(
            DeliveryContentResponse(
                id=entry.id,
                slug=entry.slug,
                title=entry.title,
                fields=fields,
                published_at=entry.published_at,
                updated_at=entry.updated_at,
            )
        )

    return DeliveryContentListResponse(items=items, total=total, page=page, page_size=page_size)
