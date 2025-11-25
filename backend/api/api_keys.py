"""
API key management endpoints.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional

from backend.db.session import get_db
from backend.models.api_key import APIKey
from backend.models.user import User
from backend.core.dependencies import get_current_user
from backend.api.schemas.api_key import (
    APIKeyCreateSchema,
    APIKeyUpdateSchema,
    APIKeyResponseSchema,
    APIKeyWithSecretSchema,
    APIKeyListResponseSchema,
)
from backend.core.exceptions import NotFoundException, ForbiddenException
from backend.core.security import generate_api_key


router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post(
    "",
    response_model=APIKeyWithSecretSchema,
    status_code=201,
    summary="Create API key",
    description="Generate a new API key. The full key is only shown once, store it securely.",
)
async def create_api_key(
    data: APIKeyCreateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new API key for the current user's organization.
    
    - **name**: Descriptive name for the key
    - **scopes**: List of permission scopes (e.g., ['read:content', 'write:media'])
    - **expires_at**: Optional expiration datetime (null = never expires)
    
    **Important**: The full key is only returned once. Store it securely.
    """
    # Generate API key
    key = generate_api_key()
    key_prefix = key[:8]
    
    # Create API key record
    api_key = APIKey(
        name=data.name,
        key=key,  # Should be hashed in production
        key_prefix=key_prefix,
        scopes=data.scopes,
        organization_id=current_user.organization_id,
        expires_at=data.expires_at,
        is_active=True,
    )
    
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    
    # Return with full key (only time it's shown)
    return APIKeyWithSecretSchema(
        id=api_key.id,
        name=api_key.name,
        key=key,  # Full key
        key_prefix=key_prefix,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        organization_id=api_key.organization_id,
    )


@router.get(
    "",
    response_model=APIKeyListResponseSchema,
    summary="List API keys",
    description="Get paginated list of API keys for the current organization.",
)
async def list_api_keys(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all API keys for the current organization.
    
    - **page**: Page number (starting from 1)
    - **page_size**: Number of items per page (max 100)
    - **is_active**: Filter by active status (optional)
    
    Returns paginated list without full keys (only key_prefix).
    """
    # Build query
    query = select(APIKey).where(APIKey.organization_id == current_user.organization_id)
    
    if is_active is not None:
        query = query.where(APIKey.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.offset((page - 1) * page_size).limit(page_size).order_by(APIKey.created_at.desc())
    result = await db.execute(query)
    api_keys = result.scalars().all()
    
    return APIKeyListResponseSchema(
        items=[APIKeyResponseSchema.model_validate(key) for key in api_keys],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{key_id}",
    response_model=APIKeyResponseSchema,
    summary="Get API key",
    description="Get details of a specific API key (without full key).",
)
async def get_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get API key details by ID.
    
    Returns key information without the full secret key.
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundException(detail=f"API key with ID {key_id} not found")
    
    return APIKeyResponseSchema.model_validate(api_key)


@router.patch(
    "/{key_id}",
    response_model=APIKeyResponseSchema,
    summary="Update API key",
    description="Update API key name, scopes, or active status.",
)
async def update_api_key(
    key_id: int,
    data: APIKeyUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update API key properties.
    
    - **name**: New descriptive name
    - **scopes**: New list of permission scopes
    - **is_active**: Enable/disable the key
    
    Cannot update the key itself or expiration after creation.
    """
    # Get API key
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundException(detail=f"API key with ID {key_id} not found")
    
    # Update fields
    if data.name is not None:
        api_key.name = data.name
    if data.scopes is not None:
        api_key.scopes = data.scopes
    if data.is_active is not None:
        api_key.is_active = data.is_active
    
    await db.commit()
    await db.refresh(api_key)
    
    return APIKeyResponseSchema.model_validate(api_key)


@router.delete(
    "/{key_id}",
    status_code=204,
    summary="Delete API key",
    description="Permanently delete an API key.",
)
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an API key permanently.
    
    This action cannot be undone. Active integrations using this key will fail.
    """
    # Get API key
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise NotFoundException(detail=f"API key with ID {key_id} not found")
    
    await db.delete(api_key)
    await db.commit()
    
    return None
