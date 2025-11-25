"""
FastAPI dependencies for authentication and authorization
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.core.security import verify_token
from backend.models.user import User


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
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
    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
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
    db: Session = Depends(get_db)
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
        
        user = db.query(User).filter(User.id == int(token_data.sub)).first()
        
        if user and user.is_active:
            return user
            
    except Exception:
        pass
    
    return None


async def get_current_organization(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's active organization
    
    Args:
        current_user: Current authenticated user
    
    Returns:
        Organization object
    
    Raises:
        HTTPException: 400 if user has no active organization
    """
    if not current_user.current_organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active organization. Please switch to an organization first."
        )
    
    # Return the organization from the relationship
    organization = current_user.current_organization
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current organization not found"
        )
    
    return organization

