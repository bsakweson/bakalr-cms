"""
RBAC permission checking and enforcement
"""
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.rbac import Role, Permission
from backend.core.permission_hierarchy import PermissionHierarchyService


class PermissionChecker:
    """Utility class for checking user permissions"""
    
    @staticmethod
    def has_permission(
        user: User,
        permission_name: str,
        db: Session,
        content_type_id: Optional[int] = None,
        field_name: Optional[str] = None,
        use_hierarchy: bool = True
    ) -> bool:
        """
        Check if user has a specific permission
        
        Args:
            user: User object
            permission_name: Permission name to check
            db: Database session
            content_type_id: Optional content type ID for content-specific permissions
            field_name: Optional field name for field-level permissions
            use_hierarchy: Whether to use permission hierarchy (default: True)
        
        Returns:
            True if user has permission, False otherwise
        """
        # Check if user is the organization owner - owners have all permissions
        from backend.models.organization import Organization
        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if org and org.owner_id == user.id:
            return True
        
        # Use hierarchy if enabled
        if use_hierarchy:
            return PermissionHierarchyService.has_permission_with_inheritance(
                user, permission_name, db, content_type_id, field_name
            )
        
        # Original direct permission check (no hierarchy)
        # Super admin has all permissions
        if any(role.name == "super_admin" for role in user.roles):
            return True
        
        # Check if user has the permission through any of their roles
        for role in user.roles:
            if role.organization_id != user.organization_id:
                continue
                
            for permission in role.permissions:
                # Match permission name
                if permission.name != permission_name:
                    continue
                
                # Check content type scope
                if content_type_id is not None:
                    # Permission must either be global (NULL) or match the content type
                    if permission.content_type_id is not None and permission.content_type_id != content_type_id:
                        continue
                
                # Check field-level scope
                if field_name is not None:
                    # Permission must either be for all fields (NULL) or match the specific field
                    if permission.field_name is not None and permission.field_name != field_name:
                        continue
                
                # All checks passed
                return True
        
        return False
    
    @staticmethod
    def has_any_permission(
        user: User,
        permission_names: List[str],
        db: Session
    ) -> bool:
        """
        Check if user has any of the specified permissions
        
        Args:
            user: User object
            permission_names: List of permission names
            db: Database session
        
        Returns:
            True if user has at least one permission, False otherwise
        """
        for permission_name in permission_names:
            if PermissionChecker.has_permission(user, permission_name, db):
                return True
        return False
    
    @staticmethod
    def has_all_permissions(
        user: User,
        permission_names: List[str],
        db: Session
    ) -> bool:
        """
        Check if user has all of the specified permissions
        
        Args:
            user: User object
            permission_names: List of permission names
            db: Database session
        
        Returns:
            True if user has all permissions, False otherwise
        """
        for permission_name in permission_names:
            if not PermissionChecker.has_permission(user, permission_name, db):
                return False
        return True
    
    @staticmethod
    def has_role(user: User, role_name: str) -> bool:
        """
        Check if user has a specific role
        
        Args:
            user: User object
            role_name: Role name to check
        
        Returns:
            True if user has role, False otherwise
        """
        return any(
            role.name == role_name and role.organization_id == user.organization_id
            for role in user.roles
        )
    
    @staticmethod
    def get_user_permissions(user: User, db: Session = None, expand: bool = True) -> List[str]:
        """
        Get all permissions for a user
        
        Args:
            user: User object
            db: Database session (required if expand=True)
            expand: Whether to expand permissions with hierarchy (default: True)
        
        Returns:
            List of permission names
        """
        if expand and db:
            # Get expanded permissions with hierarchy
            expanded = PermissionHierarchyService.get_all_permissions_for_user(user, db)
            # Filter out the special "*" marker
            return [p for p in expanded if p != "*"]
        
        # Direct permissions only
        permissions = set()
        
        for role in user.roles:
            if role.organization_id != user.organization_id:
                continue
                
            for permission in role.permissions:
                permissions.add(permission.name)
        
        return list(permissions)
    
    @staticmethod
    def require_permission(
        user: User,
        permission_name: str,
        db: Session
    ) -> None:
        """
        Raise exception if user doesn't have permission
        
        Args:
            user: User object
            permission_name: Required permission name
            db: Database session
        
        Raises:
            HTTPException: 403 Forbidden if permission is missing
        """
        if not PermissionChecker.has_permission(user, permission_name, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission_name}' required"
            )
    
    @staticmethod
    def require_any_permission(
        user: User,
        permission_names: List[str],
        db: Session
    ) -> None:
        """
        Raise exception if user doesn't have any of the permissions
        
        Args:
            user: User object
            permission_names: List of permission names
            db: Database session
        
        Raises:
            HTTPException: 403 Forbidden if no permissions match
        """
        if not PermissionChecker.has_any_permission(user, permission_names, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: one of {permission_names} required"
            )
    
    @staticmethod
    def require_role(user: User, role_name: str) -> None:
        """
        Raise exception if user doesn't have role
        
        Args:
            user: User object
            role_name: Required role name
        
        Raises:
            HTTPException: 403 Forbidden if role is missing
        """
        if not PermissionChecker.has_role(user, role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: '{role_name}'"
            )
    
    @staticmethod
    def is_organization_member(user: User, organization_id: int) -> bool:
        """
        Check if user belongs to specified organization
        
        Args:
            user: User object
            organization_id: Organization ID to check
        
        Returns:
            True if user is member, False otherwise
        """
        return user.organization_id == organization_id
    
    @staticmethod
    def require_organization_access(user: User, organization_id: int) -> None:
        """
        Raise exception if user doesn't belong to organization
        
        Args:
            user: User object
            organization_id: Required organization ID
        
        Raises:
            HTTPException: 403 Forbidden if not organization member
        """
        if not PermissionChecker.is_organization_member(user, organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not a member of this organization"
            )
    
    @staticmethod
    def has_field_permission(
        user: User,
        permission_name: str,
        content_type_id: int,
        field_name: str,
        db: Session
    ) -> bool:
        """
        Check if user has permission for a specific field in a content type
        
        Args:
            user: User object
            permission_name: Permission name (e.g., "content.read", "content.write")
            content_type_id: Content type ID
            field_name: Field name to check
            db: Database session
        
        Returns:
            True if user has field permission, False otherwise
        """
        return PermissionChecker.has_permission(
            user, 
            permission_name, 
            db, 
            content_type_id=content_type_id,
            field_name=field_name
        )
    
    @staticmethod
    def get_accessible_fields(
        user: User,
        permission_name: str,
        content_type_id: int,
        all_fields: List[str],
        db: Session
    ) -> List[str]:
        """
        Get list of fields user can access for a content type
        
        Args:
            user: User object
            permission_name: Permission name to check
            content_type_id: Content type ID
            all_fields: List of all field names in the content type
            db: Database session
        
        Returns:
            List of accessible field names
        """
        # Super admin has access to all fields
        if any(role.name == "super_admin" for role in user.roles):
            return all_fields
        
        accessible_fields = []
        
        for field_name in all_fields:
            # Check if user has global permission (applies to all fields)
            if PermissionChecker.has_permission(user, permission_name, db, content_type_id=content_type_id):
                accessible_fields.append(field_name)
            # Or specific field permission
            elif PermissionChecker.has_field_permission(user, permission_name, content_type_id, field_name, db):
                accessible_fields.append(field_name)
        
        return accessible_fields
    
    @staticmethod
    def filter_fields_by_permission(
        user: User,
        permission_name: str,
        content_type_id: int,
        data: dict,
        db: Session
    ) -> dict:
        """
        Filter dictionary to only include fields user has permission for
        
        Args:
            user: User object
            permission_name: Permission name (e.g., "content.read")
            content_type_id: Content type ID
            data: Dictionary with field data
            db: Database session
        
        Returns:
            Filtered dictionary with only accessible fields
        """
        # Super admin has access to all fields
        if any(role.name == "super_admin" for role in user.roles):
            return data
        
        accessible_fields = PermissionChecker.get_accessible_fields(
            user,
            permission_name,
            content_type_id,
            list(data.keys()),
            db
        )
        
        return {k: v for k, v in data.items() if k in accessible_fields}


