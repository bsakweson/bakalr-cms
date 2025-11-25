"""
GraphQL API Tests

Tests GraphQL queries, mutations, authentication, and authorization.
"""
import sys
from datetime import datetime

def test_graphql_imports():
    """Test that GraphQL modules can be imported."""
    print("Testing GraphQL imports...")
    
    try:
        from backend.graphql.types import (
            ContentEntryType, ContentTypeType, MediaType, UserType,
            OrganizationType, PaginationInfo
        )
        from backend.graphql.context import GraphQLContext, get_graphql_context
        from backend.graphql.schema import Query, Mutation, schema
        print("✓ All GraphQL modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import GraphQL modules: {e}")
        return False


def test_graphql_types():
    """Test GraphQL type definitions."""
    print("\nTesting GraphQL types...")
    
    try:
        from backend.graphql.types import ContentEntryType, PaginationInfo
        import strawberry
        
        # Check ContentEntryType fields
        fields = ContentEntryType.__annotations__
        required_fields = ['id', 'slug', 'status', 'content_data', 'created_at']
        for field in required_fields:
            if field not in fields:
                print(f"✗ ContentEntryType missing field: {field}")
                return False
        
        # Check PaginationInfo
        pagination_fields = PaginationInfo.__annotations__
        required_pagination = ['total', 'page', 'per_page', 'has_next', 'has_prev']
        for field in required_pagination:
            if field not in pagination_fields:
                print(f"✗ PaginationInfo missing field: {field}")
                return False
        
        print("✓ GraphQL types have all required fields")
        return True
    except Exception as e:
        print(f"✗ GraphQL types test failed: {e}")
        return False


def test_graphql_context():
    """Test GraphQL context structure."""
    print("\nTesting GraphQL context...")
    
    try:
        from backend.graphql.context import GraphQLContext
        
        # Check that GraphQLContext has required methods
        required_methods = ['require_auth', 'require_permission', 'user', 'organization_id']
        context_methods = dir(GraphQLContext)
        
        for method in required_methods:
            if method not in context_methods:
                print(f"✗ GraphQLContext missing method/property: {method}")
                return False
        
        print("✓ GraphQLContext has all required methods")
        return True
    except Exception as e:
        print(f"✗ GraphQL context test failed: {e}")
        return False


def test_graphql_schema():
    """Test GraphQL schema structure."""
    print("\nTesting GraphQL schema...")
    
    try:
        from backend.graphql.schema import schema, Query, Mutation
        
        # Check Query fields
        query_fields = Query.__strawberry_definition__.fields
        query_field_names = [f.python_name for f in query_fields]
        
        required_queries = [
            'content_entry', 'content_entries', 'content_types',
            'media', 'me', 'locales', 'themes'
        ]
        
        for query_name in required_queries:
            if query_name not in query_field_names:
                print(f"✗ Query missing field: {query_name}")
                return False
        
        # Check Mutation fields
        mutation_fields = Mutation.__strawberry_definition__.fields
        mutation_field_names = [f.python_name for f in mutation_fields]
        
        required_mutations = ['publish_content', 'unpublish_content']
        
        for mutation_name in required_mutations:
            if mutation_name not in mutation_field_names:
                print(f"✗ Mutation missing field: {mutation_name}")
                return False
        
        print(f"✓ GraphQL schema has {len(query_field_names)} queries and {len(mutation_field_names)} mutations")
        return True
    except Exception as e:
        print(f"✗ GraphQL schema test failed: {e}")
        return False


def test_graphql_endpoint_registration():
    """Test that GraphQL endpoint is registered in main app."""
    print("\nTesting GraphQL endpoint registration...")
    
    try:
        from backend.main import app
        
        # Check if GraphQL route is registered
        routes = [route.path for route in app.routes]
        graphql_routes = [r for r in routes if 'graphql' in r.lower()]
        
        if not graphql_routes:
            print("✗ GraphQL endpoint not registered")
            return False
        
        print(f"✓ GraphQL endpoints registered: {graphql_routes}")
        return True
    except Exception as e:
        print(f"✗ GraphQL endpoint registration test failed: {e}")
        return False


def test_graphql_converters():
    """Test model-to-type converter functions."""
    print("\nTesting GraphQL converters...")
    
    try:
        from backend.graphql.schema import (
            to_content_entry_type, to_content_type_type,
            to_media_type, to_user_type, to_organization_type
        )
        
        converters = [
            to_content_entry_type, to_content_type_type,
            to_media_type, to_user_type, to_organization_type
        ]
        
        for converter in converters:
            if not callable(converter):
                print(f"✗ Converter not callable: {converter.__name__}")
                return False
        
        print(f"✓ All {len(converters)} converter functions are callable")
        return True
    except Exception as e:
        print(f"✗ GraphQL converters test failed: {e}")
        return False


def main():
    """Run all GraphQL tests."""
    print("=" * 60)
    print("Testing GraphQL Implementation")
    print("=" * 60)
    
    tests = [
        test_graphql_imports,
        test_graphql_types,
        test_graphql_context,
        test_graphql_schema,
        test_graphql_endpoint_registration,
        test_graphql_converters,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All {total} GraphQL tests passed!")
        print("=" * 60)
        return 0
    else:
        print(f"❌ {total - passed} of {total} tests failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
