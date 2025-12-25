"""
Social Login API endpoints.
Handles OAuth2 flows for Google, Apple, Facebook, GitHub, and Microsoft.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.dependencies import get_current_user
from backend.core.security import create_access_token, create_refresh_token
from backend.core.social_login_service import SocialProvider, get_social_login_service
from backend.db.session import get_db
from backend.models.organization import Organization
from backend.models.user import User

router = APIRouter(prefix="/auth/social", tags=["social-login"])


# === Schemas ===


class SocialProviderInfo(BaseModel):
    """Available social login provider"""

    provider: str
    name: str


class AvailableProvidersResponse(BaseModel):
    """List of available social login providers"""

    providers: list[SocialProviderInfo]


class AuthorizationUrlRequest(BaseModel):
    """Request to get authorization URL"""

    provider: str
    redirect_uri: str
    link_to_existing: bool = False  # If true, link to current user account


class AuthorizationUrlResponse(BaseModel):
    """Authorization URL response"""

    authorization_url: str
    state: str
    provider: str


class SocialCallbackRequest(BaseModel):
    """OAuth2 callback data"""

    provider: str
    code: str
    state: str
    redirect_uri: str


class SocialLoginResponse(BaseModel):
    """Social login response with tokens"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict
    is_new_user: bool
    linked_identity: bool


class LinkedIdentityResponse(BaseModel):
    """Social identity linked to user"""

    provider: str
    provider_email: Optional[str]
    provider_name: Optional[str]
    provider_avatar_url: Optional[str]
    linked_at: str
    last_login_at: Optional[str]


class UserIdentitiesResponse(BaseModel):
    """List of user's linked social identities"""

    identities: list[LinkedIdentityResponse]


class UnlinkIdentityRequest(BaseModel):
    """Request to unlink a social identity"""

    provider: str


class UnlinkIdentityResponse(BaseModel):
    """Response after unlinking identity"""

    success: bool
    message: str


# === Endpoints ===


@router.get("/providers", response_model=AvailableProvidersResponse)
async def get_available_providers(
    db: Session = Depends(get_db),
):
    """
    Get list of available social login providers.
    Only returns providers that are properly configured.
    """
    service = get_social_login_service(db)
    providers = service.get_available_providers()

    return AvailableProvidersResponse(providers=[SocialProviderInfo(**p) for p in providers])


