"""Pydantic schemas for Two-Factor Authentication."""
from typing import List, Optional
from pydantic import BaseModel, Field


class TwoFactorEnableResponse(BaseModel):
    """Response when enabling 2FA."""
    secret: str = Field(..., description="Base32-encoded TOTP secret (store securely)")
    qr_code: str = Field(..., description="Base64-encoded QR code image")
    backup_codes: List[str] = Field(..., description="Backup codes (show once)")
    message: str = Field(default="Scan QR code with authenticator app and verify")


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify TOTP code."""
    code: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class TwoFactorVerifyResponse(BaseModel):
    """Response after verifying TOTP code."""
    success: bool
    message: str


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA."""
    password: str = Field(..., description="User's password")
    code: Optional[str] = Field(None, min_length=6, max_length=6, description="6-digit TOTP code or backup code")


class TwoFactorBackupCodesResponse(BaseModel):
    """Response with backup codes."""
    backup_codes: List[str] = Field(..., description="List of backup codes")
    remaining: int = Field(..., description="Number of unused backup codes")
    message: str


class TwoFactorBackupVerifyRequest(BaseModel):
    """Request to verify backup code."""
    code: str = Field(..., description="Backup code")


class TwoFactorStatusResponse(BaseModel):
    """2FA status for a user."""
    enabled: bool = Field(..., description="Whether 2FA is enabled")
    verified: bool = Field(..., description="Whether 2FA setup is verified")
    backup_codes_remaining: int = Field(default=0, description="Unused backup codes")
    required: bool = Field(default=False, description="Whether 2FA is required for this user")
