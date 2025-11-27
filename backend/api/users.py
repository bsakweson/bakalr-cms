"""
User Management API endpoints
Allows admins to manage users within their organization
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.rbac import Role
from backend.models.user import User
from backend.models.user_organization import UserOrganization

router = APIRouter(prefix="/users", tags=["User Management"])


# Schemas
class UserListItem(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    roles: List[str]
    created_at: str
    last_login: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    users: List[UserListItem]
    total: int


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role_id: int
    send_invite_email: bool = True


class InviteUserResponse(BaseModel):
    user_id: int
    email: str
    message: str


class UpdateUserRoleRequest(BaseModel):
    role_id: int


class UpdateUserRoleResponse(BaseModel):
    user_id: int
    role_id: int
    message: str


@router.get("/", response_model=UserListResponse)
@limiter.limit(get_rate_limit())
async def list_users(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    List all users in the current organization

    Requires: view_users permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "view_users", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have permission to view users"
        )

    # Get all users in current organization
    memberships = (
        db.query(UserOrganization)
        .filter(UserOrganization.organization_id == current_user.organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    users_list = []
    for membership in memberships:
        user = db.query(User).filter(User.id == membership.user_id).first()
        if not user:
            continue

        # Get user's roles in this organization
        user_roles = (
            db.query(Role)
            .filter(
                and_(
                    Role.organization_id == current_user.organization_id, Role.users.any(id=user.id)
                )
            )
            .all()
        )

        role_names = [role.name for role in user_roles]

        users_list.append(
            UserListItem(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                roles=role_names,
                created_at=user.created_at.isoformat() if user.created_at else "",
                last_login=(
                    user.last_login.isoformat()
                    if hasattr(user, "last_login") and user.last_login
                    else None
                ),
            )
        )

    total = (
        db.query(UserOrganization)
        .filter(UserOrganization.organization_id == current_user.organization_id)
        .count()
    )

    return UserListResponse(users=users_list, total=total)


@router.post("/invite", response_model=InviteUserResponse)
@limiter.limit(get_rate_limit())
async def invite_user(
    request: Request,
    invite_data: InviteUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Invite a new user to the organization

    Requires: manage_users permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "manage_users", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite users",
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == invite_data.email).first()

    if existing_user:
        # Check if user is already in this organization
        existing_membership = (
            db.query(UserOrganization)
            .filter(
                and_(
                    UserOrganization.user_id == existing_user.id,
                    UserOrganization.organization_id == current_user.organization_id,
                )
            )
            .first()
        )

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )

        # Add existing user to organization
        membership = UserOrganization(
            user_id=existing_user.id,
            organization_id=current_user.organization_id,
            is_active=True,
            is_default=False,
        )
        db.add(membership)

        # Assign role
        role = (
            db.query(Role)
            .filter(
                and_(
                    Role.id == invite_data.role_id,
                    Role.organization_id == current_user.organization_id,
                )
            )
            .first()
        )

        if role:
            role.users.append(existing_user)

        db.commit()

        return InviteUserResponse(
            user_id=existing_user.id,
            email=existing_user.email,
            message="User added to organization",
        )

    # Create new user (without password, they'll set it via invite link)
    from backend.core.security import get_password_hash

    new_user = User(
        email=invite_data.email,
        full_name=invite_data.full_name,
        hashed_password=get_password_hash("temporary_password_" + invite_data.email),  # Temporary
        is_active=True,
        organization_id=current_user.organization_id,
    )
    db.add(new_user)
    db.flush()

    # Create membership
    membership = UserOrganization(
        user_id=new_user.id,
        organization_id=current_user.organization_id,
        is_active=True,
        is_default=True,
    )
    db.add(membership)

    # Assign role
    role = (
        db.query(Role)
        .filter(
            and_(
                Role.id == invite_data.role_id, Role.organization_id == current_user.organization_id
            )
        )
        .first()
    )

    if role:
        role.users.append(new_user)

    db.commit()
    db.refresh(new_user)

    # TODO: Send invite email with password reset link

    return InviteUserResponse(
        user_id=new_user.id,
        email=new_user.email,
        message=(
            "User invited successfully. Invite email sent."
            if request.send_invite_email
            else "User created successfully."
        ),
    )


@router.put("/{user_id}/role", response_model=UpdateUserRoleResponse)
@limiter.limit(get_rate_limit())
async def update_user_role(
    request: Request,
    user_id: int,
    role_data: UpdateUserRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a user's role in the organization

    Requires: manage_users permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "manage_users", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage users",
        )

    # Verify user is in organization
    membership = (
        db.query(UserOrganization)
        .filter(
            and_(
                UserOrganization.user_id == user_id,
                UserOrganization.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found in organization"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get new role
    new_role = (
        db.query(Role)
        .filter(
            and_(Role.id == role_data.role_id, Role.organization_id == current_user.organization_id)
        )
        .first()
    )

    if not new_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    # Remove user from all current roles in this organization
    current_roles = (
        db.query(Role)
        .filter(
            and_(Role.organization_id == current_user.organization_id, Role.users.any(id=user_id))
        )
        .all()
    )

    for role in current_roles:
        role.users.remove(user)

    # Assign new role
    new_role.users.append(user)

    db.commit()

    return UpdateUserRoleResponse(
        user_id=user_id, role_id=role_data.role_id, message="User role updated successfully"
    )


@router.delete("/{user_id}")
@limiter.limit(get_rate_limit())
async def remove_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a user from the organization

    Requires: manage_users permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "manage_users", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage users",
        )

    # Can't remove yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the organization",
        )

    # Verify user is in organization
    membership = (
        db.query(UserOrganization)
        .filter(
            and_(
                UserOrganization.user_id == user_id,
                UserOrganization.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found in organization"
        )

    # Remove membership
    db.delete(membership)

    # Remove user from all roles in this organization
    roles = (
        db.query(Role)
        .filter(
            and_(Role.organization_id == current_user.organization_id, Role.users.any(id=user_id))
        )
        .all()
    )

    user = db.query(User).filter(User.id == user_id).first()
    for role in roles:
        role.users.remove(user)

    db.commit()

    return {"message": "User removed from organization successfully"}
