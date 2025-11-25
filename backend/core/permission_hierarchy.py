"""
Permission hierarchy and inheritance system.

This module provides hierarchical permission checking where:
1. Roles inherit permissions from lower-level roles
2. Permissions have parent-child relationships (e.g., delete implies read)
3. Automatic permission expansion based on hierarchies
"""
from typing import Dict, Set, List, Optional
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.models.rbac import Role, Permission


# Permission hierarchy: child permissions inherit from parents
# Format: "permission_name": ["implied_permission1", "implied_permission2"]
PERMISSION_HIERARCHY: Dict[str, List[str]] = {
    # Content permissions
    "content.delete": ["content.update", "content.read"],
    "content.update": ["content.read"],
    "content.publish": ["content.update", "content.read"],
    
    # Content type permissions
    "content_types.delete": ["content_types.update", "content_types.read"],
    "content_types.update": ["content_types.read"],
    
    # User management permissions
    "users.delete": ["users.update", "users.read"],
    "users.update": ["users.read"],
    "users.invite": ["users.read"],
    
    # Role management permissions
    "roles.delete": ["roles.update", "roles.read"],
    "roles.update": ["roles.read"],
    "roles.assign": ["roles.read"],
    
    # Permission management
    "permissions.manage": ["permissions.read"],
    
    # Media permissions
    "media.delete": ["media.update", "media.read"],
    "media.update": ["media.read"],
    
    # Translation permissions
    "translations.delete": ["translations.update", "translations.read"],
    "translations.update": ["translations.read"],
    
    # SEO permissions
    "seo.update": ["seo.read"],
    
    # Webhook permissions
    "webhooks.delete": ["webhooks.update", "webhooks.read"],
    "webhooks.update": ["webhooks.read"],
    "webhooks.test": ["webhooks.read"],
    
    # Theme permissions
    "themes.delete": ["themes.update", "themes.read"],
    "themes.update": ["themes.read"],
    "themes.manage": ["themes.update", "themes.read"],
    
    # Template permissions
    "templates.delete": ["templates.update", "templates.read"],
    "templates.update": ["templates.read"],
    "templates.apply": ["templates.read"],
    
    # API key permissions
    "api_keys.delete": ["api_keys.update", "api_keys.read"],
    "api_keys.update": ["api_keys.read"],
    
    # Organization/settings permissions
    "organization.delete": ["organization.update", "organization.read"],
    "organization.update": ["organization.read"],
    "settings.update": ["settings.read"],
}


# Role hierarchy levels (higher number = more permissions)
ROLE_LEVELS: Dict[str, int] = {
    "super_admin": 100,      # System-wide admin
    "org_admin": 90,         # Organization administrator
    "admin": 80,             # Full admin within org
    "editor": 60,            # Can edit and publish content
    "contributor": 40,       # Can create and edit own content
    "viewer": 20,            # Read-only access
}


