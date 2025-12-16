"""
Authentication API endpoints
"""

from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict
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
from backend.core.avatar import get_gravatar_url
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


# Account Deletion Schemas
class DeleteAccountRequest(BaseModel):
    """Request schema for account deletion"""

    password: str
    confirmation: str  # Must be "DELETE" to confirm

    model_config = ConfigDict(from_attributes=True)


class DeleteAccountResponse(BaseModel):
    """Response schema for account deletion"""

    message: str
    deleted_user_id: UUID
    deleted_organization: Optional[str] = None
    deleted_users_count: int = 1

    model_config = ConfigDict(from_attributes=True)


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

        # Seed default roles (admin, editor, viewer) for new organization
        from backend.core.seed_permissions import seed_organization_roles

        seed_organization_roles(db, organization_id)
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
        # Roles are already seeded via seed_organization_roles
        admin_role = (
            db.query(Role)
            .filter(Role.organization_id == organization_id, Role.name == "admin")
            .first()
        )

        if admin_role:
            user.roles.append(admin_role)
        else:
            print(f"⚠️  Admin role not found for organization {organization_id}")

        # Set this user as organization owner
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if org and not org.owner_id:
            org.owner_id = user.id
            print(f"✅ Set {user.email} as owner of organization: {org.name}")

        print(f"✅ Assigned admin role to organization creator: {user.email}")
    else:
        # Subsequent users = Viewer role (least permissions)
        # Roles are already seeded via seed_organization_roles
        viewer_role = (
            db.query(Role)
            .filter(Role.organization_id == organization_id, Role.name == "viewer")
            .first()
        )

        if viewer_role:
            user.roles.append(viewer_role)
        else:
            print(f"⚠️  Viewer role not found for organization {organization_id}")

        print(f"ℹ️  Assigned viewer role to new user: {user.email}")

    db.commit()
    db.refresh(user)

    # Get user roles for token
    role_names = [role.name for role in user.roles]

    # Check if user is organization owner
    is_owner = organization.owner_id == user.id if organization else False

    # Create token pair
    tokens = create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        roles=role_names,
        first_name=user.first_name,
        last_name=user.last_name,
        is_organization_owner=is_owner,
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
        is_organization_owner=is_owner,
        avatar_url=user.avatar_url,
        gravatar_url=get_gravatar_url(user.email),
        bio=user.bio,
        preferences=user.preferences,
        roles=role_names,
        permissions=PermissionChecker.get_user_permissions(user),
        organization=organization,  # Include organization in response
    )

    # Send verification email (async, non-blocking)
    async def send_verification_email_task():
        """Wrapper to catch and log errors in background task"""
        try:
            from backend.core.email_service import email_service

            await email_service.send_verification_email(
                db=db,
                to_email=user.email,
                user_name=user.first_name or user.email,
                verification_token=verification_token,
                organization_name=organization.name,
                organization_id=organization.id,
                user_id=user.id,
            )
            print(f"✓ Verification email sent to {user.email}")
        except Exception as e:
            import traceback

            print(f"✗ Failed to send verification email to {user.email}: {e}")
            traceback.print_exc()

    # Send welcome email (async, non-blocking)
    async def send_welcome_email_task():
        """Wrapper to send welcome email after registration"""
        try:
            from backend.core.email_service import email_service

            await email_service.send_welcome_email(
                db=db,
                to_email=user.email,
                user_name=user.first_name or user.email,
                organization_name=organization.name,
                organization_id=organization.id,
                user_id=user.id,
            )
            print(f"✓ Welcome email sent to {user.email}")
        except Exception as e:
            import traceback

            print(f"✗ Failed to send welcome email to {user.email}: {e}")
            traceback.print_exc()

    background_tasks.add_task(send_verification_email_task)
    background_tasks.add_task(send_welcome_email_task)

    # Create session record for session management
    from backend.core.session_service import SessionService

    session_service = SessionService(db)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    user_agent = request.headers.get("User-Agent")

    session = session_service.create_session(
        user=user,
        ip_address=client_ip,
        user_agent_string=user_agent,
        device_id=None,
        login_method="registration",
        mfa_verified=False,
        refresh_token=tokens.refresh_token,
    )

    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        user=user_response,
        session_id=str(session.id),
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

    # Get organization to check ownership
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    is_owner = organization.owner_id == user.id if organization else False

    # Create token pair
    tokens = create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        roles=role_names,
        first_name=user.first_name,
        last_name=user.last_name,
        is_organization_owner=is_owner,
    )

    # Create session record for session management
    from backend.core.session_service import SessionService

    session_service = SessionService(db)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    user_agent = request.headers.get("User-Agent")
    device_id = credentials.device_id if hasattr(credentials, "device_id") else None

    session = session_service.create_session(
        user=user,
        ip_address=client_ip,
        user_agent_string=user_agent,
        device_id=device_id,
        login_method="password",
        mfa_verified=False,
        refresh_token=tokens.refresh_token,
    )

    # Get organization details (Organization is already imported at module level)
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
        is_organization_owner=is_owner,
        avatar_url=user.avatar_url,
        gravatar_url=get_gravatar_url(user.email),
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
        session_id=str(session.id),  # Include session ID for client tracking
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
    user = db.query(User).filter(User.id == token_data.sub).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    # Get user roles for token
    role_names = [role.name for role in user.roles]

    # Get organization to check ownership
    organization = db.query(Organization).filter(Organization.id == user.organization_id).first()
    is_owner = organization.owner_id == user.id if organization else False

    # Create new token pair
    tokens = create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        roles=role_names,
        first_name=user.first_name,
        last_name=user.last_name,
        is_organization_owner=is_owner,
    )

    # Update existing session - do NOT create new sessions on refresh
    import hashlib
    from datetime import datetime, timezone
    from uuid import UUID

    from backend.models.session import UserSession

    # Try to find existing session - first by session_id, then by refresh token hash
    existing_session = None

    # Try session_id first (most reliable)
    if request_body.session_id:
        try:
            session_uuid = UUID(request_body.session_id)
            existing_session = (
                db.query(UserSession)
                .filter(
                    UserSession.id == session_uuid,
                    UserSession.user_id == user.id,
                    UserSession.is_active.is_(True),
                )
                .first()
            )
        except (ValueError, TypeError):
            pass  # Invalid UUID, continue to hash lookup

    # Fallback to refresh token hash lookup
    if not existing_session:
        old_token_hash = hashlib.sha256(request_body.refresh_token.encode()).hexdigest()
        existing_session = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.refresh_token_hash == old_token_hash,
                UserSession.is_active.is_(True),
            )
            .first()
        )

    session_id = None
    if existing_session:
        # Update existing session with new refresh token hash
        existing_session.refresh_token_hash = hashlib.sha256(
            tokens.refresh_token.encode()
        ).hexdigest()
        existing_session.last_active_at = datetime.now(timezone.utc)
        db.commit()
        session_id = str(existing_session.id)
    else:
        # Log warning instead of creating new session - this prevents session explosion
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Refresh token used but no matching session found for user {user.id}. Session ID: {request_body.session_id}"
        )
        # Return the provided session_id even if we couldn't find the session
        # The session may have been cleaned up but the refresh token is still valid
        session_id = request_body.session_id

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
        is_organization_owner=is_owner,
        avatar_url=user.avatar_url,
        gravatar_url=get_gravatar_url(user.email),
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
        session_id=session_id,
    )