# Convenience functions for hierarchy features
def can_user_manage_role(manager: User, target_role: Role, db: Session) -> bool:
    """
    Check if a user can manage (assign/modify) a specific role.
    
    Args:
        manager: User attempting to manage the role
        target_role: Role being managed
        db: Database session
        
    Returns:
        True if manager can manage the target role
    """
    return PermissionHierarchyService.can_manage_role(manager, target_role, db)


def get_role_hierarchy_level(role: Role) -> int:
    """
    Get the hierarchy level for a role.
    
    Args:
        role: Role object
        
    Returns:
        Hierarchy level (higher = more permissions)
    """
    return PermissionHierarchyService.get_role_level(role)


def suggest_role_level(role_name: str) -> int:
    """
    Suggest an appropriate level for a role based on its name.
    
    Args:
        role_name: Name of the role
        
    Returns:
        Suggested hierarchy level
    """
    return PermissionHierarchyService.suggest_role_level(role_name)


def get_inherited_roles(role: Role, db: Session) -> List[Role]:
    """
    Get all roles that this role inherits from (lower-level roles).
    
    Args:
        role: The role to check
        db: Database session
        
    Returns:
        List of roles with lower levels
    """
    return PermissionHierarchyService.get_inherited_roles(role, db)


def expand_permission(permission_name: str) -> List[str]:
    """
    Expand a permission to show all implied permissions.
    
    Args:
        permission_name: Permission to expand
        
    Returns:
        List of all permissions (including the original)
    """
    return list(PermissionHierarchyService.expand_permissions(permission_name))
