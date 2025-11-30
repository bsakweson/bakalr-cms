"""
Authentication API endpoints
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.api.schemas.auth import (
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from backend.core.dependencies import get_current_user, get_current_user_unverified
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.security import (
    create_token_pair,
    get_password_hash,
    verify_password,
    verify_token,
)
from backend.db.session import get_db
from backend.models.organization import Organization
from backend.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit("register"))
async def register(
    request: Request,
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Check if username already exists (if provided)
    if user_data.username:
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

    # Handle organization
    organization_id = user_data.organization_id

    if not organization_id:
        # Create new organization for first user
        # organization_name is now required (validated by schema)
        org_name = user_data.organization_name

        # Check if organization name already exists
        existing_org = db.query(Organization).filter(Organization.name == org_name).first()
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Organization '{org_name}' already exists. Please choose a different name or contact the organization owner to be invited.",
            )

        org_slug = (
            user_data.organization_name.lower().replace(" ", "-").replace("'", "").replace(".", "-")
        )

        # Ensure unique slug
        base_slug = org_slug
        counter = 1
        while db.query(Organization).filter(Organization.slug == org_slug).first():
            org_slug = f"{base_slug}-{counter}"
            counter += 1

        organization = Organization(name=org_name, slug=org_slug, plan_type="free")
        db.add(organization)
        db.flush()
        organization_id = organization.id
    else:
        # Verify organization exists
        organization = db.query(Organization).filter(Organization.id == organization_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

    # Create user
    hashed_password = get_password_hash(user_data.password)

    # Handle full_name splitting
    first_name = user_data.first_name
    last_name = user_data.last_name

    if user_data.full_name:
        # Split full_name into first_name and last_name
        parts = user_data.full_name.strip().split(None, 1)  # Split on first whitespace
        first_name = parts[0] if len(parts) > 0 else None
        last_name = parts[1] if len(parts) > 1 else None

    # Generate email verification token
    import secrets
    from datetime import datetime, timedelta, timezone

    verification_token = secrets.token_urlsafe(32)
    verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    user = User(
        email=user_data.email,
        username=user_data.username,
        first_name=first_name,
        last_name=last_name,
        hashed_password=hashed_password,
        organization_id=organization_id,
        is_active=True,
        is_email_verified=False,
        email_verification_token=verification_token,
        email_verification_expires=verification_expires.isoformat(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign default role to new user
    from backend.models.rbac import Role

    # If this is the first user in the organization (org creator), assign admin role
    user_count = db.query(User).filter(User.organization_id == organization_id).count()

    if user_count == 1:
        # First user = Organization Owner (Admin role)
        admin_role = (
            db.query(Role)
            .filter(Role.organization_id == organization_id, Role.name == "admin")
            .first()
        )

        if not admin_role:
            # Create admin role if it doesn't exist
            from backend.models.rbac import Permission

            admin_role = Role(
                organization_id=organization_id,
                name="admin",
                description="Organization administrator (auto-created)",
                is_system_role=True,
                level=80,
            )
            db.add(admin_role)
            db.flush()

            # Assign all non-system permissions to admin
            permissions = db.query(Permission).filter(Permission.category != "system").all()
            admin_role.permissions.extend(permissions)

        user.roles.append(admin_role)
        print(f"✅ Assigned admin role to organization creator: {user.email}")
    else:
        # Subsequent users = Viewer role (least permissions)
        viewer_role = (
            db.query(Role)
            .filter(Role.organization_id == organization_id, Role.name == "viewer")
            .first()
        )

        if not viewer_role:
            # Create viewer role if it doesn't exist
            viewer_role = Role(
                organization_id=organization_id,
                name="viewer",
                description="Read-only access (auto-created)",
                is_system_role=True,
                level=20,
            )
            db.add(viewer_role)
            db.flush()

            # Assign only read permissions
            from backend.models.rbac import Permission

            read_permissions = db.query(Permission).filter(Permission.name.like("%.read")).all()
            viewer_role.permissions.extend(read_permissions)

        user.roles.append(viewer_role)
        print(f"ℹ️  Assigned viewer role to new user: {user.email}")

    db.commit()
    db.refresh(user)

    # Get user roles for token
    role_names = [role.name for role in user.roles]

    # Create token pair
    tokens = create_token_pair(
        user_id=user.id, organization_id=user.organization_id, email=user.email, roles=role_names
    )

    # Prepare user response (include organization details)
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
        bio=user.bio,
        preferences=user.preferences,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(user),
        organization=organization,  # Include organization in response
    )

    # Send verification email (async, non-blocking)
    try:
        from backend.core.email_service import email_service

        background_tasks.add_task(
            email_service.send_verification_email,
            to_email=user.email,
            user_name=user.first_name or user.email,
            verification_token=verification_token,
            organization_name=organization.name,
            organization_id=organization.id,
            user_id=user.id,
        )
    except Exception as e:
        # Log error but don't fail registration
        print(f"Failed to queue verification email: {e}")

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=user_response,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit(get_rate_limit())
async def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email/username and password

    Returns access token, refresh token, and user information
    """
    # Find user by email or username
    if credentials.email:
        user = db.query(User).filter(User.email == credentials.email).first()
    elif credentials.username:
        user = db.query(User).filter(User.username == credentials.username).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or username must be provided",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect credentials"
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    # Get user roles for token
    role_names = [role.name for role in user.roles]

    # Create token pair
    tokens = create_token_pair(
        user_id=user.id, organization_id=user.organization_id, email=user.email, roles=role_names
    )

    # Get organization details
    from backend.models.organization import Organization

    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()

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
        bio=user.bio,
        preferences=user.preferences,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(user),
        organization=organization,
    )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=user_response,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(get_rate_limit())