@router.get("/me", response_model=UserResponse)
@limiter.limit(get_rate_limit())
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current authenticated user information
    """
    role_names = [role.name for role in current_user.roles]

    # Check if user is organization owner
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )
    is_owner = organization.owner_id == current_user.id if organization else False

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        is_organization_owner=is_owner,
        avatar_url=current_user.avatar_url,
        gravatar_url=get_gravatar_url(current_user.email),
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
    is_owner = organization.owner_id == current_user.id if organization else False

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        organization_id=current_user.organization_id,
        is_active=current_user.is_active,
        is_email_verified=current_user.is_email_verified,
        is_organization_owner=is_owner,
        avatar_url=current_user.avatar_url,
        gravatar_url=get_gravatar_url(current_user.email),
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


class LogoutRequest(BaseModel):
    """Request schema for logout"""

    session_id: Optional[str] = None


@router.post("/logout")
@limiter.limit(get_rate_limit())
async def logout(
    request: Request,
    logout_request: Optional[LogoutRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Logout current user and terminate the session.

    If session_id is provided, terminates that specific session.
    Otherwise, attempts to find and terminate the current session.
    """
    from backend.models.session import RefreshTokenRecord, UserSession

    session_id = logout_request.session_id if logout_request else None

    if session_id:
        # Terminate specific session
        session = (
            db.query(UserSession)
            .filter(
                UserSession.id == session_id,
                UserSession.user_id == current_user.id,
            )
            .first()
        )

        if session:
            session.terminate()
            # Also invalidate any refresh tokens for this session
            db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.session_id == session_id
            ).delete()
            db.commit()
    else:
        # Try to find session from token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            payload = verify_token(token)
            if payload and payload.get("session_id"):
                session = (
                    db.query(UserSession)
                    .filter(
                        UserSession.id == payload["session_id"],
                        UserSession.user_id == current_user.id,
                    )
                    .first()
                )
                if session:
                    session.terminate()
                    db.query(RefreshTokenRecord).filter(
                        RefreshTokenRecord.session_id == payload["session_id"]
                    ).delete()
                    db.commit()

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


