"""Content template management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import Optional

from backend.db.session import get_db
from backend.models.user import User
from backend.models.content_template import ContentTemplate
from backend.models.content import ContentType, ContentEntry
from backend.api.schemas.content_template import (
    ContentTemplateCreate,
    ContentTemplateUpdate,
    ContentTemplateResponse,
    ContentTemplateListResponse,
    ContentTemplateApply,
    ContentTemplateApplyResponse,
    TemplateStats,
)
from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import limiter, get_rate_limit
from backend.core.config import settings
from backend.core.seo_utils import generate_slug


router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=ContentTemplateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
def create_template(
    request: Request,
    template_data: ContentTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new content template.
    
    Requires 'content.manage' permission.
    """
    # Check permission
    checker = PermissionChecker(db)
    if not checker.has_permission(current_user, "content.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage templates",
        )
    
    # Verify content type exists and belongs to organization
    content_type = db.query(ContentType).filter(
        and_(
            ContentType.id == template_data.content_type_id,
            ContentType.organization_id == current_user.organization_id,
        )
    ).first()
    
    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content type not found",
        )
    
    # Check if template name already exists
    existing = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.organization_id == current_user.organization_id,
            ContentTemplate.content_type_id == template_data.content_type_id,
            ContentTemplate.name == template_data.name,
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template '{template_data.name}' already exists for this content type",
        )
    
    # Create template
    template = ContentTemplate(
        organization_id=current_user.organization_id,
        content_type_id=template_data.content_type_id,
        name=template_data.name,
        description=template_data.description,
        icon=template_data.icon,
        thumbnail_url=template_data.thumbnail_url,
        is_system_template=False,
        is_published=template_data.is_published,
        field_defaults=template_data.field_defaults,
        field_config=template_data.field_config.model_dump() if template_data.field_config else None,
        content_structure=template_data.content_structure,
        category=template_data.category,
        tags=template_data.tags,
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


@router.get("", response_model=ContentTemplateListResponse)
@limiter.limit(get_rate_limit())
def list_templates(
    request: Request,
    content_type_id: Optional[int] = Query(None, description="Filter by content type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_published: Optional[bool] = Query(None, description="Filter by published status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List content templates for the organization."""
    query = db.query(ContentTemplate).filter(
        ContentTemplate.organization_id == current_user.organization_id
    )
    
    if content_type_id is not None:
        query = query.filter(ContentTemplate.content_type_id == content_type_id)
    
    if category:
        query = query.filter(ContentTemplate.category == category)
    
    if is_published is not None:
        query = query.filter(ContentTemplate.is_published == is_published)
    
    # Count total
    total = query.count()
    
    # Paginate and sort by usage
    offset = (page - 1) * page_size
    templates = query.order_by(
        ContentTemplate.usage_count.desc(),
        ContentTemplate.created_at.desc()
    ).offset(offset).limit(page_size).all()
    
    return ContentTemplateListResponse(
        templates=templates,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{template_id}", response_model=ContentTemplateResponse)
@limiter.limit(get_rate_limit())
def get_template(
    request: Request,
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific template by ID."""
    template = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.id == template_id,
            ContentTemplate.organization_id == current_user.organization_id,
        )
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    return template


@router.patch("/{template_id}", response_model=ContentTemplateResponse)
@limiter.limit(get_rate_limit())
def update_template(
    request: Request,
    template_id: int,
    template_data: ContentTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a content template.
    
    Requires 'content.manage' permission.
    System templates cannot be updated.
    """
    # Check permission
    checker = PermissionChecker(db)
    if not checker.has_permission(current_user, "content.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage templates",
        )
    
    # Get template
    template = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.id == template_id,
            ContentTemplate.organization_id == current_user.organization_id,
        )
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Prevent updating system templates
    if template.is_system_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system templates",
        )
    
    # Update fields
    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "field_config" and value:
            setattr(template, field, {k: v.model_dump() for k, v in value.items()})
        else:
            setattr(template, field, value)
    
    db.commit()
    db.refresh(template)
    
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
def delete_template(
    request: Request,
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a content template.
    
    Requires 'content.manage' permission.
    System templates cannot be deleted.
    """
    # Check permission
    checker = PermissionChecker(db)
    if not checker.has_permission(current_user, "content.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage templates",
        )
    
    # Get template
    template = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.id == template_id,
            ContentTemplate.organization_id == current_user.organization_id,
        )
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Prevent deleting system templates
    if template.is_system_template:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system templates",
        )
    
    db.delete(template)
    db.commit()


@router.post("/apply", response_model=ContentTemplateApplyResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
def apply_template(
    request: Request,
    apply_data: ContentTemplateApply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Apply a template to create a new content entry.
    
    Creates a content entry with template defaults merged with provided overrides.
    Requires 'content.create' permission.
    """
    # Check permission
    checker = PermissionChecker(db)
    if not checker.has_permission(current_user, "content.create"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create content",
        )
    
    # Get template
    template = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.id == apply_data.template_id,
            ContentTemplate.organization_id == current_user.organization_id,
            ContentTemplate.is_published == True,
        )
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found or not published",
        )
    
    # Apply template with overrides
    merged_data = template.apply_to_entry(apply_data.overrides or {})
    
    # Generate title and slug if not provided
    title = apply_data.title or merged_data.get("title", f"New {template.name}")
    slug = apply_data.slug or generate_slug(title)
    
    # Check slug uniqueness
    existing_entry = db.query(ContentEntry).filter(
        and_(
            ContentEntry.content_type_id == template.content_type_id,
            ContentEntry.slug == slug,
        )
    ).first()
    
    if existing_entry:
        # Append timestamp to make unique
        import time
        slug = f"{slug}-{int(time.time())}"
    
    # Create content entry
    import json
    content_entry = ContentEntry(
        content_type_id=template.content_type_id,
        title=title,
        slug=slug,
        data=json.dumps(merged_data),
        status="draft",
        author_id=current_user.id,
    )
    
    db.add(content_entry)
    
    # Increment template usage
    template.increment_usage()
    
    db.commit()
    db.refresh(content_entry)
    
    return ContentTemplateApplyResponse(
        content_entry_id=content_entry.id,
        template_id=template.id,
        template_name=template.name,
        applied_data=merged_data,
        message=f"Content created successfully from template '{template.name}'",
    )


@router.get("/{template_id}/stats", response_model=TemplateStats)
@limiter.limit(get_rate_limit())
def get_template_stats(
    request: Request,
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get usage statistics for a template."""
    template = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.id == template_id,
            ContentTemplate.organization_id == current_user.organization_id,
        )
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Could track more detailed stats in future (e.g., actual content entries created)
    return TemplateStats(
        template_id=template.id,
        template_name=template.name,
        usage_count=template.usage_count,
        last_used=template.updated_at.isoformat() if template.updated_at else None,
        total_content_created=template.usage_count,  # Simplified for now
    )


@router.post("/{template_id}/duplicate", response_model=ContentTemplateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
def duplicate_template(
    request: Request,
    template_id: int,
    new_name: str = Query(..., description="Name for the duplicated template"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Duplicate an existing template.
    
    Requires 'content.manage' permission.
    """
    # Check permission
    checker = PermissionChecker(db)
    if not checker.has_permission(current_user, "content.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage templates",
        )
    
    # Get source template
    source = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.id == template_id,
            ContentTemplate.organization_id == current_user.organization_id,
        )
    ).first()
    
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    
    # Check if new name already exists
    existing = db.query(ContentTemplate).filter(
        and_(
            ContentTemplate.organization_id == current_user.organization_id,
            ContentTemplate.content_type_id == source.content_type_id,
            ContentTemplate.name == new_name,
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template '{new_name}' already exists",
        )
    
    # Duplicate template
    duplicate = ContentTemplate(
        organization_id=source.organization_id,
        content_type_id=source.content_type_id,
        name=new_name,
        description=f"Copy of {source.name}",
        icon=source.icon,
        thumbnail_url=source.thumbnail_url,
        is_system_template=False,
        is_published=source.is_published,
        field_defaults=source.field_defaults,
        field_config=source.field_config,
        content_structure=source.content_structure,
        category=source.category,
        tags=source.tags,
    )
    
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    
    return duplicate