class PermissionHierarchyService:
    """Service for managing permission inheritance and role hierarchies."""
    
    @staticmethod
    def expand_permissions(permission_name: str) -> Set[str]:
        """
        Expand a permission to include all implied permissions.
        
        Args:
            permission_name: The permission to expand
            
        Returns:
            Set of all permissions including the original and implied ones
        """
        expanded = {permission_name}
        
        # Add direct children
        if permission_name in PERMISSION_HIERARCHY:
            for implied in PERMISSION_HIERARCHY[permission_name]:
                # Recursively expand implied permissions
                expanded.update(PermissionHierarchyService.expand_permissions(implied))
        
        return expanded
    
    @staticmethod
    def get_all_permissions_for_user(user: User, db: Session) -> Set[str]:
        """
        Get all permissions for a user, including inherited ones.
        
        Args:
            user: User object
            db: Database session
            
        Returns:
            Set of all permission names (expanded with inheritance)
        """
        all_permissions: Set[str] = set()
        
        # Super admin gets all permissions
        if any(role.name == "super_admin" for role in user.roles):
            return {"*"}  # Special marker for all permissions
        
        for role in user.roles:
            # Only consider roles in user's organization
            if role.organization_id != user.organization_id:
                continue
            
            # Add role's direct permissions
            for permission in role.permissions:
                # Expand each permission to include implied permissions
                expanded = PermissionHierarchyService.expand_permissions(permission.name)
                all_permissions.update(expanded)
            
            # Add permissions from lower-level roles (role hierarchy)
            lower_roles = PermissionHierarchyService.get_inherited_roles(role, db)
            for lower_role in lower_roles:
                for permission in lower_role.permissions:
                    expanded = PermissionHierarchyService.expand_permissions(permission.name)
                    all_permissions.update(expanded)
        
        return all_permissions
    
    @staticmethod
    def get_inherited_roles(role: Role, db: Session) -> List[Role]:
        """
        Get all roles that this role inherits from (lower-level roles).
        
        Args:
            role: The role to check
            db: Database session
            
        Returns:
            List of roles with lower levels
        """
        inherited_roles = []
        
        # Get role level
        role_level = role.level
        if role.name in ROLE_LEVELS:
            role_level = ROLE_LEVELS[role.name]
        
        # Find all roles in same organization with lower level
        org_roles = db.query(Role).filter(
            Role.organization_id == role.organization_id,
            Role.id != role.id  # Don't include self
        ).all()
        
        for other_role in org_roles:
            other_level = other_role.level
            if other_role.name in ROLE_LEVELS:
                other_level = ROLE_LEVELS[other_role.name]
            
            # If other role has lower level, this role inherits from it
            if other_level < role_level:
                inherited_roles.append(other_role)
        
        return inherited_roles
    
    @staticmethod
    def has_permission_with_inheritance(
        user: User,
        permission_name: str,
        db: Session,
        content_type_id: Optional[int] = None,
        field_name: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission, considering inheritance.
        
        Args:
            user: User object
            permission_name: Permission to check
            db: Database session
            content_type_id: Optional content type filter
            field_name: Optional field name filter
            
        Returns:
            True if user has permission (directly or through inheritance)
        """
        # Get all expanded permissions
        all_permissions = PermissionHierarchyService.get_all_permissions_for_user(user, db)
        
        # Super admin check
        if "*" in all_permissions:
            return True
        
        # Check if permission is in expanded set
        if permission_name in all_permissions:
            # If no content_type_id or field_name specified, we're done
            if content_type_id is None and field_name is None:
                return True
            
            # Need to check specific permission objects for content type / field scoping
            for role in user.roles:
                if role.organization_id != user.organization_id:
                    continue
                
                for permission in role.permissions:
                    # Check if this permission or any of its parents match
                    expanded = PermissionHierarchyService.expand_permissions(permission.name)
                    if permission_name not in expanded:
                        continue
                    
                    # Check content type scope
                    if content_type_id is not None:
                        if permission.content_type_id is not None and permission.content_type_id != content_type_id:
                            continue
                    
                    # Check field scope
                    if field_name is not None:
                        if permission.field_name is not None and permission.field_name != field_name:
                            continue
                    
                    return True
        
        return False
    
    @staticmethod
    def get_role_level(role: Role) -> int:
        """
        Get the hierarchy level for a role.
        
        Args:
            role: Role object
            
        Returns:
            Hierarchy level (higher = more permissions)
        """
        # Check if role name matches system role
        if role.name in ROLE_LEVELS:
            return ROLE_LEVELS[role.name]
        
        # Return role's level field
        return role.level if role.level else 0
    
    @staticmethod
    def can_manage_role(manager: User, target_role: Role, db: Session) -> bool:
        """
        Check if a user can manage (assign/modify) a specific role.
        Users can only manage roles with lower levels than their highest role.
        
        Args:
            manager: User attempting to manage the role
            target_role: Role being managed
            db: Database session
            
        Returns:
            True if manager can manage the target role
        """
        # Super admin can manage all roles
        if any(role.name == "super_admin" for role in manager.roles):
            return True
        
        # Get manager's highest role level
        manager_max_level = 0
        for role in manager.roles:
            if role.organization_id == manager.organization_id:
                level = PermissionHierarchyService.get_role_level(role)
                manager_max_level = max(manager_max_level, level)
        
        # Get target role level
        target_level = PermissionHierarchyService.get_role_level(target_role)
        
        # Manager must have higher level than target
        return manager_max_level > target_level
    
    @staticmethod
    def suggest_role_level(role_name: str) -> int:
        """
        Suggest an appropriate level for a role based on its name.
        
        Args:
            role_name: Name of the role
            
        Returns:
            Suggested hierarchy level
        """
        role_name_lower = role_name.lower()
        
        # Check for known role types
        if "admin" in role_name_lower or "administrator" in role_name_lower:
            if "super" in role_name_lower or "system" in role_name_lower:
                return 100
            elif "org" in role_name_lower or "organization" in role_name_lower:
                return 90
            else:
                return 80
        elif "editor" in role_name_lower or "publisher" in role_name_lower:
            return 60
        elif "author" in role_name_lower or "contributor" in role_name_lower:
            return 40
        elif "viewer" in role_name_lower or "reader" in role_name_lower:
            return 20
        
        # Default level for custom roles
        return 50
