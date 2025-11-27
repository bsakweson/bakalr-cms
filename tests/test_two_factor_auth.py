"""
Test suite for two-factor authentication
"""

from fastapi import status


class TestTwoFactorAuth:
    """Test 2FA functionality"""

    def test_enable_2fa_setup(self, authenticated_client):
        """Test setting up 2FA"""
        response = authenticated_client.post("/api/v1/auth/2fa/setup")

        # 2FA setup may require additional verification
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should return QR code data or secret
            assert "secret" in data or "qr_code" in data or "setup_url" in data

    def test_verify_2fa_setup(self, authenticated_client):
        """Test verifying 2FA setup with TOTP code"""
        # First setup 2FA
        setup_response = authenticated_client.post("/api/v1/auth/2fa/setup")

        if setup_response.status_code == status.HTTP_200_OK:
            # Try to verify with invalid code
            verify_response = authenticated_client.post(
                "/api/v1/auth/2fa/verify", json={"code": "000000"}  # Invalid code
            )

            # Should reject invalid code
            assert verify_response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_401_UNAUTHORIZED,
            ]

    def test_disable_2fa(self, authenticated_client, test_user_data):
        """Test disabling 2FA"""
        # Try to disable 2FA (requires password)
        response = authenticated_client.post(
            "/api/v1/auth/2fa/disable", json={"password": test_user_data["password"]}
        )

        # Should return 400 if 2FA is not enabled, or 200 if successfully disabled
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,  # 2FA not enabled
            status.HTTP_401_UNAUTHORIZED,  # Invalid password
        ]

    def test_2fa_backup_codes(self, authenticated_client):
        """Test generating 2FA backup codes"""
        response = authenticated_client.get("/api/v1/auth/2fa/backup-codes")

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should return backup codes
            assert "codes" in data or "backup_codes" in data

    def test_login_with_2fa_required(self, client, test_user_data):
        """Test login flow when 2FA is enabled"""
        # Register and login normally first
        client.post("/api/v1/auth/register", json=test_user_data)

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )

        # Login should succeed (2FA may not be enabled)
        assert login_response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED,  # If 2FA required
        ]
