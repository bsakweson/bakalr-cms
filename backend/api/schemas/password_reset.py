"""
Pydantic schemas for password reset flow.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class PasswordResetRequestSchema(BaseModel):
    """Schema for requesting password reset."""
    email: EmailStr = Field(..., description="Email address of the user")


class PasswordResetConfirmSchema(BaseModel):
    """Schema for confirming password reset with token."""
    token: str = Field(..., min_length=32, max_length=500, description="Password reset token from email")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password (min 8 characters)")
    
    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Require at least one uppercase, one lowercase, one digit
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        
        return v


class PasswordResetResponseSchema(BaseModel):
    """Schema for password reset response."""
    message: str = Field(..., description="Success message")
    email: str = Field(..., description="Email where reset link was sent")


class PasswordResetTokenValidationSchema(BaseModel):
    """Schema for validating reset token."""
    token: str = Field(..., min_length=32, max_length=500, description="Password reset token to validate")


class PasswordResetTokenValidationResponse(BaseModel):
    """Schema for token validation response."""
    valid: bool = Field(..., description="Whether the token is valid")
    email: str | None = Field(None, description="Email associated with token (if valid)")
    expires_at: str | None = Field(None, description="Token expiration timestamp (if valid)")
