"""
Content Preview API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.models.user import User
from backend.models.content import ContentEntry
from backend.core.dependencies import get_current_user
from backend.core.preview_service import PreviewService
from backend.api.schemas.preview import (
    PreviewTokenRequest,
    PreviewTokenResponse,
    PreviewAccessRequest,
    PreviewContentResponse
)
from backend.core.rate_limit import limiter, get_rate_limit
from backend.core.config import settings

router = APIRouter(prefix="/preview", tags=["preview"])


@router.post("/generate", response_model=PreviewTokenResponse)
@limiter.limit(get_rate_limit())
async def generate_preview_token(
    request: Request,
    preview_data: PreviewTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a signed preview token for a content entry.
    Allows sharing preview links with expiration.
    """
    # Verify content entry exists and belongs to user's organization
    result = await db.execute(
        select(ContentEntry).where(
            ContentEntry.id == preview_data.content_id,
            ContentEntry.content_type.has(organization_id=current_user.organization_id)
        )
    )
    content_entry = result.scalar_one_or_none()
    
    if not content_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content entry not found"
        )
    
    # Generate token
    token, expires_at = PreviewService.generate_preview_token(
        content_entry_id=preview_data.content_entry_id,
        organization_id=current_user.organization_id,
        expires_in_hours=preview_data.expires_in_hours
    )
    
    # Generate preview URL (using a placeholder base URL)
    # In production, this should come from settings
    base_url = "https://your-cms-domain.com"
    preview_url = PreviewService.generate_preview_url(
        base_url=base_url,
        content_entry_id=preview_data.content_entry_id,
        token=token
    )
    
    return PreviewTokenResponse(
        preview_url=preview_url,
        token=token,
        expires_at=expires_at,
        content_entry_id=preview_data.content_entry_id
    )


@router.get("/{content_entry_id}", response_model=PreviewContentResponse)
@limiter.limit(get_rate_limit())
async def access_preview_content(
    request: Request,
    content_entry_id: int,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Access content via preview token.
    Allows viewing draft content with a signed token.
    """
    # Validate token
    payload = PreviewService.validate_preview_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired preview token"
        )
    
    # Verify token matches content entry
    if payload.get("content_entry_id") != content_entry_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match content entry"
        )
    
    # Get content entry (including drafts)
    result = await db.execute(
        select(ContentEntry).where(ContentEntry.id == content_entry_id)
    )
    content_entry = result.scalar_one_or_none()
    
    if not content_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content entry not found"
        )
    
    # Verify organization matches
    # Get content type to check organization
    await db.refresh(content_entry, ["content_type"])
    if content_entry.content_type.organization_id != payload.get("organization_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized access to this content"
        )
    
    # Parse data field
    import json
    fields = json.loads(content_entry.data) if isinstance(content_entry.data, str) else content_entry.data
    
    return PreviewContentResponse(
        id=content_entry.id,
        content_type_id=content_entry.content_type_id,
        organization_id=content_entry.content_type.organization_id,
        title=content_entry.title,
        slug=content_entry.slug,
        status=content_entry.status,
        fields=fields,
        version=content_entry.version,
        created_at=content_entry.created_at,
        updated_at=content_entry.updated_at,
        published_at=content_entry.published_at,
        is_preview=True
    )
