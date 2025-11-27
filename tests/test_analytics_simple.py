"""
Test suite for analytics - simplified version
"""
import pytest
from fastapi import status


class TestAnalytics:
    """Test analytics endpoints"""
    
    def test_get_content_stats(self, authenticated_client):
        """Test getting content statistics"""
        response = authenticated_client.get("/api/v1/analytics/content")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Check for expected fields
        assert "total_entries" in data or "total" in data or "content" in data
    
    def test_get_user_stats(self, authenticated_client):
        """Test getting user statistics"""
        response = authenticated_client.get("/api/v1/analytics/users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Check for expected fields  
        assert "total_users" in data or "total" in data or "users" in data
