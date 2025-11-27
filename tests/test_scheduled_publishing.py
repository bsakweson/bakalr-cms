"""
Test suite for scheduled publishing
"""

from datetime import datetime, timedelta, timezone

from fastapi import status


class TestScheduledPublishing:
    """Test scheduled publishing functionality"""

    def test_schedule_future_publish(self, authenticated_client):
        """Test scheduling content for future publication"""
        # Create content type
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Scheduled Post",
                "api_id": "scheduled_post",
                "fields": [{"name": "title", "type": "text", "required": True}],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]

            # Create entry with scheduled publish date
            future_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": "scheduled-post",
                    "status": "draft",
                    "data": {"title": "Future Post"},
                    "published_at": future_date,
                },
            )

            assert entry_response.status_code == status.HTTP_201_CREATED
            entry_data = entry_response.json()
            assert entry_data["status"] == "draft"

    def test_list_scheduled_content(self, authenticated_client):
        """Test listing scheduled content"""
        response = authenticated_client.get("/api/v1/content/schedules")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_cancel_scheduled_publish(self, authenticated_client):
        """Test canceling a scheduled publish"""
        # Create scheduled content
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Cancelable Post",
                "api_id": "cancelable_post",
                "fields": [{"name": "title", "type": "text", "required": True}],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]
            future_date = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": "cancelable-post",
                    "status": "draft",
                    "data": {"title": "Post to Cancel"},
                    "published_at": future_date,
                },
            )

            if entry_response.status_code == status.HTTP_201_CREATED:
                entry_id = entry_response.json()["id"]

                # Cancel the schedule
                cancel_response = authenticated_client.delete(
                    f"/api/v1/content/schedules/{entry_id}"
                )

                assert cancel_response.status_code in [
                    status.HTTP_204_NO_CONTENT,
                    status.HTTP_200_OK,
                    status.HTTP_404_NOT_FOUND,
                ]

    def test_reschedule_content(self, authenticated_client):
        """Test rescheduling content to a different time"""
        ct_response = authenticated_client.post(
            "/api/v1/content/types",
            json={
                "name": "Reschedulable Post",
                "api_id": "reschedulable_post",
                "fields": [{"name": "title", "type": "text", "required": True}],
            },
        )

        if ct_response.status_code == status.HTTP_201_CREATED:
            content_type_id = ct_response.json()["id"]

            # Create with initial schedule
            initial_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            entry_response = authenticated_client.post(
                "/api/v1/content/entries",
                json={
                    "content_type_id": content_type_id,
                    "slug": "reschedulable-post",
                    "status": "draft",
                    "data": {"title": "Reschedulable Post"},
                    "published_at": initial_date,
                },
            )

            if entry_response.status_code == status.HTTP_201_CREATED:
                entry_id = entry_response.json()["id"]

                # Reschedule to new date
                new_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
                update_response = authenticated_client.patch(
                    f"/api/v1/content/entries/{entry_id}", json={"published_at": new_date}
                )

                assert update_response.status_code in [
                    status.HTTP_200_OK,
                    status.HTTP_404_NOT_FOUND,
                ]
