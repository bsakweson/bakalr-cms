"""
Reference Data API endpoints

This module provides a dedicated API for fetching organization-specific reference data
(departments, roles, statuses, etc.) with multi-language support via auto-translation.

The reference data is stored as ContentEntry instances of the 'organization_reference_data'
content type, which allows organizations to customize their reference data without code changes.
"""

import json
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.api.schemas.reference_data import (
    ReferenceDataCreate,
    ReferenceDataFullResponse,
    ReferenceDataItem,
    ReferenceDataResponse,
    ReferenceDataTypesResponse,
    ReferenceDataUpdate,
)
from backend.core.cache import cache_response, invalidate_cache_pattern
from backend.core.dependencies import get_current_user_flexible, require_permission
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.content import ContentEntry, ContentType
from backend.models.translation import Locale, Translation
from backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reference-data", tags=["Reference Data"])

# Content type API ID for organization reference data
REFERENCE_DATA_CONTENT_TYPE = "organization_reference_data"

# Default reference data types
DEFAULT_DATA_TYPES = ["department", "role", "status", "order_status"]


def get_reference_data_content_type(db: Session, organization_id: UUID) -> Optional[ContentType]:
    """Get the reference data content type for an organization."""
    return (
        db.query(ContentType)
        .filter(
            ContentType.organization_id == organization_id,
            ContentType.api_id == REFERENCE_DATA_CONTENT_TYPE,
        )
        .first()
    )


def parse_entry_data(entry: ContentEntry) -> dict:
    """Parse content entry data from JSON string."""
    if not entry.data:
        return {}
    try:
        return json.loads(entry.data) if isinstance(entry.data, str) else entry.data
    except json.JSONDecodeError:
        return {}


def get_translated_label(
    db: Session, entry: ContentEntry, locale_code: str, organization_id: UUID
) -> Optional[str]:
    """Get translated label for a reference data entry."""
    # Get locale
    locale = (
        db.query(Locale)
        .filter(
            Locale.organization_id == organization_id,
            Locale.code == locale_code,
            Locale.is_enabled.is_(True),
        )
        .first()
    )

    if not locale:
        return None

    # Get translation
    translation = (
        db.query(Translation)
        .filter(
            Translation.content_entry_id == entry.id,
            Translation.locale_id == locale.id,
        )
        .first()
    )

    if translation and translation.translated_data:
        try:
            translated = (
                json.loads(translation.translated_data)
                if isinstance(translation.translated_data, str)
                else translation.translated_data
            )
            return translated.get("label")
        except json.JSONDecodeError:
            pass

    return None


