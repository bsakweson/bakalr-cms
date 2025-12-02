"""
User Management API endpoints
Allows admins to manage users within their organization
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.organization import Organization
from backend.models.rbac import Role
from backend.models.user import User
from backend.models.user_organization import UserOrganization

router = APIRouter(prefix="/users", tags=["User Management"])


# Schemas
class UserListItem(BaseModel):
    id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
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
    first_name: str
    last_name: str
    role_id: UUID
    send_invite_email: bool = True


class InviteUserResponse(BaseModel):
    user_id: UUID
    email: str
    message: str


class UpdateUserRoleRequest(BaseModel):
    role_id: UUID


class UpdateUserRoleResponse(BaseModel):
    user_id: UUID
    role_id: UUID
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

    Requires: user.read permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "user.read", db):
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
                first_name=user.first_name,
                last_name=user.last_name,
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

    Requires: user.manage permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "user.manage", db):
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
    user_id: UUID,
    role_data: UpdateUserRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a user's role in the organization

    Requires: user.manage permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "user.manage", db):
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

    # Get organization to check ownership
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

    # Cannot change organization owner's role
    if organization and organization.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify organization owner's role. The owner maintains full administrative privileges.",
        )

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
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a user from the organization

    Requires: user.manage permission
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "user.manage", db):
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

    # Get organization to check ownership
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

    # Can't remove organization owner without transfer
    if organization and organization.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization owner. Please transfer ownership first.",
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


# Ownership Transfer Schema
class TransferOwnershipRequest(BaseModel):
    """Schema for transferring organization ownership"""

    new_owner_id: UUID

    model_config = ConfigDict(from_attributes=True)


class TransferOwnershipResponse(BaseModel):
    """Response schema for ownership transfer"""

    organization_id: UUID
    organization_name: str
    previous_owner_id: UUID
    new_owner_id: UUID
    new_owner_email: str
    message: str

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/transfer-ownership",
    response_model=TransferOwnershipResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(get_rate_limit("expensive_operations"))
async def transfer_ownership(
    request: Request,
    transfer_request: TransferOwnershipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Transfer organization ownership to another user.

    Only the current owner can transfer ownership.
    The new owner must:
    - Be a member of the organization
    - Have an Admin role

    Requires: Current user must be the organization owner
    """
    # Get organization
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Verify current user is the owner
    if organization.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the organization owner can transfer ownership",
        )

    # Get new owner user
    new_owner = db.query(User).filter(User.id == transfer_request.new_owner_id).first()

    if not new_owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New owner user not found",
        )

    # Verify new owner is in the organization
    if new_owner.organization_id != organization.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner must be a member of your organization",
        )

    # Verify new owner has Admin role
    admin_role = (
        db.query(Role)
        .filter(and_(Role.organization_id == organization.id, Role.name == "Admin"))
        .first()
    )

    if not admin_role or new_owner not in admin_role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New owner must have Admin role in the organization",
        )

    # Transfer ownership
    previous_owner_id = organization.owner_id
    organization.owner_id = new_owner.id
    db.commit()

    return TransferOwnershipResponse(
        organization_id=organization.id,
        organization_name=organization.name,
        previous_owner_id=previous_owner_id,
        new_owner_id=new_owner.id,
        new_owner_email=new_owner.email,
        message=f"Ownership successfully transferred to {new_owner.email}",
    )
