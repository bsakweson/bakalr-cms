"""
SEO Management API endpoints
"""

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.schemas.seo import (
    CompleteSEOData,
    RobotsConfig,
    RobotsResponse,
    SEOAnalysis,
    SitemapEntry,
    SitemapResponse,
    SlugValidation,
    StructuredData,
)
from backend.core.dependencies import get_current_user
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.seo_utils import (
    analyze_seo,
    generate_robots_txt,
    generate_sitemap_xml,
    generate_slug,
    generate_structured_data_article,
    validate_slug,
)
from backend.db.session import get_db
from backend.models.content import ContentEntry, ContentType
from backend.models.user import User

router = APIRouter(prefix="/seo", tags=["seo"])


@router.post("/validate-slug", response_model=SlugValidation)
@limiter.limit(get_rate_limit())
async def validate_content_slug(
    request: Request,
    slug: str,
    content_type_id: Optional[UUID] = None,
    exclude_entry_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate slug format and check availability

    Args:
        slug: Slug to validate
        content_type_id: Optional content type ID to check within
        exclude_entry_id: Optional entry ID to exclude from check

    Returns:
        SlugValidation result
    """
    # Validate format
    validation = validate_slug(slug)

    if not validation.is_valid:
        return validation

    # Check availability in database
    query = (
        select(ContentEntry)
        .join(ContentEntry.content_type)
        .where(
            ContentEntry.slug == slug, ContentType.organization_id == current_user.organization_id
        )
    )

    if content_type_id:
        query = query.where(ContentEntry.content_type_id == content_type_id)

    if exclude_entry_id:
        query = query.where(ContentEntry.id != exclude_entry_id)

    existing = db.execute(query).scalar_one_or_none()

    validation.is_available = existing is None

    if not validation.is_available:
        validation.errors.append("Slug already exists")
        # Generate alternative slug
        base_slug = slug
        counter = 1
        while True:
            suggested = f"{base_slug}-{counter}"
            query = (
                select(ContentEntry)
                .join(ContentEntry.content_type)
                .where(
                    ContentEntry.slug == suggested,
                    ContentType.organization_id == current_user.organization_id,
                )
            )
            if content_type_id:
                query = query.where(ContentEntry.content_type_id == content_type_id)

            if not db.execute(query).scalar_one_or_none():
                validation.suggested_slug = suggested
                break
            counter += 1

    return validation


@router.get("/analyze/{entry_id}", response_model=SEOAnalysis)
@limiter.limit(get_rate_limit())
async def analyze_content_seo(
    request: Request,
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze SEO quality for a content entry

    Args:
        entry_id: Content entry ID

    Returns:
        SEO analysis with score and recommendations
    """
    # Get content entry
    entry = db.execute(
        select(ContentEntry)
        .join(ContentEntry.content_type)
        .where(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Parse SEO data
    seo_data = None
    if entry.seo_data:
        try:
            seo_dict = json.loads(entry.seo_data)
            seo_data = CompleteSEOData(**seo_dict)
        except Exception:
            pass

    # Analyze
    analysis = analyze_seo(seo_data)

    return analysis


@router.put("/update/{entry_id}", response_model=dict)
@limiter.limit(get_rate_limit())
async def update_content_seo(
    request: Request,
    entry_id: UUID,
    seo_data: CompleteSEOData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update SEO metadata for a content entry

    Args:
        entry_id: Content entry ID
        seo_data: Complete SEO data

    Returns:
        Success message
    """
    # Get content entry
    entry = db.execute(
        select(ContentEntry)
        .join(ContentEntry.content_type)
        .where(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Update SEO data
    entry.seo_data = json.dumps(seo_data.model_dump(exclude_none=True))
    entry.updated_at = datetime.now(timezone.utc)

    db.commit()

    return {"message": "SEO metadata updated successfully"}


@router.post("/structured-data/article/{entry_id}", response_model=StructuredData)
@limiter.limit(get_rate_limit())
async def generate_article_structured_data(
    request: Request,
    entry_id: UUID,
    author: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate Article structured data for a content entry

    Args:
        entry_id: Content entry ID
        author: Optional author name

    Returns:
        Structured data for Article
    """
    # Get content entry
    entry = db.execute(
        select(ContentEntry)
        .join(ContentEntry.content_type)
        .where(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Parse SEO data for title/description/image
    title = entry.slug.replace("-", " ").title()
    description = ""
    image = None

    if entry.seo_data:
        try:
            seo_dict = json.loads(entry.seo_data)
            if "seo" in seo_dict:
                title = seo_dict["seo"].get("title", title)
                description = seo_dict["seo"].get("description", "")
            if "open_graph" in seo_dict:
                image = seo_dict["open_graph"].get("og_image")
        except Exception:
            pass

    # Generate structured data
    structured_data = generate_structured_data_article(
        title=title,
        description=description,
        url=f"/content/{entry.slug}",
        image=image,
        author=author,
        published_at=entry.created_at,
        modified_at=entry.updated_at,
    )

    return structured_data


@router.get("/sitemap.xml")
@limiter.limit(get_rate_limit())
async def get_sitemap(
    request: Request, db: Session = Depends(get_db), base_url: str = "https://example.com"
):
    """
    Generate XML sitemap for published content

    Args:
        base_url: Base URL for the site

    Returns:
        XML sitemap
    """
    # Get all published content entries
    entries = (
        db.execute(
            select(ContentEntry)
            .join(ContentEntry.content_type)
            .where(ContentEntry.status == "published")
            .order_by(ContentEntry.updated_at.desc())
        )
        .scalars()
        .all()
    )

    # Build sitemap entries
    sitemap_entries = []
    for entry in entries:
        sitemap_entries.append(
            {
                "loc": f"{base_url}/content/{entry.slug}",
                "lastmod": entry.updated_at,
                "changefreq": "weekly",
                "priority": 0.8,  # All published content has same priority
            }
        )

    # Generate XML
    xml_content = generate_sitemap_xml(sitemap_entries)

    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": "inline; filename=sitemap.xml"},
    )


@router.get("/sitemap", response_model=SitemapResponse)
@limiter.limit(get_rate_limit())
async def get_sitemap_json(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    base_url: str = "https://example.com",
):
    """
    Get sitemap data as JSON (for preview/management)

    Args:
        base_url: Base URL for the site

    Returns:
        Sitemap entries as JSON
    """
    # Get published content entries for organization
    entries = (
        db.execute(
            select(ContentEntry)
            .join(ContentEntry.content_type)
            .where(
                ContentEntry.status == "published",
                ContentType.organization_id == current_user.organization_id,
            )
            .order_by(ContentEntry.updated_at.desc())
        )
        .scalars()
        .all()
    )

    # Build sitemap entries
    sitemap_entries = []
    for entry in entries:
        sitemap_entries.append(
            SitemapEntry(
                loc=f"{base_url}/content/{entry.slug}",
                lastmod=entry.updated_at,
                changefreq="weekly",
                priority=0.8,  # All published content has same priority
            )
        )

    return SitemapResponse(
        entries=sitemap_entries,
        total_urls=len(sitemap_entries),
        generated_at=datetime.now(timezone.utc),
    )


@router.post("/robots.txt", response_model=RobotsResponse)
@limiter.limit(get_rate_limit())
async def generate_robots(
    request: Request, config: RobotsConfig, current_user: User = Depends(get_current_user)
):
    """
    Generate robots.txt content

    Args:
        config: Robots.txt configuration

    Returns:
        Generated robots.txt content
    """
    content = generate_robots_txt(
        allow_paths=config.allow,
        disallow_paths=config.disallow,
        sitemap_urls=config.sitemap_urls,
        crawl_delay=config.crawl_delay,
        user_agent=config.user_agent,
    )

    return RobotsResponse(content=content)


@router.get("/robots.txt")
@limiter.limit(get_rate_limit())
async def get_robots(request: Request, base_url: str = "https://example.com"):
    """
    Get default robots.txt

    Args:
        base_url: Base URL for sitemap

    Returns:
        robots.txt content
    """
    content = generate_robots_txt(
        allow_paths=["/"],
        disallow_paths=["/api/", "/admin/"],
        sitemap_urls=[f"{base_url}/api/v1/seo/sitemap.xml"],
        crawl_delay=None,
        user_agent="*",
    )

    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "inline; filename=robots.txt"},
    )


@router.post("/generate-slug", response_model=dict)
@limiter.limit(get_rate_limit())
async def generate_slug_from_text(
    request: Request, text: str, current_user: User = Depends(get_current_user)
):
    """
    Generate a URL-safe slug from text

    Args:
        text: Input text

    Returns:
        Generated slug
    """
    slug = generate_slug(text)

    return {"text": text, "slug": slug}


@router.get("/meta-preview/{entry_id}", response_model=dict)
@limiter.limit(get_rate_limit())
async def preview_meta_tags(
    request: Request,
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview how meta tags will appear in search results and social media

    Args:
        entry_id: Content entry ID

    Returns:
        Preview data for different platforms
    """
    # Get content entry
    entry = db.execute(
        select(ContentEntry)
        .join(ContentEntry.content_type)
        .where(
            ContentEntry.id == entry_id, ContentType.organization_id == current_user.organization_id
        )
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Parse SEO data
    preview = {
        "google": {
            "title": entry.slug.replace("-", " ").title(),
            "description": "No description available",
            "url": f"/content/{entry.slug}",
        },
        "facebook": {
            "title": entry.slug.replace("-", " ").title(),
            "description": "No description available",
            "image": None,
        },
        "twitter": {
            "title": entry.slug.replace("-", " ").title(),
            "description": "No description available",
            "image": None,
            "card_type": "summary_large_image",
        },
    }

    if entry.seo_data:
        try:
            seo_dict = json.loads(entry.seo_data)

            # Update Google preview
            if "seo" in seo_dict:
                seo = seo_dict["seo"]
                preview["google"]["title"] = seo.get("title", preview["google"]["title"])
                preview["google"]["description"] = seo.get(
                    "description", preview["google"]["description"]
                )

            # Update Facebook preview
            if "open_graph" in seo_dict:
                og = seo_dict["open_graph"]
                preview["facebook"]["title"] = og.get("og_title", preview["facebook"]["title"])
                preview["facebook"]["description"] = og.get(
                    "og_description", preview["facebook"]["description"]
                )
                preview["facebook"]["image"] = og.get("og_image")

            # Update Twitter preview
            if "twitter" in seo_dict:
                tw = seo_dict["twitter"]
                preview["twitter"]["title"] = tw.get("twitter_title", preview["twitter"]["title"])
                preview["twitter"]["description"] = tw.get(
                    "twitter_description", preview["twitter"]["description"]
                )
                preview["twitter"]["image"] = tw.get("twitter_image")
                preview["twitter"]["card_type"] = tw.get("twitter_card", "summary_large_image")
        except Exception:
            pass

    return preview
