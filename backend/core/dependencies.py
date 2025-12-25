"""
FastAPI dependencies for authentication and authorization

Supports two authentication providers:
- 'cms': Built-in JWT authentication (default)
- 'keycloak': External Keycloak IdP authentication

Set AUTH_PROVIDER environment variable to switch providers.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import verify_password, verify_token
from backend.db.session import get_db
from backend.models.api_key import APIKey
from backend.models.organization import Organization
from backend.models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()


def is_keycloak_auth() -> bool:
    """Check if Keycloak authentication is enabled"""
    return getattr(settings, "AUTH_PROVIDER", "cms").lower() == "keycloak"


async def _get_user_from_cms_token(token: str, db: Session) -> Optional[User]:
    """
    Validate CMS JWT token and return user.
    """
    token_data = verify_token(token, token_type="access")
    if not token_data:
        return None

    user = db.query(User).filter(User.id == token_data.sub).first()
    return user


async def _get_or_create_user_from_keycloak(token: str, db: Session) -> Optional[User]:
    """
    Validate Keycloak JWT token and return/create CMS user.

    If the user doesn't exist in CMS, auto-provision them based on
    Keycloak token claims.
    """
    # Import here to avoid circular imports
    from backend.core.keycloak_auth import get_keycloak_provider

    provider = get_keycloak_provider()
    if not provider:
        logger.error("Keycloak provider not configured")
        return None

    # Verify token with Keycloak
    token_data = await provider.verify_token(token)
    if not token_data:
        return None

    # Look up user by Keycloak subject ID (stored in external_id)
    user = db.query(User).filter(User.external_id == token_data.sub).first()

    if user:
        # Update user info from token if changed
        updated = False
        if token_data.email and user.email != token_data.email:
            user.email = token_data.email
            updated = True
        if token_data.given_name and user.first_name != token_data.given_name:
            user.first_name = token_data.given_name
            updated = True
        if token_data.family_name and user.last_name != token_data.family_name:
            user.last_name = token_data.family_name
            updated = True
        if updated:
            db.commit()
            db.refresh(user)
        return user

    # Auto-provision new user from Keycloak token
    logger.info(f"Auto-provisioning CMS user for Keycloak user: {token_data.sub}")

    # Get or create organization
    organization = None
    if token_data.tenant_id:
        # Look up org by external tenant ID
        organization = (
            db.query(Organization).filter(Organization.external_id == token_data.tenant_id).first()
        )

    if not organization:
        # Create new organization for this user
        org_name = token_data.organization_name or f"{token_data.email}'s Organization"
        org_slug = org_name.lower().replace(" ", "-").replace("'", "").replace("@", "-at-")

        # Ensure unique slug
        base_slug = org_slug[:50]  # Limit length
        counter = 1
        while db.query(Organization).filter(Organization.slug == org_slug).first():
            org_slug = f"{base_slug}-{counter}"
            counter += 1

        organization = Organization(
            name=org_name,
            slug=org_slug,
            external_id=token_data.tenant_id,  # Link to Keycloak tenant
            plan_type="free",
            is_active=True,
        )
        db.add(organization)
        db.flush()
        logger.info(f"Created organization: {organization.name} (id={organization.id})")

    # Create user
    user = User(
        email=token_data.email,
        username=token_data.preferred_username,
        first_name=token_data.given_name,
        last_name=token_data.family_name,
        external_id=token_data.sub,  # Keycloak user ID
        organization_id=organization.id,
        is_active=True,
        is_email_verified=token_data.email_verified,  # Trust Keycloak's verification
        hashed_password="",  # No password - auth via Keycloak
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Assign roles based on Keycloak roles
    cms_roles = provider.map_roles_to_cms(token_data)
    logger.info(f"Created user: {user.email} with roles: {cms_roles}")

    # TODO: Actually assign roles from cms_roles list
    # This would require creating role assignments in the RBAC system

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Supports both CMS JWT and Keycloak JWT based on AUTH_PROVIDER setting.
    For Keycloak auth, auto-provisions users on first access.

    Args:
        credentials: Bearer token from request header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials

    # Determine auth provider and validate token
    if is_keycloak_auth():
        user = await _get_or_create_user_from_keycloak(token, db)
    else:
        user = await _get_user_from_cms_token(token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    # Check email verification (skip for Keycloak - trust their verification)
    # Also skip in test mode when SKIP_EMAIL_VERIFICATION is set
    skip_email_verification = os.environ.get("SKIP_EMAIL_VERIFICATION", "").lower() == "true"
    if not is_keycloak_auth() and not user.is_email_verified and not skip_email_verification:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email for verification link.",
        )

    return user


async def get_current_user_unverified(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user WITHOUT checking email verification.
    Used for endpoints that need authentication but should work for unverified users,
    such as resending verification emails.

    Args:
        credentials: Bearer token from request header
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials

    # Verify token
    token_data = verify_token(token, token_type="access")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = db.query(User).filter(User.id == token_data.sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    # NOTE: We do NOT check is_email_verified here - that's the whole point
    # This allows unverified users to access specific endpoints like resend-verification

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (alias for get_current_user)

    Args:
        current_user: Current user from get_current_user

    Returns:
        User object
    """
    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    Useful for optional authentication endpoints

    Args:
        credentials: Optional bearer token
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        token_data = verify_token(token, token_type="access")

        if not token_data:
            return None

        user = db.query(User).filter(User.id == token_data.sub).first()

        if user and user.is_active:
            return user

    except Exception:
        pass

    return None


