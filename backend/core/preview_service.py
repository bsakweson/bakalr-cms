"""
Content preview service for generating and validating preview tokens.
Uses JWT tokens with expiration for secure preview access.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from backend.core.config import settings


class PreviewService:
    """Service for managing content preview tokens."""
    
    @staticmethod
    def generate_preview_token(
        content_entry_id: int,
        organization_id: int,
        expires_in_hours: int = 24
    ) -> tuple[str, datetime]:
        """
        Generate a signed preview token for content entry.
        
        Args:
            content_entry_id: ID of the content entry
            organization_id: ID of the organization
            expires_in_hours: Token validity in hours (default 24)
            
        Returns:
            Tuple of (token, expiration_datetime)
        """
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
        
        payload = {
            "content_entry_id": content_entry_id,
            "organization_id": organization_id,
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
            "type": "preview"
        }
        
        token = jwt.encode(
            payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        return token, expires_at
    
    @staticmethod
    def validate_preview_token(token: str) -> Optional[dict]:
        """
        Validate and decode a preview token.
        
        Args:
            token: The preview token to validate
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            
            # Verify it's a preview token
            if payload.get("type") != "preview":
                return None
                
            return payload
            
        except JWTError:
            return None
    
    @staticmethod
    def generate_preview_url(
        base_url: str,
        content_entry_id: int,
        token: str
    ) -> str:
        """
        Generate a full preview URL with token.
        
        Args:
            base_url: Base URL of the application
            content_entry_id: ID of the content entry
            token: Preview token
            
        Returns:
            Full preview URL
        """
        return f"{base_url}/preview/{content_entry_id}?token={token}"