async def refresh_token(
    request: Request, request_body: RefreshTokenRequest, db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    # Verify refresh token
    token_data = verify_token(request_body.refresh_token, token_type="refresh")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Get user
    user = db.query(User).filter(User.id == int(token_data.sub)).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    # Get user roles for token
    role_names = [role.name for role in user.roles]

    # Create new token pair
    tokens = create_token_pair(
        user_id=user.id, organization_id=user.organization_id, email=user.email, roles=role_names
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
        bio=user.bio,
        preferences=user.preferences,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(user),
    )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=user_response,
    )


@router.get("/me", response_model=UserResponse)
@limiter.limit(get_rate_limit())
async def get_current_user_info(request: Request, current_user: User = Depends(get_current_user)):
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
        bio=current_user.bio,
        preferences=current_user.preferences,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(current_user),
    )


@router.put("/profile", response_model=UserResponse)
@limiter.limit(get_rate_limit())
async def update_profile(
    request: Request,
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current user profile.

    Supports updating:
    - email (triggers email verification reset)
    - username
    - first_name and last_name (or provide full_name to auto-split)
    - avatar_url
    - bio (user description, max 500 characters)
    - preferences (JSON string for user settings like theme, language, notifications)
    """
    # Handle full_name if provided (for backwards compatibility)
    if hasattr(profile_data, "full_name") and profile_data.full_name:
        parts = profile_data.full_name.strip().split(None, 1)
        profile_data.first_name = parts[0] if len(parts) > 0 else None
        profile_data.last_name = parts[1] if len(parts) > 1 else None

    # Update email if provided
    if profile_data.email is not None and profile_data.email != current_user.email:
        # Check if email already exists
        existing = (
            db.query(User)
            .filter(User.email == profile_data.email, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use"
            )
        current_user.email = profile_data.email
        current_user.is_email_verified = False  # Require re-verification

    # Update username if provided
    if profile_data.username is not None:
        # Check if username already exists
        if profile_data.username:  # Only check if not empty
            existing = (
                db.query(User)
                .filter(User.username == profile_data.username, User.id != current_user.id)
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Username already in use"
                )
        current_user.username = profile_data.username or None

    # Update names if provided
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name

    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name

    # Update avatar URL if provided
    if profile_data.avatar_url is not None:
        current_user.avatar_url = profile_data.avatar_url

    # Update bio if provided
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio

    # Update preferences if provided
    if profile_data.preferences is not None:
        current_user.preferences = profile_data.preferences

    db.commit()
    db.refresh(current_user)

    role_names = [role.name for role in current_user.roles]

    # Get organization for response
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

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
        bio=current_user.bio,
        preferences=current_user.preferences,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(current_user),
        organization=organization,
    )


@router.post("/change-password")
@limiter.limit(get_rate_limit())
async def change_password(
    request: Request,
    request_body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Change password for current user
    """
    # Verify current password
    if not verify_password(request_body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    # Update password
    current_user.hashed_password = get_password_hash(request_body.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


@router.post("/logout")
@limiter.limit(get_rate_limit())
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """
    Logout current user

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing tokens. This endpoint is for completeness and can be
    extended to add token to a blacklist if needed.
    """
    return {"message": "Logged out successfully"}


@router.get("/verify-email/{token}")
@limiter.limit(get_rate_limit())
async def verify_email(request: Request, token: str, db: Session = Depends(get_db)):
    """
    Verify user's email address using the verification token sent via email
    """
    from datetime import datetime, timezone

    # Find user with this verification token
    user = db.query(User).filter(User.email_verification_token == token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification token"
        )

    # Check if token has expired (24 hours)
    if user.email_verification_expires:
        expires_at = datetime.fromisoformat(user.email_verification_expires)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new one.",
            )

    # Mark email as verified
    user.is_email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    db.commit()

    return {
        "message": "Email verified successfully! You can now access all features.",
        "email": user.email,
    }


@router.post("/resend-verification")
@limiter.limit(get_rate_limit())
async def resend_verification(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_unverified),
    db: Session = Depends(get_db),
):
    """
    Resend verification email to current user
    """
    import secrets
    from datetime import datetime, timedelta, timezone

    from backend.core.email_service import email_service

    # Check if already verified
    if current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified"
        )

    # Generate new verification token
    verification_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Update user with new token
    current_user.email_verification_token = verification_token
    current_user.email_verification_expires = expires_at.isoformat()
    db.commit()

    # Get organization
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

    # Send verification email
    try:
        background_tasks.add_task(
            email_service.send_verification_email,
            to_email=current_user.email,
            user_name=current_user.first_name or current_user.email,
            verification_token=verification_token,
            organization_name=organization.name if organization else "Bakalr CMS",
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
    except Exception as e:
        print(f"Failed to queue verification email: {e}")

    return {"message": "Verification email sent successfully", "email": current_user.email}
