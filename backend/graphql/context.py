"""
GraphQL context for authentication and organization scope.
"""
from typing import Optional
from fastapi import Request, Depends
from sqlalchemy.orm import Session
from strawberry.fastapi import BaseContext

from backend.models.user import User
from backend.db.session import get_db
from backend.core.security import verify_token


class GraphQLContext(BaseContext):
    """
    GraphQL context with request, database, and authenticated user.
    """
    def __init__(self, request: Request, db: Session):
        self.request = request
        self.db = db
        self._user: Optional[User] = None
        self._user_loaded = False
    
    @property
    def user(self) -> Optional[User]:
        """
        Get authenticated user from JWT token.
        Lazy loads user on first access.
        """
        if not self._user_loaded:
            self._user = self._get_user_from_token()
            self._user_loaded = True
        return self._user
    
    def _get_user_from_token(self) -> Optional[User]:
        """Extract user from JWT token in Authorization header."""
        auth_header = self.request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.split(" ")[1]
        try:
            token_data = verify_token(token, token_type="access")
            if not token_data or not token_data.sub:
                return None
            
            user = self.db.query(User).filter(User.id == int(token_data.sub)).first()
            return user
        except Exception:
            return None
    
    @property
    def organization_id(self) -> Optional[int]:
        """Get current organization ID from authenticated user."""
        if self.user:
            return self.user.organization_id
        return None
    
    def require_auth(self) -> User:
        """
        Require authentication, raise error if not authenticated.
        """
        if not self.user:
            raise Exception("Authentication required")
        return self.user
    
    def require_permission(self, permission: str) -> User:
        """
        Check if user has permission, raise error if not.
        """
        user = self.require_auth()
        
        # Import here to avoid circular dependency
        from backend.core.permissions import has_permission
        
        if not has_permission(self.db, user, permission):
            raise Exception(f"Permission denied: {permission}")
        
        return user


async def get_graphql_context(
    request: Request,
    db: Session = Depends(get_db)
) -> GraphQLContext:
    """
    Dependency to create GraphQL context.
    """
    return GraphQLContext(request, db)
