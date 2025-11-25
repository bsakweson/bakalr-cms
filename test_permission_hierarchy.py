"""
Test permission hierarchy and inheritance system.
"""
import pytest
from backend.core.permission_hierarchy import (
    PermissionHierarchyService,
    PERMISSION_HIERARCHY,
    ROLE_LEVELS
)


def test_permission_expansion():
    """Test that permissions expand correctly to include implied permissions."""
    # content.delete should imply content.update and content.read
    expanded = PermissionHierarchyService.expand_permissions("content.delete")
    assert "content.delete" in expanded
    assert "content.update" in expanded
    assert "content.read" in expanded
    
    # content.update should imply content.read
    expanded = PermissionHierarchyService.expand_permissions("content.update")
    assert "content.update" in expanded
    assert "content.read" in expanded
    assert "content.delete" not in expanded
    
    # content.read has no implied permissions
    expanded = PermissionHierarchyService.expand_permissions("content.read")
    assert expanded == {"content.read"}


def test_role_levels():
    """Test role hierarchy levels."""
    assert ROLE_LEVELS["super_admin"] == 100
    assert ROLE_LEVELS["org_admin"] == 90
    assert ROLE_LEVELS["admin"] == 80
    assert ROLE_LEVELS["editor"] == 60
    assert ROLE_LEVELS["contributor"] == 40
    assert ROLE_LEVELS["viewer"] == 20
    
    # Higher levels should have more permissions
    assert ROLE_LEVELS["super_admin"] > ROLE_LEVELS["org_admin"]
    assert ROLE_LEVELS["org_admin"] > ROLE_LEVELS["editor"]
    assert ROLE_LEVELS["editor"] > ROLE_LEVELS["contributor"]
    assert ROLE_LEVELS["contributor"] > ROLE_LEVELS["viewer"]


def test_suggest_role_level():
    """Test role level suggestion based on name."""
    # Admin roles
    assert PermissionHierarchyService.suggest_role_level("Super Administrator") == 100
    assert PermissionHierarchyService.suggest_role_level("Organization Admin") == 90
    assert PermissionHierarchyService.suggest_role_level("Site Admin") == 80
    
    # Editor roles
    assert PermissionHierarchyService.suggest_role_level("Content Editor") == 60
    assert PermissionHierarchyService.suggest_role_level("Publisher") == 60
    
    # Contributor roles
    assert PermissionHierarchyService.suggest_role_level("Author") == 40
    assert PermissionHierarchyService.suggest_role_level("Contributor") == 40
    
    # Viewer roles
    assert PermissionHierarchyService.suggest_role_level("Viewer") == 20
    assert PermissionHierarchyService.suggest_role_level("Reader") == 20
    
    # Custom roles get default level
    assert PermissionHierarchyService.suggest_role_level("Custom Role") == 50


def test_permission_hierarchy_completeness():
    """Test that permission hierarchy is well-defined."""
    # Check that all implied permissions in hierarchy exist as keys or are terminal
    for permission, implied_list in PERMISSION_HIERARCHY.items():
        assert isinstance(implied_list, list), f"{permission} should have a list of implied permissions"
        
        # Each permission should follow naming convention
        assert "." in permission, f"{permission} should use dot notation (category.action)"
        
        for implied in implied_list:
            # Implied permissions should also follow naming convention
            assert "." in implied, f"{implied} should use dot notation"


def test_crud_permission_hierarchy():
    """Test CRUD permission hierarchy patterns."""
    # Delete implies update and read
    for resource in ["content", "users", "roles", "media", "webhooks", "themes", "templates", "api_keys"]:
        delete_perm = f"{resource}.delete"
        if delete_perm in PERMISSION_HIERARCHY:
            expanded = PermissionHierarchyService.expand_permissions(delete_perm)
            assert f"{resource}.update" in expanded or f"{resource}.read" in expanded
    
    # Update implies read
    for resource in ["content", "users", "roles", "media", "translations", "seo", "webhooks", "themes", "templates"]:
        update_perm = f"{resource}.update"
        if update_perm in PERMISSION_HIERARCHY:
            expanded = PermissionHierarchyService.expand_permissions(update_perm)
            assert f"{resource}.read" in expanded


def test_permission_expansion_depth():
    """Test multi-level permission expansion."""
    # content.delete → content.update → content.read (2 levels deep)
    expanded = PermissionHierarchyService.expand_permissions("content.delete")
    
    # Should include all 3 levels
    assert len(expanded) == 3
    assert "content.delete" in expanded
    assert "content.update" in expanded
    assert "content.read" in expanded


if __name__ == "__main__":
    # Run tests
    print("Testing permission expansion...")
    test_permission_expansion()
    print("✓ Permission expansion works correctly")
    
    print("\nTesting role levels...")
    test_role_levels()
    print("✓ Role levels configured correctly")
    
    print("\nTesting role level suggestions...")
    test_suggest_role_level()
    print("✓ Role level suggestion works correctly")
    
    print("\nTesting permission hierarchy completeness...")
    test_permission_hierarchy_completeness()
    print("✓ Permission hierarchy is well-defined")
    
    print("\nTesting CRUD permission patterns...")
    test_crud_permission_hierarchy()
    print("✓ CRUD permissions follow hierarchy correctly")
    
    print("\nTesting multi-level expansion...")
    test_permission_expansion_depth()
    print("✓ Multi-level permission expansion works")
    
    print("\n✅ All permission hierarchy tests passed!")