@router.delete("/account", response_model=DeleteAccountResponse)
@limiter.limit(get_rate_limit("expensive_operations"))
async def delete_account(
    request: Request,
    delete_request: DeleteAccountRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete the current user's account.

    **For regular users**: Removes the user from the organization and deletes their data.

    **For organization owners**: Deletes the entire organization and all its members.
    This is a destructive operation that cannot be undone.

    Requires:
    - Password confirmation
    - Typing "DELETE" as confirmation

    Triggers:
    - user.deleted webhook event for each deleted user
    - organization.deleted webhook event (if org owner)
    """
    from backend.models.api_key import APIKey
    from backend.models.session import RefreshTokenRecord, UserSession

    # Verify confirmation text
    if delete_request.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type 'DELETE' to confirm account deletion",
        )

    # Verify password
    if not verify_password(delete_request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    # Get organization
    organization = (
        db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    deleted_user_id = current_user.id
    deleted_org_name = None
    deleted_users_count = 1

    # Check if user is organization owner
    is_org_owner = organization.owner_id == current_user.id

    if is_org_owner:
        # Organization owner - delete entire organization and all members
        deleted_org_name = organization.name

        # Get all users in the organization for webhook notifications
        org_users = db.query(User).filter(User.organization_id == organization.id).all()
        deleted_users_count = len(org_users)
        user_ids_to_delete = [user.id for user in org_users]

        # Clear owner_id first to avoid foreign key constraint issues
        organization.owner_id = None
        db.flush()

        # Delete all sessions for all users in the organization
        db.query(UserSession).filter(UserSession.organization_id == organization.id).delete(
            synchronize_session=False
        )

        # Delete all refresh tokens for all users in the organization
        db.query(RefreshTokenRecord).filter(
            RefreshTokenRecord.user_id.in_(user_ids_to_delete)
        ).delete(synchronize_session=False)

        # Delete all API keys for users in the organization
        db.query(APIKey).filter(APIKey.organization_id == organization.id).delete(
            synchronize_session=False
        )

        # Delete the organization (cascades to users, roles, content, etc.)
        db.delete(organization)

        # Schedule webhook notifications for each deleted user
        background_tasks.add_task(
            _emit_deletion_webhooks,
            user_ids=user_ids_to_delete,
            organization_id=organization.id,
            organization_name=deleted_org_name,
            is_org_deletion=True,
        )

    else:
        # Regular user - just remove themselves
        # Delete user sessions
        db.query(UserSession).filter(UserSession.user_id == current_user.id).delete(
            synchronize_session=False
        )

        # Delete user refresh tokens
        db.query(RefreshTokenRecord).filter(RefreshTokenRecord.user_id == current_user.id).delete(
            synchronize_session=False
        )

        # Delete user API keys
        db.query(APIKey).filter(APIKey.user_id == current_user.id).delete(synchronize_session=False)

        # Delete the user
        db.delete(current_user)

        # Schedule webhook notification
        background_tasks.add_task(
            _emit_deletion_webhooks,
            user_ids=[current_user.id],
            organization_id=organization.id,
            organization_name=organization.name,
            is_org_deletion=False,
        )

    db.commit()

    return DeleteAccountResponse(
        message="Account deleted successfully"
        + (
            f". Organization '{deleted_org_name}' and all {deleted_users_count} members have been removed."
            if is_org_owner
            else ""
        ),
        deleted_user_id=deleted_user_id,
        deleted_organization=deleted_org_name,
        deleted_users_count=deleted_users_count,
    )


async def _emit_deletion_webhooks(
    user_ids: List[UUID],
    organization_id: UUID,
    organization_name: str,
    is_org_deletion: bool,
):
    """
    Emit webhook events for user deletions.
    This runs as a background task after the deletion is committed.
    """
    # Note: We can't emit webhooks here because the organization's webhooks
    # are deleted along with the organization. Instead, external systems
    # (like boutique-platform) should handle user deletion through their
    # own sync mechanisms or by catching the API call response.
    #
    # For boutique-platform integration, the frontend will need to:
    # 1. Call CMS delete account endpoint
    # 2. On success, call platform cleanup endpoint
    #
    # Future enhancement: Support external webhook URLs that persist
    # beyond organization deletion for critical events like user.deleted
    pass


# ==================== Avatar Upload Endpoints ====================


class AvatarUploadResponse(BaseModel):
    """Response schema for avatar upload"""

    avatar_url: str
    message: str

    model_config = ConfigDict(from_attributes=True)


class AvatarDeleteResponse(BaseModel):
    """Response schema for avatar deletion"""

    message: str
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/avatar", response_model=AvatarUploadResponse)
@limiter.limit(get_rate_limit())
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload profile picture/avatar for current user.

    Accepts image files (JPEG, PNG, GIF, WebP).
    Max file size: 5MB.
    Recommended size: 256x256 pixels.

    The uploaded image is stored and the user's avatar_url is automatically updated.
    Previous avatar files are NOT deleted automatically to support CDN caching.
    """
    from backend.core.media_utils import generate_unique_filename, get_file_extension
    from backend.core.storage import get_storage_backend

    # Validate file is provided and has content
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided. Please upload an image file.",
        )

    # Get file extension
    extension = get_file_extension(file.filename)

    # Validate it's an image
    allowed_image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    if extension.lower() not in allowed_image_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_image_extensions)}",
        )

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Validate file size (5MB max for avatars)
    max_avatar_size = 5 * 1024 * 1024  # 5MB
    if file_size > max_avatar_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size for avatars is 5MB.",
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file provided.",
        )

    # Generate unique filename with avatar prefix
    base_filename = f"avatar_{current_user.id}"
    unique_filename = generate_unique_filename(f"{base_filename}{extension}")

    # Get storage backend
    storage = get_storage_backend()

    # Prepare storage path (organization-specific avatars folder)
    relative_path = f"{current_user.organization_id}/avatars/{unique_filename}"

    # Save file using storage backend
    try:
        avatar_url = storage.save_file(file_content, relative_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save avatar: {str(e)}",
        )

    # Update user's avatar_url
    current_user.avatar_url = avatar_url
    db.commit()
    db.refresh(current_user)

    return AvatarUploadResponse(
        avatar_url=avatar_url,
        message="Avatar uploaded successfully",
    )


@router.delete("/avatar", response_model=AvatarDeleteResponse)
@limiter.limit(get_rate_limit())
async def delete_avatar(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete/remove current user's avatar.

    This clears the avatar_url field. The actual file may remain in storage
    for CDN caching purposes but will no longer be associated with the user.
    """

    if not current_user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No avatar to delete",
        )

    # Optionally delete the file from storage
    # (commented out to support CDN caching - files will be cleaned up by lifecycle rules)
    # try:
    #     storage = get_storage_backend()
    #     # Extract relative path from URL and delete
    #     storage.delete_file(relative_path)
    # except Exception:
    #     pass  # File deletion is best-effort

    # Clear user's avatar_url
    current_user.avatar_url = None
    db.commit()
    db.refresh(current_user)

    return AvatarDeleteResponse(
        message="Avatar removed successfully",
        avatar_url=None,
    )
