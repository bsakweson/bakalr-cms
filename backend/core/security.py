"""
Security utilities for password hashing and JWT tokens
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
import bcrypt
import secrets
from pydantic import BaseModel

from backend.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


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
    hashed = bcrypt.hashpw(api_key.encode('utf-8'), salt)
    return hashed.decode('utf-8')


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
    sub: str  # user_id
    org_id: int  # organization_id
    email: str
    roles: list[str] = []
    exp: Optional[int] = None
    type: str = "access"  # access or refresh


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time (default: 30 minutes)
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token
    
    Args:
        data: Token payload data
    
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token string
        token_type: Expected token type (access or refresh)
    
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
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
            type=payload.get("type")
        )
        
        return token_data
        
    except JWTError:
        return None


def create_token_pair(user_id: int, organization_id: int, email: str, roles: list[str]) -> Token:
    """
    Create access and refresh token pair
    
    Args:
        user_id: User ID
        organization_id: Organization ID
        email: User email
        roles: List of role names
    
    Returns:
        Token object with access_token and refresh_token
    """
    token_data = {
        "sub": str(user_id),
        "org_id": organization_id,
        "email": email,
        "roles": roles
    }
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token
    )
