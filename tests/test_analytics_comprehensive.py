"""
Comprehensive test suite for analytics endpoints
Testing business logic and data accuracy
"""

from fastapi import status


class TestAnalyticsComprehensive:
    """Test analytics with actual data"""

    def test_content_stats_with_data(self, authenticated_client, test_content_data):
        """Test content statistics with actual content entries"""
        import uuid

        unique_id = str(uuid.uuid4())[:8]

        # Create a content type and entry
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": f"Blog Post {unique_id}",
                "api_id": f"blog_post_{unique_id}",
                "description": "Blog articles",
                "fields": [
                    {"name": "title", "type": "text", "required": True},
                    {"name": "body", "type": "textarea", "required": True},
                ],
            },
        )
        if ct_response.status_code != status.HTTP_201_CREATED:
            print(f"Content Type Creation Failed: {ct_response.status_code}")
            print(f"Response: {ct_response.json()}")
        assert ct_response.status_code == status.HTTP_201_CREATED
        content_type_id = ct_response.json()["id"]

        # Create multiple content entries
        for i in range(5):
            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": f"post-{i}",
                    "status": "published" if i % 2 == 0 else "draft",
                    "data": {"title": f"Test Post {i}", "body": f"Content for post {i}"},
                },
            )
            assert entry_response.status_code == status.HTTP_201_CREATED

        # Get content statistics
        response = authenticated_client.get("/api/v1/analytics/content")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify statistics
        assert data["total_entries"] == 5
        assert data["published_entries"] == 3  # entries 0, 2, 4
        assert data["draft_entries"] == 2  # entries 1, 3
        assert data["total_types"] >= 1
        assert "recent_entries" in data
        assert len(data["recent_entries"]) <= 10

    def test_user_stats_accuracy(self, authenticated_client):
        """Test user statistics accuracy"""
        response = authenticated_client.get("/api/v1/analytics/users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify user stats structure
        assert "total_users" in data
        assert "active_users_7d" in data
        assert "active_users_30d" in data
        assert data["total_users"] >= 1  # At least the test user
        assert data["active_users_7d"] >= 0
        assert data["active_users_30d"] >= data["active_users_7d"]
        assert data["active_users_30d"] <= data["total_users"]

    def test_activity_stats_structure(self, authenticated_client):
        """Test activity statistics structure"""
        response = authenticated_client.get("/api/v1/analytics/activity")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify activity stats
        assert "actions_today" in data
        assert "actions_7d" in data
        assert "actions_30d" in data
        assert "actions_by_type" in data
        assert isinstance(data["actions_today"], int)
        assert isinstance(data["actions_7d"], int)
        assert isinstance(data["actions_30d"], int)
        assert isinstance(data["actions_by_type"], list)

    def test_content_by_type_breakdown(self, authenticated_client):
        """Test content breakdown by type"""
        # Create two different content types
        for i in range(2):
            ct_response = authenticated_client.post(
                "/api/v1/content/types",
                json={
                    "name": f"Type {i}",
                    "api_id": f"type_{i}",
                    "description": f"Test type {i}",
                    "fields": [{"name": "title", "type": "text", "required": True}],
                },
            )
            assert ct_response.status_code == status.HTTP_201_CREATED
            content_type_id = ct_response.json()["id"]

            # Create entries for this type
            for j in range(i + 1):  # Type 0: 1 entry, Type 1: 2 entries
                authenticated_client.post(
                    "/api/v1/content/entries",
                    json={
                        "content_type_id": content_type_id,
                        "slug": f"entry-{i}-{j}",
                        "status": "published",
                        "data": {"title": f"Entry {i}-{j}"},
                    },
                )

        # Get statistics
        response = authenticated_client.get("/api/v1/analytics/content")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify entries by type
        assert "entries_by_type" in data
        assert len(data["entries_by_type"]) >= 2