@router.post("/authorize", response_model=AuthorizationUrlResponse)
async def get_authorization_url(
    request: AuthorizationUrlRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get OAuth2 authorization URL for a provider.
    If link_to_existing is true and user is authenticated,
    the social account will be linked to their existing account.
    """
    try:
        provider = SocialProvider(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {request.provider}",
        )

    service = get_social_login_service(db)

    user_id = None
    if request.link_to_existing and current_user:
        user_id = str(current_user.id)

    try:
        auth_url = service.get_authorization_url(
            provider=provider,
            redirect_uri=request.redirect_uri,
            user_id=user_id,
        )

        # Extract state from URL
        state = auth_url.split("state=")[1].split("&")[0] if "state=" in auth_url else ""

        return AuthorizationUrlResponse(
            authorization_url=auth_url,
            state=state,
            provider=provider.value,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/callback", response_model=SocialLoginResponse)
async def handle_social_callback(
    callback_data: SocialCallbackRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle OAuth2 callback from social provider.
    Creates new user or links to existing account.
    """
    try:
        provider = SocialProvider(callback_data.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {callback_data.provider}",
        )

    service = get_social_login_service(db)

    try:
        result = await service.handle_callback(
            provider=provider,
            code=callback_data.code,
            state=callback_data.state,
            redirect_uri=callback_data.redirect_uri,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to authenticate with {provider.value}: {str(e)}",
        )

    user_info = result["user_info"]
    tokens = result["tokens"]
    identity = result["identity"]
    state_data = result["state_data"]
    is_new = result["is_new"]

    # Check if we're linking to existing account
    linking_user_id = state_data.get("user_id")

    if linking_user_id:
        # Linking to existing account
        user = db.query(User).filter(User.id == linking_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found for linking",
            )

        if identity:
            # Already linked to another account
            if str(identity.user_id) != linking_user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"This {provider.value} account is already linked to another user",
                )
        else:
            # Create new identity link
            identity = service.create_identity(
                user_id=linking_user_id,
                provider=provider,
                user_info=user_info,
                tokens=tokens,
            )

        is_new_user = False
        linked_identity = True

    elif identity:
        # Existing social identity - log in the user
        user = db.query(User).filter(User.id == identity.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        is_new_user = False
        linked_identity = False

    else:
        # New social identity - create new user
        if not user_info.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{provider.value} did not provide an email address. Please use a different login method.",
            )

        # Check if email already exists
        existing_user = db.query(User).filter(User.email == user_info.email).first()

        if existing_user:
            # Email exists - link to existing account
            identity = service.create_identity(
                user_id=str(existing_user.id),
                provider=provider,
                user_info=user_info,
                tokens=tokens,
            )
            user = existing_user
            is_new_user = False
            linked_identity = True
        else:
            # Create new user and organization
            org = Organization(
                name=f"{user_info.name or user_info.email}'s Organization",
                slug=_generate_org_slug(user_info.email),
                plan_type="free",
            )
            db.add(org)
            db.flush()

            # Create user with random password (they'll use social login)
            import secrets

            from backend.core.security import get_password_hash

            random_password = secrets.token_urlsafe(32)

            user = User(
                email=user_info.email,
                first_name=user_info.first_name,
                last_name=user_info.last_name,
                hashed_password=get_password_hash(random_password),
                organization_id=org.id,
                is_active=True,
                is_email_verified=user_info.email_verified,
                avatar_url=user_info.avatar_url,
                external_provider=provider.value,
                external_id=user_info.provider_user_id,
            )
            db.add(user)
            db.flush()

            # Set org owner
            org.owner_id = user.id

            # Create social identity
            identity = service.create_identity(
                user_id=str(user.id),
                provider=provider,
                user_info=user_info,
                tokens=tokens,
            )

            db.commit()

            is_new_user = True
            linked_identity = True

    # Update last login
    user.last_login = datetime.now(timezone.utc).isoformat()
    db.commit()

    # Generate JWT tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "org_id": str(user.organization_id),
        }
    )
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return SocialLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "organization_id": str(user.organization_id),
        },
        is_new_user=is_new_user,
        linked_identity=linked_identity,
    )


@router.get("/identities", response_model=UserIdentitiesResponse)
async def get_user_identities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all social identities linked to the current user."""
    service = get_social_login_service(db)
    identities = service.get_user_identities(str(current_user.id))

    return UserIdentitiesResponse(
        identities=[
            LinkedIdentityResponse(
                provider=i.provider,
                provider_email=i.provider_email,
                provider_name=i.provider_name,
                provider_avatar_url=i.provider_avatar_url,
                linked_at=i.created_at,
                last_login_at=i.last_login_at,
            )
            for i in identities
        ]
    )


@router.post("/unlink", response_model=UnlinkIdentityResponse)
async def unlink_social_identity(
    request: UnlinkIdentityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unlink a social identity from the current user.
    User must have a password set or another linked identity to unlink.
    """
    try:
        provider = SocialProvider(request.provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown provider: {request.provider}",
        )

    service = get_social_login_service(db)

    # Check if user has password or other identities
    identities = service.get_user_identities(str(current_user.id))

    if len(identities) <= 1 and not current_user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot unlink the only login method. Set a password first.",
        )

    success = service.unlink_identity(str(current_user.id), provider)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {provider.value} identity linked to your account",
        )

    return UnlinkIdentityResponse(
        success=True,
        message=f"{provider.value.title()} account unlinked successfully",
    )


def _generate_org_slug(email: str) -> str:
    """Generate organization slug from email"""
    import re
    import secrets

    base = email.split("@")[0]
    # Remove special characters
    slug = re.sub(r"[^a-zA-Z0-9-]", "-", base.lower())
    # Add random suffix
    slug = f"{slug}-{secrets.token_hex(4)}"
    return slug[:50]  # Max 50 chars
