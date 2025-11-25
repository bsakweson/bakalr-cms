"""
Role and Permission Management API endpoints
Allows admins to manage roles and permissions within their organization
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.db.session import get_db
from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.models.user import User
from backend.models.rbac import Role, Permission
from pydantic import BaseModel


router = APIRouter(prefix="/roles", tags=["Role Management"])


# Schemas
class PermissionItem(BaseModel):
    id: int
    name: str
    description: str | None
    category: str | None
    
    class Config:
        from_attributes = True


class RoleItem(BaseModel):
    id: int
    name: str
    description: str | None
    is_system_role: bool
    level: int
    permissions: List[str] = []
    user_count: int = 0
    
    class Config:
        from_attributes = True


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
    id: int
    name: str
    description: str | None
    is_system_role: bool
    level: int
    permissions: List[PermissionItem]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=RoleListResponse)
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all roles in the current organization
    
    Requires: view_roles permission
    """
    # Check permission
    checker = PermissionChecker(db, current_user)
    if not checker.has_permission("view_roles") and not checker.has_permission("manage_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view roles"
        )
    
    # Get all roles in current organization
    roles = db.query(Role).filter(
        Role.organization_id == current_user.organization_id
    ).all()
    
    roles_list = []
    for role in roles:
        permission_names = [p.name for p in role.permissions]
        user_count = len(role.users)
        
        roles_list.append(RoleItem(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system_role=role.is_system_role,
            level=role.level,
            permissions=permission_names,
            user_count=user_count
        ))
    
    return RoleListResponse(roles=roles_list, total=len(roles_list))


@router.get("/permissions", response_model=PermissionListResponse)
async def list_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str | None = None
):
    """
    List all available permissions (for building permission matrix)
    
    Requires: manage_roles permission
    """
    # Check permission
    checker = PermissionChecker(db, current_user)
    if not checker.has_permission("manage_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view permissions"
        )
    
    # Get all permissions, optionally filtered by category
    query = db.query(Permission)
    if category:
        query = query.filter(Permission.category == category)
    
    permissions = query.all()
    
    permissions_list = [
        PermissionItem(
            id=p.id,
            name=p.name,
            description=p.description,
            category=p.category
        )
        for p in permissions
    ]
    
    return PermissionListResponse(permissions=permissions_list, total=len(permissions_list))


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific role with its permissions
    
    Requires: view_roles permission
    """
    # Check permission
    checker = PermissionChecker(db, current_user)
    if not checker.has_permission("view_roles") and not checker.has_permission("manage_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view roles"
        )
    
    # Get role
    role = db.query(Role).filter(
        and_(
            Role.id == role_id,
            Role.organization_id == current_user.organization_id
        )
    ).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    permissions_list = [
        PermissionItem(
            id=p.id,
            name=p.name,
            description=p.description,
            category=p.category
        )
        for p in role.permissions
    ]
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        level=role.level,
        permissions=permissions_list
    )


@router.post("/", response_model=RoleResponse)
async def create_role(
    request: CreateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new role in the organization
    
    Requires: manage_roles permission
    """
    # Check permission
    checker = PermissionChecker(db, current_user)
    if not checker.has_permission("manage_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to create roles"
        )
    
    # Check if role name already exists in organization
    existing_role = db.query(Role).filter(
        and_(
            Role.name == request.name,
            Role.organization_id == current_user.organization_id
        )
    ).first()
    
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{request.name}' already exists in this organization"
        )
    
    # Create new role
    new_role = Role(
        name=request.name,
        description=request.description,
        organization_id=current_user.organization_id,
        is_system_role=False,
        level=1  # Default level for custom roles
    )
    db.add(new_role)
    db.flush()
    
    # Assign permissions
    if request.permission_ids:
        permissions = db.query(Permission).filter(
            Permission.id.in_(request.permission_ids)
        ).all()
        new_role.permissions = permissions
    
    db.commit()
    db.refresh(new_role)
    
    permissions_list = [
        PermissionItem(
            id=p.id,
            name=p.name,
            description=p.description,
            category=p.category
        )
        for p in new_role.permissions
    ]
    
    return RoleResponse(
        id=new_role.id,
        name=new_role.name,
        description=new_role.description,
        is_system_role=new_role.is_system_role,
        level=new_role.level,
        permissions=permissions_list
    )


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    request: UpdateRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a role's details and permissions
    
    Requires: manage_roles permission
    """
    # Check permission
    checker = PermissionChecker(db, current_user)
    if not checker.has_permission("manage_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update roles"
        )
    
    # Get role
    role = db.query(Role).filter(
        and_(
            Role.id == role_id,
            Role.organization_id == current_user.organization_id
        )
    ).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Can't modify system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system roles"
        )
    
    # Update fields
    if request.name is not None:
        # Check if new name already exists
        existing_role = db.query(Role).filter(
            and_(
                Role.name == request.name,
                Role.organization_id == current_user.organization_id,
                Role.id != role_id
            )
        ).first()
        
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{request.name}' already exists"
            )
        
        role.name = request.name
    
    if request.description is not None:
        role.description = request.description
    
    if request.permission_ids is not None:
        permissions = db.query(Permission).filter(
            Permission.id.in_(request.permission_ids)
        ).all()
        role.permissions = permissions
    
    db.commit()
    db.refresh(role)
    
    permissions_list = [
        PermissionItem(
            id=p.id,
            name=p.name,
            description=p.description,
            category=p.category
        )
        for p in role.permissions
    ]
    
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        level=role.level,
        permissions=permissions_list
    )


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a role from the organization
    
    Requires: manage_roles permission
    """
    # Check permission
    checker = PermissionChecker(db, current_user)
    if not checker.has_permission("manage_roles"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete roles"
        )
    
    # Get role
    role = db.query(Role).filter(
        and_(
            Role.id == role_id,
            Role.organization_id == current_user.organization_id
        )
    ).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    # Can't delete system roles
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )
    
    # Check if role is assigned to any users
    if len(role.users) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role '{role.name}' because it is assigned to {len(role.users)} user(s)"
        )
    
    db.delete(role)
    db.commit()
    
    return {"message": f"Role '{role.name}' deleted successfully"}