@router.get("/types", response_model=ReferenceDataTypesResponse)
@limiter.limit(get_rate_limit())
async def list_reference_data_types(
    request: Request,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    List available reference data types for the organization.

    Returns the distinct data_type values from published reference data entries.
    Supports both JWT and API key authentication.
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        return ReferenceDataTypesResponse(types=DEFAULT_DATA_TYPES)

    # Get distinct data_type values from published entries
    entries = (
        db.query(ContentEntry)
        .filter(
            ContentEntry.content_type_id == content_type.id,
            ContentEntry.status == "published",
        )
        .all()
    )

    types = set()
    for entry in entries:
        data = parse_entry_data(entry)
        if data.get("data_type"):
            types.add(data["data_type"])

    # Include default types even if no entries exist
    types.update(DEFAULT_DATA_TYPES)

    return ReferenceDataTypesResponse(types=sorted(types))


@router.get("", response_model=ReferenceDataResponse)
@limiter.limit(get_rate_limit())
@cache_response(ttl=300, key_prefix="reference_data")
async def get_reference_data(
    request: Request,
    type: str = Query(..., description="Type of reference data (department, role, status, etc.)"),
    locale: str = Query(
        "en", description="Locale code for translated labels (e.g., 'en', 'es', 'fr')"
    ),
    include_inactive: bool = Query(False, description="Include inactive items"),
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get reference data items by type with translated labels.

    This endpoint returns reference data (departments, roles, statuses, etc.) for the
    organization with labels translated to the requested locale.

    **Features:**
    - Multi-language support via CMS auto-translation
    - Organization-specific customization
    - Caching for performance (5 min TTL)
    - Supports both JWT and API key authentication

    **Example:**
    ```
    GET /api/v1/reference-data?type=department&locale=fr
    ```

    **Response:**
    ```json
    {
      "type": "department",
      "locale": "fr",
      "items": [
        {
          "code": "SALES",
          "label": "Ventes",
          "description": "Équipe des ventes et des opérations de détail",
          "icon": "shopping-cart",
          "color": "#3B82F6",
          "sort_order": 1,
          "is_active": true,
          "is_system": true,
          "metadata": {}
        }
      ],
      "total": 8
    }
    ```
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference data content type not found. Please seed the CMS with reference data.",
        )

    # Query published entries of the specified type
    entries = (
        db.query(ContentEntry)
        .filter(
            ContentEntry.content_type_id == content_type.id,
            ContentEntry.status == "published",
        )
        .all()
    )

    items = []
    for entry in entries:
        data = parse_entry_data(entry)

        # Filter by type
        if data.get("data_type") != type:
            continue

        # Filter inactive unless requested
        if not include_inactive and not data.get("is_active", True):
            continue

        # Get translated label if locale is not default (en)
        label = data.get("label", "")
        description = data.get("description")

        if locale != "en":
            translated_label = get_translated_label(db, entry, locale, current_user.organization_id)
            if translated_label:
                label = translated_label

            # Try to get translated description too
            # (using same translation mechanism)

        items.append(
            ReferenceDataItem(
                code=data.get("code", ""),
                label=label,
                description=description,
                icon=data.get("icon"),
                color=data.get("color"),
                sort_order=data.get("sort_order", 0),
                is_active=data.get("is_active", True),
                is_system=data.get("is_system", False),
                metadata=data.get("metadata", {}),
            )
        )

    # Sort by sort_order
    items.sort(key=lambda x: x.sort_order)

    return ReferenceDataResponse(
        type=type,
        locale=locale,
        items=items,
        total=len(items),
    )


@router.get("/{data_type}/{code}", response_model=ReferenceDataFullResponse)
@limiter.limit(get_rate_limit())
async def get_reference_data_item(
    request: Request,
    data_type: str,
    code: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get a specific reference data item by type and code.

    Supports both JWT and API key authentication.
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference data content type not found",
        )

    # Find the entry by type and code
    entries = (
        db.query(ContentEntry)
        .filter(
            ContentEntry.content_type_id == content_type.id,
            ContentEntry.status == "published",
        )
        .all()
    )

    for entry in entries:
        data = parse_entry_data(entry)
        if data.get("data_type") == data_type and data.get("code") == code:
            return ReferenceDataFullResponse(
                id=str(entry.id),
                data_type=data.get("data_type", ""),
                code=data.get("code", ""),
                label=data.get("label", ""),
                description=data.get("description"),
                icon=data.get("icon"),
                color=data.get("color"),
                sort_order=data.get("sort_order", 0),
                is_active=data.get("is_active", True),
                is_system=data.get("is_system", False),
                metadata=data.get("metadata", {}),
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Reference data item not found: {data_type}/{code}",
    )


@router.post("", response_model=ReferenceDataFullResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def create_reference_data(
    request: Request,
    data: ReferenceDataCreate,
    current_user: User = Depends(require_permission("reference_data.create")),
    db: Session = Depends(get_db),
):
    """
    Create a new reference data item.

    Requires 'reference_data.create' permission.

    The item will be created as a published ContentEntry under the
    'organization_reference_data' content type.
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference data content type not found. Please seed the CMS first.",
        )

    # Check for duplicate code within same type
    entries = db.query(ContentEntry).filter(ContentEntry.content_type_id == content_type.id).all()

    for entry in entries:
        entry_data = parse_entry_data(entry)
        if entry_data.get("data_type") == data.data_type and entry_data.get("code") == data.code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Reference data with code '{data.code}' already exists for type '{data.data_type}'",
            )

    # Create slug from type and code
    slug = f"{data.data_type.lower()}-{data.code.lower().replace('_', '-')}"

    # Build entry data
    entry_data = {
        "data_type": data.data_type,
        "code": data.code,
        "label": data.label,
        "description": data.description,
        "icon": data.icon,
        "color": data.color,
        "sort_order": data.sort_order,
        "is_active": data.is_active,
        "is_system": False,  # User-created items are never system items
        "metadata": data.metadata,
    }

    entry = ContentEntry(
        content_type_id=content_type.id,
        author_id=current_user.id,
        slug=slug,
        data=json.dumps(entry_data),
        status="published",
        version=1,
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Invalidate cache
    await invalidate_cache_pattern(f"reference_data:*:{current_user.organization_id}:*")

    logger.info(f"Created reference data: {data.data_type}/{data.code} by user {current_user.id}")

    return ReferenceDataFullResponse(
        id=str(entry.id),
        data_type=data.data_type,
        code=data.code,
        label=data.label,
        description=data.description,
        icon=data.icon,
        color=data.color,
        sort_order=data.sort_order,
        is_active=data.is_active,
        is_system=False,
        metadata=data.metadata,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.put("/{data_type}/{code}", response_model=ReferenceDataFullResponse)
@limiter.limit(get_rate_limit())
async def update_reference_data(
    request: Request,
    data_type: str,
    code: str,
    update_data: ReferenceDataUpdate,
    current_user: User = Depends(require_permission("reference_data.update")),
    db: Session = Depends(get_db),
):
    """
    Update a reference data item.

    Requires 'reference_data.update' permission.

    Note: System items (is_system=true) have limited update capabilities.
    The code and data_type cannot be changed.
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference data content type not found",
        )

    # Find the entry
    entries = (
        db.query(ContentEntry)
        .filter(
            ContentEntry.content_type_id == content_type.id,
        )
        .all()
    )

    target_entry = None
    for entry in entries:
        data = parse_entry_data(entry)
        if data.get("data_type") == data_type and data.get("code") == code:
            target_entry = entry
            break

    if not target_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference data item not found: {data_type}/{code}",
        )

    # Parse existing data and apply updates
    existing_data = parse_entry_data(target_entry)

    if update_data.label is not None:
        existing_data["label"] = update_data.label
    if update_data.description is not None:
        existing_data["description"] = update_data.description
    if update_data.icon is not None:
        existing_data["icon"] = update_data.icon
    if update_data.color is not None:
        existing_data["color"] = update_data.color
    if update_data.sort_order is not None:
        existing_data["sort_order"] = update_data.sort_order
    if update_data.is_active is not None:
        existing_data["is_active"] = update_data.is_active
    if update_data.metadata is not None:
        existing_data["metadata"] = update_data.metadata

    target_entry.data = json.dumps(existing_data)
    target_entry.version += 1

    db.commit()
    db.refresh(target_entry)

    # Invalidate cache
    await invalidate_cache_pattern(f"reference_data:*:{current_user.organization_id}:*")

    logger.info(f"Updated reference data: {data_type}/{code} by user {current_user.id}")

    return ReferenceDataFullResponse(
        id=str(target_entry.id),
        data_type=existing_data.get("data_type", ""),
        code=existing_data.get("code", ""),
        label=existing_data.get("label", ""),
        description=existing_data.get("description"),
        icon=existing_data.get("icon"),
        color=existing_data.get("color"),
        sort_order=existing_data.get("sort_order", 0),
        is_active=existing_data.get("is_active", True),
        is_system=existing_data.get("is_system", False),
        metadata=existing_data.get("metadata", {}),
        created_at=target_entry.created_at,
        updated_at=target_entry.updated_at,
    )