async def get_current_organization(current_user: User = Depends(get_current_user)):
    """
    Get the current user's active organization

    Args:
        current_user: Current authenticated user

    Returns:
        Organization object

    Raises:
        HTTPException: 400 if user has no active organization
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active organization. Please switch to an organization first.",
        )

    # Return the organization from the relationship
    organization = current_user.organization

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Current organization not found"
        )

    return organization


async def get_api_key_auth(
    x_api_key: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> Optional[dict]:
    """
    Authenticate using API key from X-API-Key header.

    Args:
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        Dict with organization_id and permissions if valid, None otherwise
    """
    if not x_api_key:
        return None

    # Query all active API keys
    api_keys = db.query(APIKey).filter(APIKey.is_active == True).all()

    # Check each key's hash
    for api_key in api_keys:
        if verify_password(x_api_key, api_key.key_hash):
            # Check expiration
            expires_at_value = api_key.expires_at
            if isinstance(expires_at_value, str):
                from dateutil import parser

                expires_at_value = parser.parse(expires_at_value)

            if expires_at_value and datetime.now(timezone.utc) > expires_at_value:
                continue

            # Update last used timestamp
            api_key.last_used_at = datetime.now(timezone.utc)
            db.commit()

            # Parse permissions
            permissions = api_key.permissions.split(",") if api_key.permissions else []

            return {
                "organization_id": api_key.organization_id,
                "permissions": permissions,
                "api_key_id": api_key.id,
            }

    return None


async def get_current_user_or_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> tuple[Optional[User], Optional[dict]]:
    """
    Get authentication via JWT token OR API key.
    Returns (user, api_key_auth) where one will be set and other None.

    Args:
        credentials: Optional JWT bearer token
        x_api_key: Optional API key from header
        db: Database session

    Returns:
        Tuple of (User or None, api_key_auth dict or None)
    """
    # Try API key first
    if x_api_key:
        api_key_auth = await get_api_key_auth(x_api_key, db)
        if api_key_auth:
            return (None, api_key_auth)

    # Try JWT token
    if credentials:
        try:
            token = credentials.credentials
            token_data = verify_token(token, token_type="access")

            if token_data:
                user = db.query(User).filter(User.id == token_data.sub).first()
                # Skip email verification check in test mode
                skip_email_verification = (
                    os.environ.get("SKIP_EMAIL_VERIFICATION", "").lower() == "true"
                )
                if user and user.is_active and (user.is_email_verified or skip_email_verification):
                    return (user, None)
        except Exception:
            pass

    return (None, None)


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Require authentication via JWT token OR API key.
    Returns auth context with organization_id and permissions.

    Raises HTTPException 401 if neither auth method is valid.
    """
    user, api_key_auth = await get_current_user_or_api_key(credentials, x_api_key, db)

    if user:
        # JWT authentication
        return {
            "user": user,
            "organization_id": user.organization_id,
            "permissions": ["*"],  # Full permissions for authenticated users
            "auth_type": "jwt",
        }

    if api_key_auth:
        # API key authentication
        return {
            "user": None,
            "organization_id": api_key_auth["organization_id"],
            "permissions": api_key_auth["permissions"],
            "auth_type": "api_key",
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_flexible(
    auth_context: dict = Depends(require_auth), db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token or create a virtual user for API key auth.
    Use this for endpoints that need user context but should work with API keys.

    For API key auth, returns a virtual user with organization_id set.
    """
    if auth_context["auth_type"] == "jwt":
        return auth_context["user"]

    # For API key auth, create a virtual user object with organization_id
    # This allows existing endpoints to work without modification
    # Use None for id since uploaded_by_id is nullable in most models
    virtual_user = User(
        id=None,
        organization_id=auth_context["organization_id"],
        email="api-key@system",
        is_active=True,
        is_email_verified=True,
    )
    return virtual_user


def require_permission(permission: str):
    """
    Dependency factory that requires a specific permission.

    Usage:
        @router.post("/items")
        async def create_item(
            current_user: User = Depends(require_permission("items.create"))
        ):
            ...

    Args:
        permission: The permission string required (e.g., "reference_data.create")

    Returns:
        A dependency function that validates the permission and returns the user
    """

    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        # Check if user has the required permission
        # For now, we allow all authenticated users - permission system can be expanded later
        # In production, you would check current_user.roles or a permissions table
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is not active",
            )

        # TODO: Implement full permission checking against roles/permissions
        # For now, we trust authenticated users
        return current_user

    return permission_checker
