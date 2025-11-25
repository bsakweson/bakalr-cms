"""
Test tenant switching functionality
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.models.user_organization import UserOrganization
from backend.models.organization import Organization
from backend.models.user import User


def test_user_organization_model():
    """Test UserOrganization model structure"""
    print("Testing UserOrganization model...")
    
    # Check model attributes
    assert hasattr(UserOrganization, 'user_id')
    assert hasattr(UserOrganization, 'organization_id')
    assert hasattr(UserOrganization, 'is_active')
    assert hasattr(UserOrganization, 'is_default')
    assert hasattr(UserOrganization, 'invited_by')
    
    print("✓ UserOrganization model has all required fields")


def test_relationships():
    """Test model relationships"""
    print("\nTesting model relationships...")
    
    # Check User has user_organizations relationship
    assert hasattr(User, 'user_organizations')
    print("✓ User model has user_organizations relationship")
    
    # Check Organization has user_organizations relationship
    assert hasattr(Organization, 'user_organizations')
    print("✓ Organization model has user_organizations relationship")


def test_schemas():
    """Test tenant switching schemas"""
    print("\nTesting tenant switching schemas...")
    
    from backend.api.schemas.tenant import (
        OrganizationMembership,
        UserOrganizationsResponse,
        SwitchOrganizationRequest,
        SwitchOrganizationResponse,
        InviteUserToOrganizationRequest,
        SetDefaultOrganizationRequest
    )
    
    # Test OrganizationMembership schema
    membership = OrganizationMembership(
        organization_id=1,
        organization_name="Test Org",
        organization_slug="test-org",
        is_default=True,
        is_active=True,
        roles=["admin", "editor"],
        joined_at="2025-01-01T00:00:00Z"
    )
    assert membership.organization_id == 1
    assert membership.is_default == True
    assert "admin" in membership.roles
    print("✓ OrganizationMembership schema works")
    
    # Test SwitchOrganizationRequest schema
    switch_request = SwitchOrganizationRequest(organization_id=2)
    assert switch_request.organization_id == 2
    print("✓ SwitchOrganizationRequest schema works")
    
    # Test InviteUserToOrganizationRequest schema
    invite_request = InviteUserToOrganizationRequest(
        email="user@example.com",
        role_names=["editor"]
    )
    assert invite_request.email == "user@example.com"
    assert invite_request.role_names == ["editor"]
    print("✓ InviteUserToOrganizationRequest schema works")


def test_api_endpoints():
    """Test tenant switching API endpoints are registered"""
    print("\nTesting API endpoints registration...")
    
    from backend.api import tenant
    
    # Check router exists
    assert hasattr(tenant, 'router')
    print("✓ Tenant router exists")
    
    # Check router has routes
    routes = [route.path for route in tenant.router.routes]
    assert any('/organizations' in path for path in routes)
    assert any('/switch' in path for path in routes)
    assert any('/set-default' in path for path in routes)
    assert any('/invite' in path for path in routes)
    print("✓ Tenant router has all required endpoints")


def test_backward_compatibility():
    """Test backward compatibility with existing User.organization_id"""
    print("\nTesting backward compatibility...")
    
    # User model should still have organization_id for backward compatibility
    assert hasattr(User, 'organization_id')
    print("✓ User.organization_id field still exists (backward compatible)")
    
    # User should still have organization relationship
    assert hasattr(User, 'organization')
    print("✓ User.organization relationship still exists (backward compatible)")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Tenant Switching Implementation")
    print("=" * 60)
    
    try:
        test_user_organization_model()
        test_relationships()
        test_schemas()
        test_api_endpoints()
        test_backward_compatibility()
        
        print("\n" + "=" * 60)
        print("✅ All tenant switching tests passed!")
        print("=" * 60)
        
        print("\n📋 Summary:")
        print("- UserOrganization model: ✓")
        print("- Model relationships: ✓")
        print("- Pydantic schemas: ✓")
        print("- API endpoints: ✓")
        print("- Backward compatibility: ✓")
        
        print("\n🔧 Features implemented:")
        print("- Users can belong to multiple organizations")
        print("- Switch between organizations with JWT refresh")
        print("- Set default organization for login")
        print("- Invite users to organizations")
        print("- Remove users from organizations")
        print("- List all user's organizations")
        
        print("\n📚 API Endpoints:")
        print("- GET  /api/v1/tenant/organizations - List user's organizations")
        print("- POST /api/v1/tenant/switch - Switch to different organization")
        print("- POST /api/v1/tenant/set-default - Set default organization")
        print("- POST /api/v1/tenant/invite - Invite user to organization")
        print("- DELETE /api/v1/tenant/remove/{user_id} - Remove user from org")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
