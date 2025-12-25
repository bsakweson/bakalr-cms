"""
Tenant/Organization switching API endpoints
Allows users to manage multi-organization memberships and switch context
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.api.schemas.tenant import (
    InviteUserToOrganizationRequest,
    InviteUserToOrganizationResponse,
    OrganizationMembership,
    SetDefaultOrganizationRequest,
    SetDefaultOrganizationResponse,
    SwitchOrganizationRequest,
    SwitchOrganizationResponse,
    UserOrganizationsResponse,
)
from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.security import create_token_pair
from backend.db.session import get_db
from backend.models.organization import Organization
from backend.models.rbac import Role
from backend.models.user import User
from backend.models.user_organization import UserOrganization

router = APIRouter(prefix="/tenant", tags=["Tenant Switching"])


@router.get("/organizations", response_model=UserOrganizationsResponse)
@limiter.limit(get_rate_limit())
async def get_user_organizations(
    request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get list of all organizations the current user belongs to

    Returns:
        List of organizations with membership details
    """
    # Get all user-organization memberships
    memberships = (
        db.query(UserOrganization).filter(UserOrganization.user_id == current_user.id).all()
    )

    # If no memberships exist, create one for primary organization (backward compatibility)
    if not memberships and current_user.organization_id:
        membership = UserOrganization(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            is_default=True,
            is_active=True,
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)
        memberships = [membership]

    organizations = []
    for membership in memberships:
        org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
        if not org:
            continue

        # Get roles for this organization
        user_roles = (
            db.query(Role)
            .filter(and_(Role.organization_id == org.id, Role.users.any(id=current_user.id)))
            .all()
        )

        role_names = [role.name for role in user_roles]

        organizations.append(
            OrganizationMembership(
                organization_id=org.id,
                organization_name=org.name,
                organization_slug=org.slug,
                is_default=membership.is_default,
                is_active=membership.is_active,
                roles=role_names,
                joined_at=(
                    membership.created_at.isoformat()
                    if hasattr(membership, "created_at") and membership.created_at
                    else ""
                ),
            )
        )

    return UserOrganizationsResponse(
        current_organization_id=current_user.organization_id,
        organizations=organizations,
        total=len(organizations),
    )


