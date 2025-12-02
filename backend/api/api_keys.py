"""
API key management endpoints.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from backend.api.schemas.api_key import (
    APIKeyCreateSchema,
    APIKeyListResponseSchema,
    APIKeyResponseSchema,
    APIKeyUpdateSchema,
    APIKeyWithSecretSchema,
)
from backend.core.dependencies import get_current_user
from backend.core.exceptions import NotFoundException
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.security import generate_api_key, hash_api_key
from backend.db.session import get_db
from backend.models.api_key import APIKey
from backend.models.user import User

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.post(
    "",
    response_model=APIKeyWithSecretSchema,
    status_code=201,
    summary="Create API key",
    description="Generate a new API key. The full key is only shown once, store it securely.",
)
@limiter.limit(get_rate_limit())
def create_api_key(
    request: Request,
    data: APIKeyCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
    key_hash = hash_api_key(key)

    # Create API key record
    api_key = APIKey(
        name=data.name,
        key_hash=key_hash,  # Store hashed key
        key_prefix=key_prefix,
        permissions=(
            ",".join(data.scopes) if data.scopes else None
        ),  # Store as comma-separated string
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
        expires_at=data.expires_at,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    # Return with full key (only time it's shown)
    scopes_list = api_key.permissions.split(",") if api_key.permissions else []

    # Convert expires_at to datetime if it's a string
    expires_at_value = api_key.expires_at
    if isinstance(expires_at_value, str):
        from dateutil import parser

        expires_at_value = parser.parse(expires_at_value)

    return APIKeyWithSecretSchema(
        id=api_key.id,
        name=api_key.name,
        key=key,  # Full key
        key_prefix=key_prefix,
        scopes=scopes_list,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=expires_at_value,
        organization_id=api_key.organization_id,
    )


@router.get(
    "",
    response_model=APIKeyListResponseSchema,
    summary="List API keys",
    description="Get paginated list of API keys for current user.",
)
@limiter.limit(get_rate_limit())
def list_api_keys(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for the current organization.

    - **page**: Page number (starting from 1)
    - **page_size**: Number of items per page (max 100)
    - **is_active**: Filter by active status (optional)

    Returns paginated list without full keys (only key_prefix).
    """
    # Build query
    query = db.query(APIKey).filter(APIKey.organization_id == current_user.organization_id)

    if is_active is not None:
        query = query.filter(APIKey.is_active == is_active)

    # Get total count
    total = query.count()

    # Get paginated results (order_by MUST come before offset/limit)
    api_keys = (
        query.order_by(APIKey.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Convert to response schema with permissions mapped to scopes
    items = []
    for key in api_keys:
        scopes_list = key.permissions.split(",") if key.permissions else []

        # Convert datetime strings if needed
        expires_at_value = key.expires_at
        if isinstance(expires_at_value, str):
            from dateutil import parser

            expires_at_value = parser.parse(expires_at_value)

        last_used_at_value = key.last_used_at
        if isinstance(last_used_at_value, str):
            from dateutil import parser

            last_used_at_value = parser.parse(last_used_at_value)

        items.append(
            APIKeyResponseSchema(
                id=key.id,
                name=key.name,
                key_prefix=key.key_prefix,
                scopes=scopes_list,
                is_active=key.is_active,
                created_at=key.created_at,
                expires_at=expires_at_value,
                last_used_at=last_used_at_value,
                organization_id=key.organization_id,
            )
        )

    return APIKeyListResponseSchema(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{key_id}",
    response_model=APIKeyResponseSchema,
    summary="Get API key",
    description="Get details of a specific API key (full key not included).",
)
@limiter.limit(get_rate_limit())
def get_api_key(
    request: Request,
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get API key details by ID.

    Returns key information without the full secret key.
    """
    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not api_key:
        raise NotFoundException(detail=f"API key with ID {key_id} not found")

    scopes_list = api_key.permissions.split(",") if api_key.permissions else []

    # Convert datetime strings if needed
    expires_at_value = api_key.expires_at
    if isinstance(expires_at_value, str):
        from dateutil import parser

        expires_at_value = parser.parse(expires_at_value)

    last_used_at_value = api_key.last_used_at
    if isinstance(last_used_at_value, str):
        from dateutil import parser

        last_used_at_value = parser.parse(last_used_at_value)

    return APIKeyResponseSchema(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=scopes_list,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=expires_at_value,
        last_used_at=last_used_at_value,
        organization_id=api_key.organization_id,
    )


@router.patch(
    "/{key_id}",
    response_model=APIKeyResponseSchema,
    summary="Update API key",
    description="Update API key name, scopes, or active status.",
)
@limiter.limit(get_rate_limit())
def update_api_key(
    request: Request,
    key_id: UUID,
    data: APIKeyUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update API key properties.

    - **name**: New descriptive name
    - **scopes**: New list of permission scopes
    - **is_active**: Enable/disable the key

    Cannot update the key itself or expiration after creation.
    """
    # Get API key
    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not api_key:
        raise NotFoundException(detail=f"API key with ID {key_id} not found")

    # Update fields
    if data.name is not None:
        api_key.name = data.name
    if data.scopes is not None:
        api_key.permissions = ",".join(data.scopes)
    if data.is_active is not None:
        api_key.is_active = data.is_active

    db.commit()
    db.refresh(api_key)

    scopes_list = api_key.permissions.split(",") if api_key.permissions else []
    return APIKeyResponseSchema(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=scopes_list,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        organization_id=api_key.organization_id,
    )

    return APIKeyResponseSchema.model_validate(api_key)


@router.post(
    "/{key_id}/permissions",
    response_model=APIKeyResponseSchema,
    summary="Add permissions to API key",
    description="Add one or more permissions to an existing API key.",
)
@limiter.limit(get_rate_limit())
def add_permissions_to_api_key(
    request: Request,
    key_id: UUID,
    permissions: list[str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add permissions to an existing API key.

    - **permissions**: List of permissions to add (e.g., ['themes.read', 'themes.manage'])

    Existing permissions are preserved, duplicates are ignored.
    """
    # Get API key
    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not api_key:
        raise NotFoundException(detail=f"API key with ID {key_id} not found")

    # Get current permissions
    current_scopes = api_key.permissions.split(",") if api_key.permissions else []

    # Add new permissions (avoiding duplicates)
    for perm in permissions:
        if perm not in current_scopes:
            current_scopes.append(perm)

    # Update API key
    api_key.permissions = ",".join(current_scopes)
    db.commit()
    db.refresh(api_key)

    return APIKeyResponseSchema(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=current_scopes,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        organization_id=api_key.organization_id,
    )


@router.delete(
    "/{key_id}",
    status_code=204,
    summary="Delete API key",
    description="Revoke and delete an API key.",
)
@limiter.limit(get_rate_limit())
def delete_api_key(
    request: Request,
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete an API key permanently.

    This action cannot be undone. Active integrations using this key will fail.
    """
    # Get API key
    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.id == key_id,
            APIKey.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not api_key:
        raise NotFoundException(detail=f"API key with ID {key_id} not found")

    db.delete(api_key)
    db.commit()

    return None
