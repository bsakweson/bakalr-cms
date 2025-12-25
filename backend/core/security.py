"""
Security utilities for password hashing and JWT tokens
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.jwt_keys import jwt_key_manager

# JWT Algorithm - RS256 for asymmetric signing
JWT_ALGORITHM = "RS256"

# bcrypt has a 72-byte limit on password input
BCRYPT_MAX_LENGTH = 72


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _prepare_secret_for_bcrypt(secret: str) -> bytes:
    """
    Prepare a secret for bcrypt hashing, handling long secrets safely.

    bcrypt has a 72-byte input limit. Secrets longer than this are pre-hashed
    with SHA-256 and base64-encoded to ensure consistent behavior and full
    entropy usage regardless of input length.

    Args:
        secret: The plain text secret

    Returns:
        Bytes suitable for bcrypt hashing (guaranteed <= 72 bytes)
    """
    secret_bytes = secret.encode("utf-8")

    if len(secret_bytes) > BCRYPT_MAX_LENGTH:
        # Pre-hash with SHA-256 and base64 encode
        # SHA-256 produces 32 bytes, base64 encoded = 44 bytes (well under 72)
        sha256_hash = hashlib.sha256(secret_bytes).digest()
        return base64.b64encode(sha256_hash)

    return secret_bytes


def hash_secret(secret: str) -> str:
    """
    Hash a secret (password, API key, client secret, etc.) for secure storage.

    This function handles secrets of any length safely by pre-hashing long
    secrets with SHA-256 before bcrypt.

    Args:
        secret: The plain text secret

    Returns:
        Hashed secret string
    """
    prepared = _prepare_secret_for_bcrypt(secret)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prepared, salt)
    return hashed.decode("utf-8")


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """
    Verify a secret against its hash.

    This function handles secrets of any length safely by pre-hashing long
    secrets with SHA-256 before bcrypt verification.

    Args:
        plain_secret: The plain text secret to verify
        hashed_secret: The stored hash to verify against

    Returns:
        True if the secret matches, False otherwise
    """
    try:
        prepared = _prepare_secret_for_bcrypt(plain_secret)
        return bcrypt.checkpw(prepared, hashed_secret.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_api_key() -> str:
    """
    Generate a secure random API key.

    Returns:
        URL-safe 32-byte random string (43 characters)
    """
    return f"bk_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        api_key: The plain text API key

    Returns:
        Hashed API key
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(api_key.encode("utf-8"), salt)
    return hashed.decode("utf-8")


class TokenData(BaseModel):
    """Token payload data"""

    user_id: int
    organization_id: int
    email: str
    roles: list[str] = []
    exp: Optional[datetime] = None


class Token(BaseModel):
    """Token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT token payload"""

    sub: str  # user_id (UUID as string)
    org_id: str  # organization_id (UUID as string)
    email: str
    roles: list[str] = []
    exp: Optional[int] = None
    type: str = "access"  # access or refresh
    session_id: Optional[str] = None  # Session ID for logout functionality


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token using RS256 algorithm.

    Args:
        data: Token payload data
        expires_delta: Token expiration time (default: 30 minutes)

    Returns:
        Encoded JWT token signed with RSA private key
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add standard JWT claims
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": settings.JWT_ISSUER,
            "type": "access",
        }
    )

    # Get private key PEM for jose library
    from cryptography.hazmat.primitives import serialization

    private_key_pem = jwt_key_manager.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    encoded_jwt = jwt.encode(
        to_encode, private_key_pem, algorithm=JWT_ALGORITHM, headers={"kid": jwt_key_manager.key_id}
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token using RS256 algorithm.

    Args:
        data: Token payload data

    Returns:
        Encoded JWT refresh token signed with RSA private key
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Add standard JWT claims
    to_encode.update(
        {
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "iss": settings.JWT_ISSUER,
            "type": "refresh",
        }
    )

    # Get private key PEM for jose library
    from cryptography.hazmat.primitives import serialization

    private_key_pem = jwt_key_manager.private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    encoded_jwt = jwt.encode(
        to_encode, private_key_pem, algorithm=JWT_ALGORITHM, headers={"kid": jwt_key_manager.key_id}
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """
    Verify and decode JWT token using RS256 algorithm.

    Args:
        token: JWT token string
        token_type: Expected token type (access or refresh)

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        # Get public key PEM for jose library
        from cryptography.hazmat.primitives import serialization

        public_key_pem = jwt_key_manager.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        payload = jwt.decode(
            token,
            public_key_pem,
            algorithms=[JWT_ALGORITHM],
            options={"verify_aud": False},  # We don't use audience claim
        )

        # Verify token type
        if payload.get("type") != token_type:
            return None

        # Extract token data
        token_data = TokenPayload(
            sub=payload.get("sub"),
            org_id=payload.get("org_id"),
            email=payload.get("email"),
            roles=payload.get("roles", []),
            exp=payload.get("exp"),
            type=payload.get("type"),
            session_id=payload.get("session_id"),
        )

        return token_data

    except JWTError:
        return None


def create_token_pair(
    user_id: UUID,
    organization_id: UUID,
    email: str,
    roles: list[str],
    permissions: list[str] = None,
    api_scopes: list[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    is_organization_owner: bool = False,
) -> Token:
    """
    Create access and refresh token pair

    Args:
        user_id: User ID (UUID)
        organization_id: Organization ID (UUID)
        email: User email
        roles: List of role names
        permissions: List of CMS permission names (e.g., ["content.read", "user.manage"])
        api_scopes: List of API scope names for external platforms (e.g., ["inventory.read", "orders.create"])
        first_name: User's first name (optional)
        last_name: User's last name (optional)
        is_organization_owner: Whether user owns the organization (optional)

    Returns:
        Token object with access_token and refresh_token
    """
    # Build full name from first and last name
    full_name = ""
    if first_name and last_name:
        full_name = f"{first_name} {last_name}"
    elif first_name:
        full_name = first_name
    elif last_name:
        full_name = last_name

    token_data = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "email": email,
        "roles": roles,
        "permissions": permissions or [],
        "api_scopes": api_scopes or [],  # Boutique platform permissions
        # Standard OIDC claims for user profile
        "name": full_name,
        "given_name": first_name or "",
        "family_name": last_name or "",
        # Custom claims
        "is_organization_owner": is_organization_owner,
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return Token(access_token=access_token, refresh_token=refresh_token)
