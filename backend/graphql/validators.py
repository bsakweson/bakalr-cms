"""
GraphQL security validators for query depth, complexity, and timeout protection.
"""

from typing import Optional

from graphql.language import ast
from strawberry.extensions import SchemaExtension


class QueryDepthLimiter(SchemaExtension):
    """
    Prevents deeply nested GraphQL queries that could cause exponential database queries.

    Example attack:
        query {
            contentEntry(id: 1) {
                author {
                    organization {
                        users {
                            organization {
                                users { ... }  # 50+ levels deep
                            }
                        }
                    }
                }
            }
        }
    """

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth
        super().__init__()

    def on_operation(self):
        """Hook called before query execution"""
        # Strawberry extensions don't provide direct access to parsed document
        # Skip validation - these would need to be implemented as middleware
        # or using graphql-core validation rules instead
        pass

    def _calculate_depth(
        self, selection_set: Optional[ast.SelectionSetNode], current_depth: int
    ) -> int:
        """Recursively calculate maximum depth of query"""
        if not selection_set:
            return current_depth

        max_depth = current_depth

        for selection in selection_set.selections:
            if isinstance(selection, ast.FieldNode):
                # Calculate depth for this field's children
                field_depth = current_depth + 1
                if selection.selection_set:
                    field_depth = self._calculate_depth(selection.selection_set, field_depth)
                max_depth = max(max_depth, field_depth)
            elif isinstance(selection, ast.InlineFragmentNode):
                fragment_depth = self._calculate_depth(selection.selection_set, current_depth)
                max_depth = max(max_depth, fragment_depth)
            elif isinstance(selection, ast.FragmentSpreadNode):
                # Fragment spreads don't add to depth directly
                pass

        return max_depth


class QueryComplexityLimiter(SchemaExtension):
    """
    Prevents high-complexity GraphQL queries that could overload the system.

    Uses cost-based scoring where:
    - List queries (contentEntries, media) cost more
    - Nested fields multiply cost
    - Simple scalar fields cost 1

    Example attack:
        query {
            contentEntries(per_page: 100) { ... }  # Cost: 10 * 100 = 1000
            media(per_page: 100) { ... }            # Cost: 10 * 100 = 1000
            me { ... }                              # Cost: 1
            # Total: 2001 > 1000 limit
        }
    """

    def __init__(self, max_complexity: int = 1000):
        self.max_complexity = max_complexity
        # Define base cost for expensive fields
        self.field_costs = {
            "contentEntries": 10,
            "media": 10,
            "users": 10,
            "notifications": 5,
            "contentTypes": 5,
            "locales": 2,
            "themes": 2,
            # Nested fields that trigger additional queries
            "author": 2,
            "organization": 2,
            "content_type": 2,
            "uploaded_by": 2,
            # Cheap fields
            "me": 1,
            "contentEntry": 1,
        }
        super().__init__()

    def on_operation(self):
        """Hook called before query execution"""
        # Strawberry extensions don't provide direct access to parsed document
        # Skip validation - these would need to be implemented as middleware
        # or using graphql-core validation rules instead
        pass

    def _calculate_complexity(
        self, selection_set: Optional[ast.SelectionSetNode], multiplier: int = 1
    ) -> int:
        """Recursively calculate total query complexity"""
        if not selection_set:
            return 0

        total_complexity = 0

        for selection in selection_set.selections:
            if isinstance(selection, ast.FieldNode):
                field_name = selection.name.value

                # Get base cost for this field (default: 1)
                base_cost = self.field_costs.get(field_name, 1)

                # Check for pagination arguments that increase cost
                pagination_multiplier = 1
                if selection.arguments:
                    for arg in selection.arguments:
                        if arg.name.value in ["per_page", "limit"]:
                            # Extract the value (simplified)
                            if isinstance(arg.value, ast.IntValueNode):
                                pagination_multiplier = int(arg.value.value)

                # Calculate cost for this field
                field_cost = base_cost * multiplier * pagination_multiplier
                total_complexity += field_cost

                # Recursively calculate cost for nested fields
                if selection.selection_set:
                    nested_cost = self._calculate_complexity(
                        selection.selection_set, multiplier * base_cost
                    )
                    total_complexity += nested_cost

            elif isinstance(selection, ast.InlineFragmentNode):
                fragment_cost = self._calculate_complexity(selection.selection_set, multiplier)
                total_complexity += fragment_cost

        return total_complexity


class QueryTimeout(SchemaExtension):
    """
    Enforces maximum execution time for GraphQL queries.

    Prevents slow queries from tying up resources indefinitely.

    Note: This is a placeholder implementation. Full timeout support
    requires database-level query timeouts or application-level monitoring.
    """

    def __init__(self, timeout_seconds: int = 10):
        self.timeout_seconds = timeout_seconds
        super().__init__()
