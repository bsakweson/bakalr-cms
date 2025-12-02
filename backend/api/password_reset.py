"""
Password reset endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from backend.api.schemas.password_reset import (
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    PasswordResetResponseSchema,
    PasswordResetTokenValidationResponse,
    PasswordResetTokenValidationSchema,
)
from backend.core.email_service import email_service
from backend.core.exceptions import BadRequestException
from backend.core.password_reset_service import PasswordResetService
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def send_reset_email(email: str, token: str, organization_id: UUID, user_id: UUID):
    """
    Send password reset email using email service.
    """
    import os

    # Skip email sending in test mode
    if os.getenv("MAIL_SUPPRESS_SEND") == "1":
        print(f"✓ Password reset email suppressed (test mode) for {email}")
        return

    # Get user name for email (sync query)
    from backend.db.session import SessionLocal
    from backend.models.user import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.first_name:
            user_name = (
                f"{user.first_name} {user.last_name}".strip() if user.last_name else user.first_name
            )
        else:
            user_name = email.split("@")[0]
    finally:
        db.close()

    try:
        await email_service.send_password_reset_email(
            to_email=email,
            user_name=user_name,
            reset_token=token,
            organization_id=organization_id,
            user_id=user_id,
        )
        print(f"✓ Password reset email sent to {email}")
    except Exception as e:
        print(f"✗ Failed to send password reset email to {email}: {e}")


@router.post(
    "/password-reset/request",
    response_model=PasswordResetResponseSchema,
    summary="Request password reset",
    description="Send a password reset email with a secure token. Token expires in 1 hour.",
)
@limiter.limit(get_rate_limit())
async def request_password_reset(
    request: Request,
    data: PasswordResetRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Request a password reset email.

    - **email**: User's email address

    Returns success message even if email doesn't exist (security best practice).
    """
    # Create reset token (this internally checks if user exists)
    token = await PasswordResetService.create_reset_token(data.email, db)

    if token:
        # Get user for organization_id (token creation already verified user exists)
        from backend.models.user import User

        user = db.query(User).filter(User.email == data.email, User.is_active == True).first()

        if user:
            # Send email in background (non-blocking)
            background_tasks.add_task(
                send_reset_email, data.email, token, user.organization_id, user.id
            )

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
@limiter.limit(get_rate_limit())
async def validate_reset_token(request: Request, data: PasswordResetTokenValidationSchema):
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
@limiter.limit(get_rate_limit())
async def confirm_password_reset(
    request: Request,
    data: PasswordResetConfirmSchema,
    db: Session = Depends(get_db),
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
