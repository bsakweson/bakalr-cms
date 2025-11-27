"""
Field-level and content type-specific permission management endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.api.schemas.field_permissions import (
    AccessibleFieldsResponse,
    ContentTypePermissionCreate,
    FieldPermissionBulkCreate,
    FieldPermissionCreate,
    FieldPermissionResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionResponse,
)
from backend.core.dependencies import get_current_user, get_db
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.models.content import ContentType
from backend.models.rbac import Permission, Role
from backend.models.user import User

router = APIRouter(prefix="/permissions", tags=["Field Permissions"])


@router.post("/field", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def create_field_permission(
    request: Request,
    data: FieldPermissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a field-level permission for a role.

    Allows granting specific permissions to individual fields within a content type.
    Example: Allow "Editor" role to edit "title" and "body" but not "price" field.
    """
    # Verify user has permission to manage roles
    PermissionChecker.require_permission(current_user, "roles.manage", db)

    # Verify role exists and belongs to user's organization
    role = (
        db.query(Role)
        .filter(and_(Role.id == data.role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Verify content type exists and belongs to user's organization
    content_type = (
        db.query(ContentType)
        .filter(
            and_(
                ContentType.id == data.content_type_id,
                ContentType.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=404, detail="Content type not found")

    # Check if permission already exists
    existing = (
        db.query(Permission)
        .filter(
            and_(
                Permission.name == data.permission_name,
                Permission.content_type_id == data.content_type_id,
                Permission.field_name == data.field_name,
            )
        )
        .first()
    )

    if existing:
        # Add permission to role if not already assigned
        if existing not in role.permissions:
            role.permissions.append(existing)
            db.commit()
        return existing

    # Create new field-level permission
    permission = Permission(
        name=data.permission_name,
        description=data.description
        or f"Field permission: {data.field_name} in {content_type.name}",
        category="content",
        resource_type="content_entry",
        content_type_id=data.content_type_id,
        field_name=data.field_name,
    )

    db.add(permission)
    db.flush()

    # Assign to role
    role.permissions.append(permission)
    db.commit()
    db.refresh(permission)

    return permission


@router.post(
    "/field/bulk", response_model=List[PermissionResponse], status_code=status.HTTP_201_CREATED
)
@limiter.limit(get_rate_limit())
async def create_field_permissions_bulk(
    request: Request,
    data: FieldPermissionBulkCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create multiple field-level permissions at once.

    Efficient way to grant permissions to multiple fields in a single request.
    """
    # Verify user has permission to manage roles
    PermissionChecker.require_permission(current_user, "roles.manage", db)

    # Verify role exists and belongs to user's organization
    role = (
        db.query(Role)
        .filter(and_(Role.id == data.role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Verify content type exists
    content_type = (
        db.query(ContentType)
        .filter(
            and_(
                ContentType.id == data.content_type_id,
                ContentType.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=404, detail="Content type not found")

    created_permissions = []

    for field_name in data.field_names:
        # Check if permission exists
        existing = (
            db.query(Permission)
            .filter(
                and_(
                    Permission.name == data.permission_name,
                    Permission.content_type_id == data.content_type_id,
                    Permission.field_name == field_name,
                )
            )
            .first()
        )

        if existing:
            if existing not in role.permissions:
                role.permissions.append(existing)
            created_permissions.append(existing)
        else:
            # Create new permission
            permission = Permission(
                name=data.permission_name,
                description=f"Field permission: {field_name} in {content_type.name}",
                category="content",
                resource_type="content_entry",
                content_type_id=data.content_type_id,
                field_name=field_name,
            )

            db.add(permission)
            db.flush()

            role.permissions.append(permission)
            created_permissions.append(permission)

    db.commit()

    for perm in created_permissions:
        db.refresh(perm)

    return created_permissions


@router.post(
    "/content-type", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(get_rate_limit())
async def create_content_type_permission(
    request: Request,
    data: ContentTypePermissionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a content type-specific permission.

    Grants permission for an entire content type (all fields).
    Example: Allow "Product Manager" role to manage all "Product" content.
    """
    # Verify user has permission to manage roles
    PermissionChecker.require_permission(current_user, "roles.manage", db)

    # Verify role exists
    role = (
        db.query(Role)
        .filter(and_(Role.id == data.role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Verify content type exists
    content_type = (
        db.query(ContentType)
        .filter(
            and_(
                ContentType.id == data.content_type_id,
                ContentType.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=404, detail="Content type not found")

    # Check if permission exists (content type-specific, no field restriction)
    existing = (
        db.query(Permission)
        .filter(
            and_(
                Permission.name == data.permission_name,
                Permission.content_type_id == data.content_type_id,
                Permission.field_name.is_(None),
            )
        )
        .first()
    )

    if existing:
        if existing not in role.permissions:
            role.permissions.append(existing)
            db.commit()
        return existing

    # Create new content type-specific permission
    permission = Permission(
        name=data.permission_name,
        description=data.description or f"Content type permission: {content_type.name}",
        category="content",
        resource_type="content_entry",
        content_type_id=data.content_type_id,
        field_name=None,  # NULL = applies to all fields
    )

    db.add(permission)
    db.flush()

    role.permissions.append(permission)
    db.commit()
    db.refresh(permission)

    return permission


@router.get("/role/{role_id}/fields", response_model=List[FieldPermissionResponse])
@limiter.limit(get_rate_limit())
async def get_role_field_permissions(
    request: Request,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all field-level permissions for a role.

    Returns permissions with content type and field details.
    """
    # Verify role exists and belongs to user's organization
    role = (
        db.query(Role)
        .filter(and_(Role.id == role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Get field-level permissions (where field_name is not NULL)
    field_permissions = []

    for permission in role.permissions:
        if permission.field_name and permission.content_type_id:
            content_type = (
                db.query(ContentType).filter(ContentType.id == permission.content_type_id).first()
            )

            if content_type:
                field_permissions.append(
                    FieldPermissionResponse(
                        permission=permission,
                        content_type_name=content_type.name,
                        field_name=permission.field_name,
                    )
                )

    return field_permissions


@router.get("/accessible-fields/{content_type_id}", response_model=AccessibleFieldsResponse)
@limiter.limit(get_rate_limit())
async def get_accessible_fields(
    request: Request,
    content_type_id: int,
    permission_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of fields user can access for a content type.

    Returns both accessible and restricted fields.
    """
    # Verify content type exists
    content_type = (
        db.query(ContentType)
        .filter(
            and_(
                ContentType.id == content_type_id,
                ContentType.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not content_type:
        raise HTTPException(status_code=404, detail="Content type not found")

    # Get all field names from content type schema
    import json

    schema = (
        json.loads(content_type.schema)
        if isinstance(content_type.schema, str)
        else content_type.schema
    )
    all_fields = list(schema.get("fields", {}).keys())

    # Get accessible fields
    accessible = PermissionChecker.get_accessible_fields(
        current_user, permission_name, content_type_id, all_fields, db
    )

    restricted = [f for f in all_fields if f not in accessible]

    return AccessibleFieldsResponse(
        content_type_id=content_type_id,
        content_type_name=content_type.name,
        permission_name=permission_name,
        accessible_fields=accessible,
        restricted_fields=restricted,
    )


@router.post("/check", response_model=PermissionCheckResponse)
@limiter.limit(get_rate_limit())
async def check_field_permission(
    request: Request,
    permission_request: PermissionCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if current user has permission for specific fields.

    Useful for frontend to determine which fields to show/hide.
    """
    accessible = []
    denied = []

    for field_name in permission_request.field_names:
        has_perm = PermissionChecker.has_field_permission(
            current_user,
            permission_request.permission_name,
            permission_request.content_type_id,
            field_name,
            db,
        )

        if has_perm:
            accessible.append(field_name)
        else:
            denied.append(field_name)

    return PermissionCheckResponse(
        has_permission=len(denied) == 0, accessible_fields=accessible, denied_fields=denied
    )


@router.delete("/field/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def revoke_field_permission(
    request: Request,
    permission_id: int,
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke a field-level permission from a role.
    """
    # Verify user has permission to manage roles
    PermissionChecker.require_permission(current_user, "roles.manage", db)

    # Verify role exists
    role = (
        db.query(Role)
        .filter(and_(Role.id == role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Find permission
    permission = db.query(Permission).filter(Permission.id == permission_id).first()

    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    # Remove permission from role
    if permission in role.permissions:
        role.permissions.remove(permission)
        db.commit()

    return None
