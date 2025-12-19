"""
API Scope management endpoints.

Allows organizations to create and manage custom permission scopes
that can be assigned to API keys.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.api_scope import ApiScope
from backend.models.user import User

router = APIRouter(prefix="/api-scopes", tags=["API Scopes"])


# Pydantic schemas
class ApiScopeCreate(BaseModel):
    """Schema for creating a new API scope"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Scope identifier (e.g., inventory.read)"
    )
    label: str = Field(..., min_length=1, max_length=200, description="Human-readable label")
    description: Optional[str] = Field(None, max_length=1000, description="Detailed description")
    category: Optional[str] = Field(None, max_length=50, description="Category for grouping")
    platform: Optional[str] = Field("custom", max_length=50, description="Platform identifier")


class ApiScopeUpdate(BaseModel):
    """Schema for updating an API scope"""

    label: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    category: Optional[str] = Field(None, max_length=50)
    platform: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class ApiScopeResponse(BaseModel):
    """Response schema for API scope"""

    id: UUID
    name: str
    label: str
    description: Optional[str]
    category: Optional[str]
    platform: Optional[str]
    is_active: bool
    is_system: bool
    organization_id: Optional[UUID]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class ApiScopeListResponse(BaseModel):
    """Response schema for listing API scopes"""

    items: List[ApiScopeResponse]
    total: int
    page: int
    page_size: int


