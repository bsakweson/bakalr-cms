"""Two-Factor Authentication (2FA) service with TOTP support."""
import pyotp
import qrcode
import io
import base64
import secrets
import json
from typing import List, Tuple, Optional

from backend.core.config import settings
from backend.core.security import get_password_hash, verify_password


class TwoFactorService:
    """Service for managing Two-Factor Authentication."""
    
    @staticmethod
    def generate_secret() -> str:
        """
        Generate a random base32 secret for TOTP.
        
        Returns:
            Base32-encoded secret string
        """
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp(secret: str) -> pyotp.TOTP:
        """
        Get TOTP instance for a secret.
        
        Args:
            secret: Base32-encoded secret
            
        Returns:
            TOTP instance
        """
        return pyotp.TOTP(
            secret,
            interval=settings.TWO_FACTOR_CODE_VALIDITY_SECONDS
        )
    
    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: Base32-encoded secret
            code: 6-digit TOTP code from authenticator app
            
        Returns:
            True if code is valid, False otherwise
        """
        if not secret or not code:
            return False
        
        totp = TwoFactorService.get_totp(secret)
        # Allow 1 window before and after for clock drift
        return totp.verify(code, valid_window=1)
    
    @staticmethod
    def get_provisioning_uri(secret: str, user_email: str) -> str:
        """
        Get provisioning URI for QR code.
        
        Args:
            secret: Base32-encoded secret
            user_email: User's email address
            
        Returns:
            Provisioning URI (otpauth://)
        """
        totp = TwoFactorService.get_totp(secret)
        return totp.provisioning_uri(
            name=user_email,
            issuer_name=settings.TWO_FACTOR_ISSUER_NAME
        )
    
    @staticmethod
    def generate_qr_code(provisioning_uri: str) -> str:
        """
        Generate QR code image as base64 string.
        
        Args:
            provisioning_uri: OTP provisioning URI
            
        Returns:
            Base64-encoded PNG image
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def generate_backup_codes(count: Optional[int] = None) -> Tuple[List[str], str]:
        """
        Generate backup codes.
        
        Args:
            count: Number of codes to generate (default from settings)
            
        Returns:
            Tuple of (plain_codes, hashed_codes_json)
            - plain_codes: List of plain text codes to show user once
            - hashed_codes_json: JSON string of hashed codes to store in database
        """
        if count is None:
            count = settings.TWO_FACTOR_BACKUP_CODES_COUNT
        
        plain_codes = []
        hashed_codes = []
        
        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = secrets.token_hex(4).upper()  # 8 chars
            plain_codes.append(code)
            hashed_codes.append({
                "code": get_password_hash(code),
                "used": False
            })
        
        return plain_codes, json.dumps(hashed_codes)
    
    @staticmethod
    def verify_backup_code(hashed_codes_json: str, code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify and consume a backup code.
        
        Args:
            hashed_codes_json: JSON string of hashed backup codes
            code: Plain text backup code to verify
            
        Returns:
            Tuple of (is_valid, updated_codes_json)
            - is_valid: True if code is valid and not used
            - updated_codes_json: Updated JSON with code marked as used, or None if invalid
        """
        if not hashed_codes_json or not code:
            return False, None
        
        try:
            codes = json.loads(hashed_codes_json)
        except json.JSONDecodeError:
            return False, None
        
        # Check each code
        for backup_code in codes:
            if backup_code.get("used"):
                continue
            
            # Verify hash
            if verify_password(code.upper(), backup_code["code"]):
                # Mark as used
                backup_code["used"] = True
                return True, json.dumps(codes)
        
        return False, None
    
    @staticmethod
    def count_remaining_backup_codes(hashed_codes_json: str) -> int:
        """
        Count how many backup codes are still unused.
        
        Args:
            hashed_codes_json: JSON string of hashed backup codes
            
        Returns:
            Number of unused codes
        """
        if not hashed_codes_json:
            return 0
        
        try:
            codes = json.loads(hashed_codes_json)
            return sum(1 for code in codes if not code.get("used"))
        except json.JSONDecodeError:
            return 0
    
    @staticmethod
    def is_2fa_required_for_user(user) -> bool:
        """
        Check if 2FA is required for a user.
        
        Args:
            user: User model instance
            
        Returns:
            True if 2FA is required
        """
        if not settings.TWO_FACTOR_ENABLED:
            return False
        
        # Check if user has admin role and 2FA is enforced for admins
        if settings.TWO_FACTOR_ENFORCE_FOR_ADMINS:
            # Check if user has admin role
            for role in user.roles:
                if role.name in ["Super Admin", "Org Admin", "Admin"]:
                    return True
        
        # Otherwise, 2FA is optional (user can enable it voluntarily)
        return user.two_factor_enabled
