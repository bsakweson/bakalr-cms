"""
Authentication API endpoints
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.security import (
    verify_password,
    get_password_hash,
    create_token_pair,
    verify_token
)
from backend.core.dependencies import get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import limiter, get_rate_limit
from backend.core.config import settings
from backend.models.user import User
from backend.models.organization import Organization
from backend.api.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    PasswordChangeRequest
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit("register"))
async def register(
   
    request: Request,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    
    For the first user in an organization, creates a new organization.
    Otherwise, requires valid organization_id.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists (if provided)
    if user_data.username:
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Handle organization
    organization_id = user_data.organization_id
    
    if not organization_id:
        # Create new organization for first user
        org_name = user_data.email.split('@')[0] + "'s Organization"
        org_slug = user_data.email.split('@')[0].lower().replace('.', '-')
        
        # Ensure unique slug
        base_slug = org_slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == org_slug).first():
            org_slug = f"{base_slug}-{counter}"
            counter += 1
        
        organization = Organization(
            name=org_name,
            slug=org_slug,
            plan_type="free"
        )
        db.add(organization)
        db.flush()
        organization_id = organization.id
    else:
        # Verify organization exists
        organization = db.query(Organization).filter(Organization.id == organization_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    
    user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        hashed_password=hashed_password,
        organization_id=organization_id,
        is_active=True,
        is_email_verified=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Get user roles for token
    role_names = [role.name for role in user.roles]
    
    # Create token pair
    tokens = create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        roles=role_names
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        organization_id=user.organization_id,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        avatar_url=user.avatar_url,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(user)
    )
    
    # Send welcome email (async, non-blocking)
    try:
        from backend.core.email_service import email_service
        background_tasks.add_task(
            email_service.send_welcome_email,
            to_email=user.email,
            user_name=user.first_name or user.email,
            organization_name=organization.name,
            organization_id=organization.id,
            user_id=user.id
        )
    except Exception as e:
        # Log error but don't fail registration
        print(f"Failed to queue welcome email: {e}")
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=user_response
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(get_rate_limit())
async def login(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login with email and password
    
    Returns access token, refresh token, and user information
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Get user roles for token
    role_names = [role.name for role in user.roles]
    
    # Create token pair
    tokens = create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        roles=role_names
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        organization_id=user.organization_id,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        avatar_url=user.avatar_url,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(user)
    )
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=user_response
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(get_rate_limit())
async def refresh_token(
    request: Request,
    request_body: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    token_data = verify_token(request_body.refresh_token, token_type="refresh")
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Get user roles for token
    role_names = [role.name for role in user.roles]
    
    # Create new token pair
    tokens = create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        roles=role_names
    )
    
    # Prepare user response
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        organization_id=user.organization_id,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        avatar_url=user.avatar_url,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(user)
    )
    
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=user_response
    )


@router.get("/me", response_model=UserResponse)
@limiter.limit(get_rate_limit())
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information
    """
    role_names = [role.name for role in current_user.roles]
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        avatar_url=current_user.avatar_url,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(current_user)
    )


@router.put("/profile", response_model=UserResponse)
@limiter.limit(get_rate_limit())
async def update_profile(
    request: Request,
    full_name: str = None,
    email: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user profile
    """
    if full_name is not None:
        # Split full_name into first_name and last_name
        parts = full_name.strip().split(None, 1)
        current_user.first_name = parts[0] if len(parts) > 0 else ""
        current_user.last_name = parts[1] if len(parts) > 1 else ""
    
    if email is not None and email != current_user.email:
        # Check if email already exists
        existing = db.query(User).filter(User.email == email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = email
        current_user.is_email_verified = False  # Require re-verification
    
    db.commit()
    db.refresh(current_user)
    
    role_names = [role.name for role in current_user.roles]
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        avatar_url=current_user.avatar_url,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(current_user)
    )


@router.post("/change-password")
@limiter.limit(get_rate_limit())
async def change_password(
    request: Request,
    request_body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for current user
    """
    # Verify current password
    if not verify_password(request_body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(request_body.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}


@router.post("/logout")
@limiter.limit(get_rate_limit())
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by removing tokens. This endpoint is for completeness and can be
    extended to add token to a blacklist if needed.
    """
    return {"message": "Logged out successfully"}
