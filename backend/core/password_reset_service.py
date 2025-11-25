"""
Password reset service with token generation and validation.
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from backend.models.user import User
from backend.core.security import get_password_hash
from backend.core.cache import cache


class PasswordResetService:
    """Service for managing password reset tokens and flows."""
    
    # Token expiration time
    TOKEN_EXPIRATION_HOURS = 1
    
    # Cache key prefix
    CACHE_PREFIX = "password_reset:"
    
    @classmethod
    def generate_reset_token(cls) -> str:
        """Generate a secure random reset token."""
        return secrets.token_urlsafe(32)
    
    @classmethod
    async def create_reset_token(cls, email: str, db: AsyncSession) -> Optional[str]:
        """
        Create a password reset token for a user.
        
        Args:
            email: User's email address
            db: Database session
        
        Returns:
            Reset token if user exists, None otherwise
        """
        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Don't reveal if user exists or not (security)
            return None
        
        # Generate token
        token = cls.generate_reset_token()
        
        # Store in cache with expiration
        cache_key = f"{cls.CACHE_PREFIX}{token}"
        await cache.set(
            cache_key,
            {
                "user_id": user.id,
                "email": user.email,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            expire=cls.TOKEN_EXPIRATION_HOURS * 3600,
        )
        
        return token
    
    @classmethod
    async def validate_reset_token(cls, token: str) -> Optional[dict]:
        """
        Validate a password reset token.
        
        Args:
            token: Reset token to validate
        
        Returns:
            Token data if valid, None otherwise
        """
        cache_key = f"{cls.CACHE_PREFIX}{token}"
        token_data = await cache.get(cache_key)
        return token_data
    
    @classmethod
    async def reset_password(
        cls,
        token: str,
        new_password: str,
        db: AsyncSession,
    ) -> bool:
        """
        Reset user password with a valid token.
        
        Args:
            token: Reset token
            new_password: New password (plain text)
            db: Database session
        
        Returns:
            True if password was reset, False otherwise
        """
        # Validate token
        token_data = await cls.validate_reset_token(token)
        if not token_data:
            return False
        
        user_id = token_data.get("user_id")
        if not user_id:
            return False
        
        # Hash new password
        hashed_password = get_password_hash(new_password)
        
        # Update user password
        await db.execute(
            update(User)
            .where(User.id == user_id, User.is_active == True)
            .values(hashed_password=hashed_password)
        )
        await db.commit()
        
        # Invalidate token (delete from cache)
        cache_key = f"{cls.CACHE_PREFIX}{token}"
        await cache.delete(cache_key)
        
        return True
    
    @classmethod
    async def invalidate_token(cls, token: str) -> None:
        """
        Invalidate a reset token.
        
        Args:
            token: Token to invalidate
        """
        cache_key = f"{cls.CACHE_PREFIX}{token}"
        await cache.delete(cache_key)
