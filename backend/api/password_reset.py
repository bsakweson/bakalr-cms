"""
Password reset endpoints.
"""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.api.schemas.password_reset import (
    PasswordResetRequestSchema,
    PasswordResetConfirmSchema,
    PasswordResetResponseSchema,
    PasswordResetTokenValidationSchema,
    PasswordResetTokenValidationResponse,
)
from backend.core.password_reset_service import PasswordResetService
from backend.core.exceptions import BadRequestException, NotFoundException


router = APIRouter(prefix="/auth", tags=["Authentication"])


async def send_reset_email(email: str, token: str):
    """
    Send password reset email (background task).
    
    In production, integrate with your email service (SendGrid, AWS SES, etc.)
    For now, this is a placeholder that logs the token.
    """
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    
    # TODO: Replace with actual email sending
    print(f"📧 Password reset email for {email}")
    print(f"Reset URL: {reset_url}")
    print(f"Token expires in {PasswordResetService.TOKEN_EXPIRATION_HOURS} hour(s)")
    
    # Example email content:
    # Subject: Reset your password
    # Body: Click the link below to reset your password: {reset_url}
    #       This link will expire in 1 hour.


@router.post(
    "/password-reset/request",
    response_model=PasswordResetResponseSchema,
    summary="Request password reset",
    description="Send a password reset email with a secure token. Token expires in 1 hour.",
)
async def request_password_reset(
    data: PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email.
    
    - **email**: User's email address
    
    Returns success message even if email doesn't exist (security best practice).
    """
    # Create reset token
    token = await PasswordResetService.create_reset_token(data.email, db)
    
    if token:
        # Send email in background (non-blocking)
        background_tasks.add_task(send_reset_email, data.email, token)
    
    # Always return success (don't reveal if user exists)
    return PasswordResetResponseSchema(
        message="If an account exists with this email, a password reset link has been sent.",
        email=data.email,
    )


@router.post(
    "/password-reset/validate",
    response_model=PasswordResetTokenValidationResponse,
    summary="Validate reset token",
    description="Check if a password reset token is valid and not expired.",
)
async def validate_reset_token(data: PasswordResetTokenValidationSchema):
    """
    Validate a password reset token without consuming it.
    
    - **token**: Password reset token to validate
    
    Returns token validity status and associated email if valid.
    """
    token_data = await PasswordResetService.validate_reset_token(data.token)
    
    if not token_data:
        return PasswordResetTokenValidationResponse(valid=False)
    
    return PasswordResetTokenValidationResponse(
        valid=True,
        email=token_data.get("email"),
        expires_at=token_data.get("created_at"),  # You can calculate actual expiry
    )


@router.post(
    "/password-reset/confirm",
    response_model=PasswordResetResponseSchema,
    summary="Confirm password reset",
    description="Reset password using a valid token. Token will be invalidated after use.",
)
async def confirm_password_reset(
    data: PasswordResetConfirmSchema,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password with a valid token.
    
    - **token**: Password reset token from email
    - **new_password**: New password (min 8 chars, must include uppercase, lowercase, digit)
    
    Token is single-use and will be invalidated after successful reset.
    """
    success = await PasswordResetService.reset_password(
        data.token,
        data.new_password,
        db,
    )
    
    if not success:
        raise BadRequestException(
            detail="Invalid or expired reset token. Please request a new password reset."
        )
    
    return PasswordResetResponseSchema(
        message="Password has been reset successfully. You can now log in with your new password.",
        email="",  # Don't return email for security
    )