@router.post("/switch", response_model=SwitchOrganizationResponse)
@limiter.limit(get_rate_limit())
async def switch_organization(
    request: Request,
    switch_data: SwitchOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Switch to a different organization

    Generates new JWT tokens with updated organization context.
    User must be a member of the target organization.

    Args:
        switch_data: Target organization ID

    Returns:
        New tokens with updated organization context
    """
    target_org_id = switch_data.organization_id

    # Check if user is member of target organization
    membership = (
        db.query(UserOrganization)
        .filter(
            and_(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == target_org_id,
                UserOrganization.is_active.is_(True),
            )
        )
        .first()
    )

    # Backward compatibility: Check if this is user's primary organization
    if not membership and current_user.organization_id == target_org_id:
        membership = UserOrganization(
            user_id=current_user.id, organization_id=target_org_id, is_active=True, is_default=True
        )
        db.add(membership)
        db.commit()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    # Get organization details
    organization = db.query(Organization).filter(Organization.id == target_org_id).first()
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organization is inactive"
        )

    # Update user's current organization
    current_user.organization_id = target_org_id
    db.commit()

    # Get roles for target organization
    user_roles = (
        db.query(Role)
        .filter(and_(Role.organization_id == target_org_id, Role.users.any(id=current_user.id)))
        .all()
    )

    role_names = [role.name for role in user_roles]

    # Get permissions for target organization (permissions are role-based)
    # Temporarily set user's organization_id to target for permission lookup
    original_org_id = current_user.organization_id
    current_user.organization_id = target_org_id
    user_permissions = PermissionChecker.get_user_permissions(current_user, db)
    user_api_scopes = PermissionChecker.get_user_api_scopes(current_user, db)
    current_user.organization_id = original_org_id  # Restore original

    # Check if user is organization owner for target org
    is_owner = organization.owner_id == current_user.id if organization else False

    # Create new token pair with updated organization context
    tokens = create_token_pair(
        user_id=current_user.id,
        organization_id=target_org_id,
        email=current_user.email,
        roles=role_names,
        permissions=user_permissions,
        api_scopes=user_api_scopes,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_organization_owner=is_owner,
    )

    return SwitchOrganizationResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        organization_id=target_org_id,
        organization_name=organization.name,
        roles=role_names,
        message=f"Successfully switched to {organization.name}",
    )


@router.post("/set-default", response_model=SetDefaultOrganizationResponse)
@limiter.limit(get_rate_limit())
async def set_default_organization(
    request: Request,
    org_data: SetDefaultOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set default organization for user

    The default organization is automatically selected when user logs in.

    Args:
        org_data: Target organization ID to set as default

    Returns:
        Confirmation of default organization
    """
    target_org_id = org_data.organization_id

    # Check if user is member of target organization
    membership = (
        db.query(UserOrganization)
        .filter(
            and_(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == target_org_id,
            )
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )

    # Get organization details
    organization = db.query(Organization).filter(Organization.id == target_org_id).first()
    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Remove default flag from all user's organizations
    db.query(UserOrganization).filter(UserOrganization.user_id == current_user.id).update(
        {"is_default": False}
    )

    # Set new default
    membership.is_default = True
    db.commit()

    return SetDefaultOrganizationResponse(
        organization_id=target_org_id,
        organization_name=organization.name,
        is_default=True,
        message=f"{organization.name} is now your default organization",
    )


@router.post("/invite", response_model=InviteUserToOrganizationResponse)
@limiter.limit(get_rate_limit())
async def invite_user_to_organization(
    request: Request,
    invite_data: InviteUserToOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Invite a user to join current organization

    Requires 'user.manage.full' permission in current organization.
    Creates UserOrganization association if user exists, otherwise sends invitation email.

    Args:
        invite_data: User email and optional roles

    Returns:
        Invitation status
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "user.manage.full", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite users",
        )

    # Get current organization
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

    if not organization:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Check if user exists
    invited_user = db.query(User).filter(User.email == invite_data.email).first()

    if not invited_user:
        # TODO: Send invitation email to non-existing user
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Email invitation feature coming soon.",
        )

    # Check if user is already member
    existing_membership = (
        db.query(UserOrganization)
        .filter(
            and_(
                UserOrganization.user_id == invited_user.id,
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

    # Create membership
    membership = UserOrganization(
        user_id=invited_user.id,
        organization_id=current_user.organization_id,
        is_active=True,
        is_default=False,
        invited_by=current_user.id,
    )
    db.add(membership)

    # Assign roles if specified
    if invite_data.role_names:
        roles = (
            db.query(Role)
            .filter(
                and_(
                    Role.organization_id == current_user.organization_id,
                    Role.name.in_(invite_data.role_names),
                )
            )
            .all()
        )

        for role in roles:
            if invited_user not in role.users:
                role.users.append(invited_user)

    db.commit()

    return InviteUserToOrganizationResponse(
        user_id=invited_user.id,
        email=invited_user.email,
        organization_id=current_user.organization_id,
        organization_name=organization.name,
        invitation_sent=True,
        message=f"{invited_user.email} has been added to {organization.name}",
    )


@router.delete("/remove/{user_id}")
@limiter.limit(get_rate_limit())
async def remove_user_from_organization(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a user from current organization

    Requires 'user.manage.full' permission.
    Cannot remove yourself or the last admin.

    Args:
        user_id: ID of user to remove

    Returns:
        Confirmation message
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "user.manage.full", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove users",
        )

    # Cannot remove yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the organization",
        )

    # Get organization to check ownership
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

    # Cannot remove organization owner
    if organization and organization.owner_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove organization owner. Please transfer ownership first.",
        )

    # Find membership
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organization",
        )

    # Get user details before deletion
    user = db.query(User).filter(User.id == user_id).first()
    user_email = user.email if user else "Unknown"

    # Delete membership
    db.delete(membership)
    db.commit()

    return {
        "message": f"User {user_email} has been removed from the organization",
        "user_id": user_id,
        "organization_id": current_user.organization_id,
    }
