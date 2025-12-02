"""
Organization settings management API endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_organization, get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.organization import Organization
from backend.models.translation import Locale
from backend.models.user import User

router = APIRouter(prefix="/organization", tags=["Organization Settings"])


# Request/Response schemas
class OrganizationProfileUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None


class OrganizationProfileResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    email: Optional[str]
    website: Optional[str]
    logo_url: Optional[str]
    is_active: bool
    plan_type: str
    created_at: str
    updated_at: str


class LocaleItem(BaseModel):
    id: UUID
    code: str
    name: str
    is_default: bool
    is_active: bool


class LocaleListResponse(BaseModel):
    locales: List[LocaleItem]
    total: int


class CreateLocaleRequest(BaseModel):
    code: str
    name: str
    is_default: bool = False
    is_active: bool = True


class UpdateLocaleRequest(BaseModel):
    name: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


@router.get("/profile", response_model=OrganizationProfileResponse)
@limiter.limit(get_rate_limit())
async def get_organization_profile(
    request: Request,
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current organization profile details
    """
    PermissionChecker.require_permission(current_user, "view_organization_settings", db)
    return OrganizationProfileResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        email=org.email,
        website=org.website,
        logo_url=org.logo_url,
        is_active=org.is_active,
        plan_type=org.plan_type,
        created_at=org.created_at.isoformat() if org.created_at else "",
        updated_at=org.updated_at.isoformat() if org.updated_at else "",
    )


@router.put("/profile", response_model=OrganizationProfileResponse)
@limiter.limit(get_rate_limit())
async def update_organization_profile(
    request: Request,
    data: OrganizationProfileUpdate,
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update organization profile details
    """
    PermissionChecker.require_permission(current_user, "manage_organization_settings", db)
    # Update fields
    if data.name is not None:
        org.name = data.name
    if data.description is not None:
        org.description = data.description
    if data.email is not None:
        org.email = data.email
    if data.website is not None:
        org.website = data.website
    if data.logo_url is not None:
        org.logo_url = data.logo_url

    db.commit()
    db.refresh(org)

    return OrganizationProfileResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        description=org.description,
        email=org.email,
        website=org.website,
        logo_url=org.logo_url,
        is_active=org.is_active,
        plan_type=org.plan_type,
        created_at=org.created_at.isoformat() if org.created_at else "",
        updated_at=org.updated_at.isoformat() if org.updated_at else "",
    )


@router.get("/locales", response_model=LocaleListResponse)
@limiter.limit(get_rate_limit())
async def list_locales(
    request: Request,
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all locales for the organization
    """
    PermissionChecker.require_permission(current_user, "view_organization_settings", db)
    locales = db.query(Locale).filter(Locale.organization_id == org.id).all()

    return LocaleListResponse(
        locales=[
            LocaleItem(
                id=locale.id,
                code=locale.code,
                name=locale.name,
                is_default=locale.is_default,
                is_active=locale.is_active,
            )
            for locale in locales
        ],
        total=len(locales),
    )


@router.post("/locales", response_model=LocaleItem)
@limiter.limit(get_rate_limit())
async def create_locale(
    request: Request,
    data: CreateLocaleRequest,
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new locale for the organization
    """
    PermissionChecker.require_permission(current_user, "manage_organization_settings", db)
    # Check if locale code already exists
    existing = (
        db.query(Locale).filter(Locale.organization_id == org.id, Locale.code == data.code).first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Locale with code '{data.code}' already exists",
        )

    # If setting as default, remove default from others
    if data.is_default:
        db.query(Locale).filter(Locale.organization_id == org.id, Locale.is_default == True).update(
            {"is_default": False}
        )

    # Create locale
    locale = Locale(
        organization_id=org.id,
        code=data.code,
        name=data.name,
        is_default=data.is_default,
        is_active=data.is_active,
    )
    db.add(locale)
    db.commit()
    db.refresh(locale)

    return LocaleItem(
        id=locale.id,
        code=locale.code,
        name=locale.name,
        is_default=locale.is_default,
        is_active=locale.is_active,
    )


@router.put("/locales/{locale_id}", response_model=LocaleItem)
@limiter.limit(get_rate_limit())
async def update_locale(
    request: Request,
    locale_id: UUID,
    data: UpdateLocaleRequest,
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a locale
    """
    PermissionChecker.require_permission(current_user, "manage_organization_settings", db)
    locale = (
        db.query(Locale).filter(Locale.id == locale_id, Locale.organization_id == org.id).first()
    )

    if not locale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locale not found")

    # If setting as default, remove default from others
    if data.is_default:
        db.query(Locale).filter(
            Locale.organization_id == org.id, Locale.is_default == True, Locale.id != locale_id
        ).update({"is_default": False})

    # Update fields
    if data.name is not None:
        locale.name = data.name
    if data.is_default is not None:
        locale.is_default = data.is_default
    if data.is_active is not None:
        locale.is_active = data.is_active

    db.commit()
    db.refresh(locale)

    return LocaleItem(
        id=locale.id,
        code=locale.code,
        name=locale.name,
        is_default=locale.is_default,
        is_active=locale.is_active,
    )


@router.delete("/locales/{locale_id}")
@limiter.limit(get_rate_limit())
async def delete_locale(
    request: Request,
    locale_id: UUID,
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a locale (cannot delete default locale)
    """
    PermissionChecker.require_permission(current_user, "manage_organization_settings", db)
    locale = (
        db.query(Locale).filter(Locale.id == locale_id, Locale.organization_id == org.id).first()
    )

    if not locale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locale not found")

    if locale.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete default locale"
        )

    db.delete(locale)
    db.commit()

    return {"message": "Locale deleted successfully"}
