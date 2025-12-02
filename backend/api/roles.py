"""
Role and Permission Management API endpoints
Allows admins to manage roles and permissions within their organization
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.rbac import Permission, Role
from backend.models.user import User

router = APIRouter(prefix="/roles", tags=["Role Management"])


# Schemas
class PermissionItem(BaseModel):
    id: UUID
    name: str
    description: str | None
    category: str | None

    model_config = ConfigDict(from_attributes=True)


class RoleItem(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system_role: bool
    level: int
    permissions: List[str] = []
    user_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class RoleListResponse(BaseModel):
    roles: List[RoleItem]
    total: int


class PermissionListResponse(BaseModel):
    permissions: List[PermissionItem]
    total: int


class CreateRoleRequest(BaseModel):
    name: str
    description: str | None = None
    permission_ids: List[int] = []


class UpdateRoleRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_ids: List[int] | None = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system_role: bool
    level: int
    permissions: List[PermissionItem]

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=RoleListResponse)
@limiter.limit(get_rate_limit())
async def list_roles(
    request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    List all roles in the current organization

    Requires: view_roles permission
    """
    # Check permission
    if not PermissionChecker.has_permission(
        current_user, "view_roles", db
    ) and not PermissionChecker.has_permission(current_user, "manage_roles", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view roles"
        )

    # Get all roles in current organization
    roles = db.query(Role).filter(Role.organization_id == current_user.organization_id).all()

    roles_list = []
    for role in roles:
        permission_names = [p.name for p in role.permissions]
        user_count = len(role.users)

        roles_list.append(
            RoleItem(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system_role=role.is_system_role,
                level=role.level,
                permissions=permission_names,
                user_count=user_count,
            )
        )

    return RoleListResponse(roles=roles_list, total=len(roles_list))


@router.get("/permissions", response_model=PermissionListResponse)
@limiter.limit(get_rate_limit())
async def list_permissions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str | None = None,
):
    """
    List all available permissions (for building permission matrix)

    Requires: manage_roles permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "manage_roles", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view permissions",
        )

    # Get all permissions, optionally filtered by category
    query = db.query(Permission)
    if category:
        query = query.filter(Permission.category == category)

    permissions = query.all()

    permissions_list = [
        PermissionItem(id=p.id, name=p.name, description=p.description, category=p.category)
        for p in permissions
    ]

    return PermissionListResponse(permissions=permissions_list, total=len(permissions_list))


@router.get("/{role_id}", response_model=RoleResponse)
@limiter.limit(get_rate_limit())
async def get_role(
    request: Request,
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific role with its permissions

    Requires: view_roles permission
    """
    # Check permission
    if not PermissionChecker.has_permission(
        current_user, "view_roles", db
    ) and not PermissionChecker.has_permission(current_user, "manage_roles", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view roles"
        )

    # Get role
    role = (
        db.query(Role)
        .filter(and_(Role.id == role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    permissions_list = [
        PermissionItem(id=p.id, name=p.name, description=p.description, category=p.category)
        for p in role.permissions
    ]

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        level=role.level,
        permissions=permissions_list,
    )


@router.post("/", response_model=RoleResponse)
@limiter.limit(get_rate_limit())
async def create_role(
    request: Request,
    role_data: CreateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new role in the organization

    Requires: manage_roles permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "manage_roles", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create roles",
        )

    # Check if role name already exists in organization
    existing_role = (
        db.query(Role)
        .filter(
            and_(Role.name == role_data.name, Role.organization_id == current_user.organization_id)
        )
        .first()
    )

    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_data.name}' already exists in this organization",
        )

    # Create new role
    new_role = Role(
        name=role_data.name,
        description=role_data.description,
        organization_id=current_user.organization_id,
        is_system_role=False,
        level=1,  # Default level for custom roles
    )
    db.add(new_role)
    db.flush()

    # Assign permissions
    if role_data.permission_ids:
        permissions = db.query(Permission).filter(Permission.id.in_(role_data.permission_ids)).all()
        new_role.permissions = permissions

    db.commit()
    db.refresh(new_role)

    permissions_list = [
        PermissionItem(id=p.id, name=p.name, description=p.description, category=p.category)
        for p in new_role.permissions
    ]

    return RoleResponse(
        id=new_role.id,
        name=new_role.name,
        description=new_role.description,
        is_system_role=new_role.is_system_role,
        level=new_role.level,
        permissions=permissions_list,
    )


@router.put("/{role_id}", response_model=RoleResponse)
@limiter.limit(get_rate_limit())
async def update_role(
    request: Request,
    role_id: UUID,
    role_data: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a role's details and permissions

    Requires: manage_roles permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "manage_roles", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update roles",
        )

    # Get role
    role = (
        db.query(Role)
        .filter(and_(Role.id == role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Can't modify system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify system roles"
        )

    # Update fields
    if role_data.name is not None:
        # Check if new name already exists
        existing_role = (
            db.query(Role)
            .filter(
                and_(
                    Role.name == role_data.name,
                    Role.organization_id == current_user.organization_id,
                    Role.id != role_id,
                )
            )
            .first()
        )

        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_data.name}' already exists",
            )

        role.name = role_data.name

    if role_data.description is not None:
        role.description = role_data.description

    if role_data.permission_ids is not None:
        permissions = db.query(Permission).filter(Permission.id.in_(role_data.permission_ids)).all()
        role.permissions = permissions

    db.commit()
    db.refresh(role)

    permissions_list = [
        PermissionItem(id=p.id, name=p.name, description=p.description, category=p.category)
        for p in role.permissions
    ]

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        level=role.level,
        permissions=permissions_list,
    )


@router.delete("/{role_id}")
@limiter.limit(get_rate_limit())
async def delete_role(
    request: Request,
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a role from the organization

    Requires: manage_roles permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "manage_roles", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete roles",
        )

    # Get role
    role = (
        db.query(Role)
        .filter(and_(Role.id == role_id, Role.organization_id == current_user.organization_id))
        .first()
    )

    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Can't delete system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete system roles"
        )

    # Check if role is assigned to any users
    if len(role.users) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role '{role.name}' because it is assigned to {len(role.users)} user(s)",
        )

    db.delete(role)
    db.commit()

    return {"message": f"Role '{role.name}' deleted successfully"}