@router.post(
    "",
    response_model=ApiScopeResponse,
    status_code=201,
    summary="Create API scope",
    description="Create a new API scope for your organization",
)
@limiter.limit(get_rate_limit())
def create_api_scope(
    request: Request,
    data: ApiScopeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new API scope."""
    # Check if scope name already exists for this organization
    existing = (
        db.query(ApiScope)
        .filter(
            ApiScope.name == data.name,
            or_(
                ApiScope.organization_id == current_user.organization_id,
                ApiScope.organization_id.is_(None),  # Global scopes
            ),
        )
        .first()
    )

    if existing:
        raise HTTPException(status_code=400, detail=f"Scope with name '{data.name}' already exists")

    scope = ApiScope(
        name=data.name,
        label=data.label,
        description=data.description,
        category=data.category,
        platform=data.platform or "custom",
        organization_id=current_user.organization_id,
        is_active=True,
        is_system=False,
    )

    db.add(scope)
    db.commit()
    db.refresh(scope)

    return ApiScopeResponse(
        id=scope.id,
        name=scope.name,
        label=scope.label,
        description=scope.description,
        category=scope.category,
        platform=scope.platform,
        is_active=scope.is_active,
        is_system=scope.is_system,
        organization_id=scope.organization_id,
        created_at=scope.created_at.isoformat() if scope.created_at else None,
        updated_at=scope.updated_at.isoformat() if scope.updated_at else None,
    )


@router.get(
    "",
    response_model=ApiScopeListResponse,
    summary="List API scopes",
    description="Get all available API scopes for your organization",
)
@limiter.limit(get_rate_limit())
def list_api_scopes(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    category: Optional[str] = Query(None, description="Filter by category"),
    include_inactive: bool = Query(False, description="Include inactive scopes"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all API scopes available to the organization."""
    query = db.query(ApiScope).filter(
        or_(
            ApiScope.organization_id == current_user.organization_id,
            ApiScope.organization_id.is_(None),  # Include global scopes
        )
    )

    if not include_inactive:
        query = query.filter(ApiScope.is_active == True)

    if platform:
        query = query.filter(ApiScope.platform == platform)

    if category:
        query = query.filter(ApiScope.category == category)

    total = query.count()

    scopes = (
        query.order_by(ApiScope.category, ApiScope.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return ApiScopeListResponse(
        items=[
            ApiScopeResponse(
                id=s.id,
                name=s.name,
                label=s.label,
                description=s.description,
                category=s.category,
                platform=s.platform,
                is_active=s.is_active,
                is_system=s.is_system,
                organization_id=s.organization_id,
                created_at=s.created_at.isoformat() if s.created_at else None,
                updated_at=s.updated_at.isoformat() if s.updated_at else None,
            )
            for s in scopes
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{scope_id}",
    response_model=ApiScopeResponse,
    summary="Get API scope",
    description="Get details of a specific API scope",
)
@limiter.limit(get_rate_limit())
def get_api_scope(
    request: Request,
    scope_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific API scope by ID."""
    scope = (
        db.query(ApiScope)
        .filter(
            ApiScope.id == scope_id,
            or_(
                ApiScope.organization_id == current_user.organization_id,
                ApiScope.organization_id.is_(None),
            ),
        )
        .first()
    )

    if not scope:
        raise HTTPException(status_code=404, detail="API scope not found")

    return ApiScopeResponse(
        id=scope.id,
        name=scope.name,
        label=scope.label,
        description=scope.description,
        category=scope.category,
        platform=scope.platform,
        is_active=scope.is_active,
        is_system=scope.is_system,
        organization_id=scope.organization_id,
        created_at=scope.created_at.isoformat() if scope.created_at else None,
        updated_at=scope.updated_at.isoformat() if scope.updated_at else None,
    )


@router.patch(
    "/{scope_id}",
    response_model=ApiScopeResponse,
    summary="Update API scope",
    description="Update an existing API scope",
)
@limiter.limit(get_rate_limit())
def update_api_scope(
    request: Request,
    scope_id: UUID,
    data: ApiScopeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an API scope."""
    scope = (
        db.query(ApiScope)
        .filter(
            ApiScope.id == scope_id,
            ApiScope.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not scope:
        raise HTTPException(status_code=404, detail="API scope not found")

    if scope.is_system:
        raise HTTPException(status_code=403, detail="Cannot modify system scopes")

    if data.label is not None:
        scope.label = data.label
    if data.description is not None:
        scope.description = data.description
    if data.category is not None:
        scope.category = data.category
    if data.platform is not None:
        scope.platform = data.platform
    if data.is_active is not None:
        scope.is_active = data.is_active

    db.commit()
    db.refresh(scope)

    return ApiScopeResponse(
        id=scope.id,
        name=scope.name,
        label=scope.label,
        description=scope.description,
        category=scope.category,
        platform=scope.platform,
        is_active=scope.is_active,
        is_system=scope.is_system,
        organization_id=scope.organization_id,
        created_at=scope.created_at.isoformat() if scope.created_at else None,
        updated_at=scope.updated_at.isoformat() if scope.updated_at else None,
    )


@router.delete(
    "/{scope_id}",
    status_code=204,
    summary="Delete API scope",
    description="Delete an API scope",
)
@limiter.limit(get_rate_limit())
def delete_api_scope(
    request: Request,
    scope_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an API scope."""
    scope = (
        db.query(ApiScope)
        .filter(
            ApiScope.id == scope_id,
            ApiScope.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not scope:
        raise HTTPException(status_code=404, detail="API scope not found")

    if scope.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system scopes")

    db.delete(scope)
    db.commit()

    return None


@router.post(
    "/seed-boutique",
    response_model=ApiScopeListResponse,
    summary="Seed Boutique Platform scopes",
    description="Create standard Boutique Platform permission scopes",
)
@limiter.limit(get_rate_limit())
def seed_boutique_scopes(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Seed the database with standard Boutique Platform scopes.
    This is a convenience endpoint to quickly set up all required scopes.
    """
    boutique_scopes = [
        # Inventory
        {
            "name": "inventory.read",
            "label": "Inventory: Read",
            "description": "View inventory items and stock levels",
            "category": "Inventory",
        },
        {
            "name": "inventory.create",
            "label": "Inventory: Create",
            "description": "Create new inventory items",
            "category": "Inventory",
        },
        {
            "name": "inventory.update",
            "label": "Inventory: Update",
            "description": "Update inventory items and stock",
            "category": "Inventory",
        },
        {
            "name": "inventory.delete",
            "label": "Inventory: Delete",
            "description": "Delete inventory items",
            "category": "Inventory",
        },
        {
            "name": "inventory.stats",
            "label": "Inventory: Stats",
            "description": "View inventory statistics",
            "category": "Inventory",
        },
        {
            "name": "inventory.reserve",
            "label": "Inventory: Reserve",
            "description": "Reserve inventory stock",
            "category": "Inventory",
        },
        {
            "name": "inventory.release",
            "label": "Inventory: Release",
            "description": "Release reserved inventory",
            "category": "Inventory",
        },
        # Orders
        {
            "name": "orders.read",
            "label": "Orders: Read",
            "description": "View orders and order details",
            "category": "Orders",
        },
        {
            "name": "orders.create",
            "label": "Orders: Create",
            "description": "Create new orders",
            "category": "Orders",
        },
        {
            "name": "orders.update",
            "label": "Orders: Update",
            "description": "Update order status and details",
            "category": "Orders",
        },
        {
            "name": "orders.cancel",
            "label": "Orders: Cancel",
            "description": "Cancel orders",
            "category": "Orders",
        },
        {
            "name": "orders.stats",
            "label": "Orders: Stats",
            "description": "View order statistics",
            "category": "Orders",
        },
        # Customers
        {
            "name": "customers.read",
            "label": "Customers: Read",
            "description": "View customer information",
            "category": "Customers",
        },
        {
            "name": "customers.create",
            "label": "Customers: Create",
            "description": "Create new customers",
            "category": "Customers",
        },
        {
            "name": "customers.update",
            "label": "Customers: Update",
            "description": "Update customer information",
            "category": "Customers",
        },
        {
            "name": "customers.delete",
            "label": "Customers: Delete",
            "description": "Delete customers",
            "category": "Customers",
        },
        # Wishlist
        {
            "name": "wishlist.read",
            "label": "Wishlist: Read",
            "description": "View wishlist items",
            "category": "Customers",
        },
        {
            "name": "wishlist.create",
            "label": "Wishlist: Create",
            "description": "Add items to wishlist",
            "category": "Customers",
        },
        {
            "name": "wishlist.delete",
            "label": "Wishlist: Delete",
            "description": "Remove items from wishlist",
            "category": "Customers",
        },
        # Addresses
        {
            "name": "addresses.read",
            "label": "Addresses: Read",
            "description": "View customer addresses",
            "category": "Customers",
        },
        {
            "name": "addresses.create",
            "label": "Addresses: Create",
            "description": "Create customer addresses",
            "category": "Customers",
        },
        {
            "name": "addresses.update",
            "label": "Addresses: Update",
            "description": "Update customer addresses",
            "category": "Customers",
        },
        {
            "name": "addresses.delete",
            "label": "Addresses: Delete",
            "description": "Delete customer addresses",
            "category": "Customers",
        },
        # Products
        {
            "name": "products.read",
            "label": "Products: Read",
            "description": "View products and catalog",
            "category": "Products",
        },
        {
            "name": "products.create",
            "label": "Products: Create",
            "description": "Create new products",
            "category": "Products",
        },
        {
            "name": "products.update",
            "label": "Products: Update",
            "description": "Update product information",
            "category": "Products",
        },
        {
            "name": "products.delete",
            "label": "Products: Delete",
            "description": "Delete products",
            "category": "Products",
        },
        # Payments
        {
            "name": "payments.read",
            "label": "Payments: Read",
            "description": "View payment information",
            "category": "Payments",
        },
        {
            "name": "payments.create",
            "label": "Payments: Create",
            "description": "Process payments",
            "category": "Payments",
        },
        {
            "name": "payments.refund",
            "label": "Payments: Refund",
            "description": "Process refunds",
            "category": "Payments",
        },
        # Shipping
        {
            "name": "shipping.read",
            "label": "Shipping: Read",
            "description": "View shipping information",
            "category": "Shipping",
        },
        {
            "name": "shipping.create",
            "label": "Shipping: Create",
            "description": "Create shipments",
            "category": "Shipping",
        },
        {
            "name": "shipping.update",
            "label": "Shipping: Update",
            "description": "Update shipment status",
            "category": "Shipping",
        },
        {
            "name": "shipping.track",
            "label": "Shipping: Track",
            "description": "Track shipments",
            "category": "Shipping",
        },
        # Admin
        {
            "name": "admin.full",
            "label": "Admin: Full Access",
            "description": "Full administrative access to all platform features",
            "category": "Admin",
        },
    ]

    created_scopes = []

    for scope_data in boutique_scopes:
        # Check if already exists
        existing = (
            db.query(ApiScope)
            .filter(
                ApiScope.name == scope_data["name"],
                or_(
                    ApiScope.organization_id == current_user.organization_id,
                    ApiScope.organization_id.is_(None),
                ),
            )
            .first()
        )

        if existing:
            created_scopes.append(existing)
            continue

        scope = ApiScope(
            name=scope_data["name"],
            label=scope_data["label"],
            description=scope_data["description"],
            category=scope_data["category"],
            platform="boutique",
            organization_id=current_user.organization_id,
            is_active=True,
            is_system=False,
        )
        db.add(scope)
        created_scopes.append(scope)

    db.commit()

    # Refresh all scopes to get IDs
    for scope in created_scopes:
        db.refresh(scope)

    return ApiScopeListResponse(
        items=[
            ApiScopeResponse(
                id=s.id,
                name=s.name,
                label=s.label,
                description=s.description,
                category=s.category,
                platform=s.platform,
                is_active=s.is_active,
                is_system=s.is_system,
                organization_id=s.organization_id,
                created_at=s.created_at.isoformat() if s.created_at else None,
                updated_at=s.updated_at.isoformat() if s.updated_at else None,
            )
            for s in created_scopes
        ],
        total=len(created_scopes),
        page=1,
        page_size=len(created_scopes),
    )
