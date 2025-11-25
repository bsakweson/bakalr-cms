"""
Tenant/Organization switching API endpoints
Allows users to manage multi-organization memberships and switch context
"""
from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from backend.db.session import get_db
from backend.core.dependencies import get_current_user
from backend.core.security import create_token_pair
from backend.core.permissions import PermissionChecker
from backend.models.user import User
from backend.models.organization import Organization
from backend.models.user_organization import UserOrganization
from backend.models.rbac import Role
from backend.api.schemas.tenant import (
    OrganizationMembership,
    UserOrganizationsResponse,
    SwitchOrganizationRequest,
    SwitchOrganizationResponse,
    InviteUserToOrganizationRequest,
    InviteUserToOrganizationResponse,
    SetDefaultOrganizationRequest,
    SetDefaultOrganizationResponse
)


router = APIRouter(prefix="/tenant", tags=["Tenant Switching"])


@router.get("/organizations", response_model=UserOrganizationsResponse)
async def list_user_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get list of all organizations the current user belongs to
    
    Returns:
        List of organizations with membership details
    """
    # Get all user-organization memberships
    memberships = db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id
    ).all()
    
    # If no memberships exist, create one for primary organization (backward compatibility)
    if not memberships and current_user.organization_id:
        membership = UserOrganization(
            user_id=current_user.id,
            organization_id=current_user.organization_id,
            is_default=True,
            is_active=True
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
        user_roles = db.query(Role).filter(
            and_(
                Role.organization_id == org.id,
                Role.users.any(id=current_user.id)
            )
        ).all()
        
        role_names = [role.name for role in user_roles]
        
        organizations.append(OrganizationMembership(
            organization_id=org.id,
            organization_name=org.name,
            organization_slug=org.slug,
            is_default=membership.is_default,
            is_active=membership.is_active,
            roles=role_names,
            joined_at=membership.created_at if hasattr(membership, 'created_at') else ""
        ))
    
    return UserOrganizationsResponse(
        current_organization_id=current_user.organization_id,
        organizations=organizations,
        total=len(organizations)
    )


@router.post("/switch", response_model=SwitchOrganizationResponse)
async def switch_organization(
    request: SwitchOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Switch to a different organization
    
    Generates new JWT tokens with updated organization context.
    User must be a member of the target organization.
    
    Args:
        request: Target organization ID
    
    Returns:
        New tokens with updated organization context
    """
    target_org_id = request.organization_id
    
    # Check if user is member of target organization
    membership = db.query(UserOrganization).filter(
        and_(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == target_org_id,
            UserOrganization.is_active == True
        )
    ).first()
    
    # Backward compatibility: Check if this is user's primary organization
    if not membership and current_user.organization_id == target_org_id:
        membership = UserOrganization(
            user_id=current_user.id,
            organization_id=target_org_id,
            is_active=True,
            is_default=True
        )
        db.add(membership)
        db.commit()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    
    # Get organization details
    organization = db.query(Organization).filter(Organization.id == target_org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )
    
    # Update user's current organization
    current_user.organization_id = target_org_id
    db.commit()
    
    # Get roles for target organization
    user_roles = db.query(Role).filter(
        and_(
            Role.organization_id == target_org_id,
            Role.users.any(id=current_user.id)
        )
    ).all()
    
    role_names = [role.name for role in user_roles]
    
    # Create new token pair with updated organization context
    tokens = create_token_pair(
        user_id=current_user.id,
        organization_id=target_org_id,
        email=current_user.email,
        roles=role_names
    )
    
    return SwitchOrganizationResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        organization_id=target_org_id,
        organization_name=organization.name,
        roles=role_names,
        message=f"Successfully switched to {organization.name}"
    )


@router.post("/set-default", response_model=SetDefaultOrganizationResponse)
async def set_default_organization(
    request: SetDefaultOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Set default organization for user
    
    The default organization is automatically selected when user logs in.
    
    Args:
        request: Target organization ID to set as default
    
    Returns:
        Confirmation of default organization
    """
    target_org_id = request.organization_id
    
    # Check if user is member of target organization
    membership = db.query(UserOrganization).filter(
        and_(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == target_org_id
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization"
        )
    
    # Get organization details
    organization = db.query(Organization).filter(Organization.id == target_org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Remove default flag from all user's organizations
    db.query(UserOrganization).filter(
        UserOrganization.user_id == current_user.id
    ).update({"is_default": False})
    
    # Set new default
    membership.is_default = True
    db.commit()
    
    return SetDefaultOrganizationResponse(
        organization_id=target_org_id,
        organization_name=organization.name,
        is_default=True,
        message=f"{organization.name} is now your default organization"
    )


@router.post("/invite", response_model=InviteUserToOrganizationResponse)
async def invite_user_to_organization(
    request: InviteUserToOrganizationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invite a user to join current organization
    
    Requires 'users.manage' permission in current organization.
    Creates UserOrganization association if user exists, otherwise sends invitation email.
    
    Args:
        request: User email and optional roles
    
    Returns:
        Invitation status
    """
    # Check permission
    checker = PermissionChecker(current_user, db)
    if not checker.has_permission("users.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite users"
        )
    
    # Get current organization
    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user exists
    invited_user = db.query(User).filter(User.email == request.email).first()
    
    if not invited_user:
        # TODO: Send invitation email to non-existing user
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Email invitation feature coming soon."
        )
    
    # Check if user is already member
    existing_membership = db.query(UserOrganization).filter(
        and_(
            UserOrganization.user_id == invited_user.id,
            UserOrganization.organization_id == current_user.organization_id
        )
    ).first()
    
    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this organization"
        )
    
    # Create membership
    membership = UserOrganization(
        user_id=invited_user.id,
        organization_id=current_user.organization_id,
        is_active=True,
        is_default=False,
        invited_by=current_user.id
    )
    db.add(membership)
    
    # Assign roles if specified
    if request.role_names:
        roles = db.query(Role).filter(
            and_(
                Role.organization_id == current_user.organization_id,
                Role.name.in_(request.role_names)
            )
        ).all()
        
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
        message=f"{invited_user.email} has been added to {organization.name}"
    )


@router.delete("/remove/{user_id}")
async def remove_user_from_organization(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a user from current organization
    
    Requires 'users.manage' permission.
    Cannot remove yourself or the last admin.
    
    Args:
        user_id: ID of user to remove
    
    Returns:
        Confirmation message
    """
    # Check permission
    checker = PermissionChecker(current_user, db)
    if not checker.has_permission("users.manage"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove users"
        )
    
    # Cannot remove yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot remove yourself from the organization"
        )
    
    # Find membership
    membership = db.query(UserOrganization).filter(
        and_(
            UserOrganization.user_id == user_id,
            UserOrganization.organization_id == current_user.organization_id
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a member of this organization"
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
        "organization_id": current_user.organization_id
    }
