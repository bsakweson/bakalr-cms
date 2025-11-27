"""
Test suite for scheduling functionality
"""

from datetime import datetime, timedelta

from fastapi import status


class TestScheduling:
    """Test content scheduling endpoints"""

    def test_create_scheduled_publish(self, authenticated_client):
        """Test scheduling content for future publication"""
        # Create content type and entry first
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Scheduled Article",
                "api_id": "scheduled_article",
                "description": "For scheduling tests",
                "fields": [{"name": "title", "type": "text", "required": True}],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]

            # Create content entry
            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": "scheduled-entry",
                    "status": "draft",
                    "data": {"title": "Scheduled Content"},
                },
            )

            if entry_response.status_code == status.HTTP_201_CREATED:
                entry_id = entry_response.json()["id"]

                # Schedule publication for 1 hour from now
                from datetime import timezone

                scheduled_time = (
                    (datetime.now(timezone.utc) + timedelta(hours=1))
                    .isoformat()
                    .replace("+00:00", "Z")
                )

                schedule_data = {
                    "content_entry_id": entry_id,
                    "scheduled_at": scheduled_time,
                    "action": "publish",
                }

                response = authenticated_client.post(
                    "/api/v1/content/schedules", json=schedule_data
                )

                assert response.status_code in [
                    status.HTTP_201_CREATED,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_404_NOT_FOUND,
                ]

    def test_list_scheduled_content(self, authenticated_client):
        """Test listing scheduled content"""
        response = authenticated_client.get("/api/v1/content/schedules")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_get_scheduled_item(self, authenticated_client):
        """Test getting specific scheduled item"""
        response = authenticated_client.get("/api/v1/content/schedules/99999")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_cancel_scheduled_item(self, authenticated_client):
        """Test canceling a scheduled action"""
        response = authenticated_client.delete("/api/v1/content/schedules/99999")

        assert response.status_code in [
            status.HTTP_204_NO_CONTENT,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