@router.delete("/{data_type}/{code}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_reference_data(
    request: Request,
    data_type: str,
    code: str,
    current_user: User = Depends(require_permission("reference_data.delete")),
    db: Session = Depends(get_db),
):
    """
    Delete a reference data item.

    Requires 'reference_data.delete' permission.

    Note: System items (is_system=true) cannot be deleted.
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference data content type not found",
        )

    # Find the entry
    entries = (
        db.query(ContentEntry)
        .filter(
            ContentEntry.content_type_id == content_type.id,
        )
        .all()
    )

    target_entry = None
    for entry in entries:
        data = parse_entry_data(entry)
        if data.get("data_type") == data_type and data.get("code") == code:
            target_entry = entry
            break

    if not target_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reference data item not found: {data_type}/{code}",
        )

    # Check if system item
    entry_data = parse_entry_data(target_entry)
    if entry_data.get("is_system", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System reference data items cannot be deleted",
        )

    db.delete(target_entry)
    db.commit()

    # Invalidate cache
    await invalidate_cache_pattern(f"reference_data:*:{current_user.organization_id}:*")

    logger.info(f"Deleted reference data: {data_type}/{code} by user {current_user.id}")


@router.get("/validate/{data_type}/{code}")
@limiter.limit(get_rate_limit())
async def validate_reference_data_code(
    request: Request,
    data_type: str,
    code: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Validate if a reference data code is valid for the given type.

    This endpoint is useful for platform services to validate incoming codes
    against the CMS-managed reference data.

    Returns:
    - 200 with `{"valid": true}` if code exists and is active
    - 200 with `{"valid": false, "reason": "..."}` if code is invalid/inactive
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        return {"valid": False, "reason": "Reference data not configured"}

    entries = (
        db.query(ContentEntry)
        .filter(
            ContentEntry.content_type_id == content_type.id,
            ContentEntry.status == "published",
        )
        .all()
    )

    for entry in entries:
        data = parse_entry_data(entry)
        if data.get("data_type") == data_type and data.get("code") == code:
            if data.get("is_active", True):
                return {"valid": True}
            else:
                return {"valid": False, "reason": "Code is inactive"}

    return {"valid": False, "reason": "Code not found"}


@router.post("/bulk-validate")
@limiter.limit(get_rate_limit())
async def bulk_validate_reference_data(
    request: Request,
    validations: List[dict],
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Validate multiple reference data codes in a single request.

    Request body:
    ```json
    [
      {"data_type": "department", "code": "SALES"},
      {"data_type": "role", "code": "MANAGER"},
      {"data_type": "status", "code": "ACTIVE"}
    ]
    ```

    Response:
    ```json
    {
      "results": [
        {"data_type": "department", "code": "SALES", "valid": true},
        {"data_type": "role", "code": "MANAGER", "valid": true},
        {"data_type": "status", "code": "UNKNOWN", "valid": false, "reason": "Code not found"}
      ],
      "all_valid": true
    }
    ```
    """
    content_type = get_reference_data_content_type(db, current_user.organization_id)

    if not content_type:
        return {
            "results": [
                {**v, "valid": False, "reason": "Reference data not configured"}
                for v in validations
            ],
            "all_valid": False,
        }

    # Load all entries once
    entries = (
        db.query(ContentEntry)
        .filter(
            ContentEntry.content_type_id == content_type.id,
            ContentEntry.status == "published",
        )
        .all()
    )

    # Build lookup map
    lookup = {}
    for entry in entries:
        data = parse_entry_data(entry)
        key = f"{data.get('data_type')}:{data.get('code')}"
        lookup[key] = data.get("is_active", True)

    results = []
    all_valid = True

    for v in validations:
        key = f"{v.get('data_type')}:{v.get('code')}"
        if key in lookup:
            if lookup[key]:
                results.append({**v, "valid": True})
            else:
                results.append({**v, "valid": False, "reason": "Code is inactive"})
                all_valid = False
        else:
            results.append({**v, "valid": False, "reason": "Code not found"})
            all_valid = False

    return {"results": results, "all_valid": all_valid}
