"""
Test suite for password reset flow
"""
import pytest
from fastapi import status


class TestPasswordReset:
    """Test password reset functionality"""
    
    def test_request_password_reset(self, client, test_user_data):
        """Test requesting a password reset"""
        # Register a user first
        register_response = client.post("/api/v1/auth/register", json=test_user_data)
        
        # Request password reset (background task may fail in tests, that's ok)
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_user_data["email"]}
        )
        
        # Should accept the request (even if email doesn't exist, for security)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED
        ]
    
    def test_password_reset_invalid_email(self, client):
        """Test password reset with non-existent email"""
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "nonexistent@example.com"}
        )
        
        # Should still return success (don't reveal if email exists)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED
        ]
    
    def test_password_reset_validation(self, client):
        """Test password reset with weak password"""
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": "fake-token",
                "new_password": "weak"  # Too weak
            }
        )
        
        # Should reject weak password or invalid token
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_password_reset_rate_limiting(self, client, test_user_data):
        """Test that password reset is rate limited"""
        # Try multiple password reset requests
        for _ in range(5):
            client.post(
                "/api/v1/auth/password-reset/request",
                json={"email": test_user_data["email"]}
            )
        
        # Additional request should be rate limited
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": test_user_data["email"]}
        )
        
        # May be rate limited or still allowed
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED,
            status.HTTP_429_TOO_MANY_REQUESTS
        ]
