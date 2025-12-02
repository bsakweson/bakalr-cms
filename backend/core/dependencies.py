"""
FastAPI dependencies for authentication and authorization
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.security import verify_password, verify_token
from backend.db.session import get_db
from backend.models.api_key import APIKey
from backend.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token

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

    # Check if email is verified
    if not user.is_email_verified:
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
                if user and user.is_active and user.is_email_verified:
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
    virtual_user = User(
        id="api-key-user",
        organization_id=auth_context["organization_id"],
        email="api-key@system",
        is_active=True,
        is_email_verified=True,
    )
    return virtual_user
