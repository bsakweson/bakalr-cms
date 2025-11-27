"""Two-Factor Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.api.schemas.two_factor import (
    TwoFactorBackupCodesResponse,
    TwoFactorBackupVerifyRequest,
    TwoFactorDisableRequest,
    TwoFactorEnableResponse,
    TwoFactorStatusResponse,
    TwoFactorVerifyRequest,
    TwoFactorVerifyResponse,
)
from backend.core.dependencies import get_current_user, get_db
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.security import verify_password
from backend.core.two_factor_service import TwoFactorService
from backend.models.user import User

router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Authentication"])


@router.get("/status", response_model=TwoFactorStatusResponse)
@limiter.limit(get_rate_limit())
def get_2fa_status(
    request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Get current 2FA status for the authenticated user.

    Returns:
        - enabled: Whether 2FA is enabled
        - verified: Whether setup is complete
        - backup_codes_remaining: Unused backup codes
        - required: Whether 2FA is mandatory for this user
    """
    return TwoFactorStatusResponse(
        enabled=current_user.two_factor_enabled or False,
        verified=bool(current_user.two_factor_secret),
        backup_codes_remaining=TwoFactorService.count_remaining_backup_codes(
            current_user.two_factor_backup_codes or ""
        ),
        required=TwoFactorService.is_2fa_required_for_user(current_user),
    )


@router.post("/enable", response_model=TwoFactorEnableResponse)
@limiter.limit(get_rate_limit())
def enable_2fa(
    request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Enable 2FA for the current user.

    Returns QR code and backup codes. User must verify with authenticator app
    to complete setup.

    Steps:
    1. Call this endpoint to get QR code
    2. Scan QR code with authenticator app (Google Authenticator, Authy, etc.)
    3. Call /verify-setup with code from app to complete setup
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enabled"
        )

    # Generate secret and QR code
    secret = TwoFactorService.generate_secret()
    provisioning_uri = TwoFactorService.get_provisioning_uri(secret, current_user.email)
    qr_code = TwoFactorService.generate_qr_code(provisioning_uri)

    # Generate backup codes
    plain_codes, hashed_codes_json = TwoFactorService.generate_backup_codes()

    # Store secret and backup codes (not enabled yet, needs verification)
    current_user.two_factor_secret = secret
    current_user.two_factor_backup_codes = hashed_codes_json
    current_user.two_factor_enabled = False  # Not enabled until verified

    db.commit()
    db.refresh(current_user)

    return TwoFactorEnableResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=plain_codes,
        message="Scan QR code with your authenticator app, then verify with a code to complete setup",
    )


@router.post("/verify-setup", response_model=TwoFactorVerifyResponse)
@limiter.limit(get_rate_limit())
def verify_2fa_setup(
    request: Request,
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify TOTP code to complete 2FA setup.

    Call this after scanning the QR code from /enable endpoint.
    This activates 2FA for the user.
    """
    if current_user.two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is already enabled and verified"
        )

    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call /enable first.",
        )

    # Verify the code
    if not TwoFactorService.verify_code(current_user.two_factor_secret, request.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code"
        )

    # Enable 2FA
    current_user.two_factor_enabled = True
    db.commit()
    db.refresh(current_user)

    return TwoFactorVerifyResponse(success=True, message="2FA has been successfully enabled")


@router.post("/verify", response_model=TwoFactorVerifyResponse)
@limiter.limit(get_rate_limit())
def verify_2fa_code(
    request: Request,
    twofactorRequest: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Verify a TOTP code for an already-enabled 2FA user.

    Used during login or for sensitive operations.
    """
    if not current_user.two_factor_enabled or not current_user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled")

    if not TwoFactorService.verify_code(current_user.two_factor_secret, twofactorRequest.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code"
        )

    return TwoFactorVerifyResponse(success=True, message="Code verified successfully")


@router.post("/disable", response_model=TwoFactorVerifyResponse)
@limiter.limit(get_rate_limit())
def disable_2fa(
    request: Request,
    disable_data: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Disable 2FA for the current user.

    Requires password and optionally a TOTP code or backup code.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled")

    # Check if 2FA is required for this user
    if TwoFactorService.is_2fa_required_for_user(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA is required for your role and cannot be disabled",
        )

    # Verify password
    if not verify_password(disable_data.password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    # Verify code if provided
    if disable_data.code:
        # Try TOTP code first
        is_valid = TwoFactorService.verify_code(current_user.two_factor_secret, disable_data.code)

        # Try backup code if TOTP failed
        if not is_valid and current_user.two_factor_backup_codes:
            is_valid, _ = TwoFactorService.verify_backup_code(
                current_user.two_factor_backup_codes, disable_data.code
            )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code"
            )

    # Disable 2FA
    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    current_user.two_factor_backup_codes = None

    db.commit()
    db.refresh(current_user)

    return TwoFactorVerifyResponse(success=True, message="2FA has been disabled")


@router.get("/backup-codes", response_model=TwoFactorBackupCodesResponse)
@limiter.limit(get_rate_limit())
def get_backup_codes(request: Request, current_user: User = Depends(get_current_user)):
    """
    Get the status of backup codes (does NOT show the codes themselves).

    Backup codes are only shown once during /enable or /backup-codes/regenerate.
    """
    if not current_user.two_factor_enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled")

    remaining = TwoFactorService.count_remaining_backup_codes(
        current_user.two_factor_backup_codes or ""
    )

    return TwoFactorBackupCodesResponse(
        backup_codes=[],  # Never return actual codes in GET
        remaining=remaining,
        message=f"You have {remaining} unused backup codes. Use /backup-codes/regenerate to create new ones.",
    )


@router.post("/backup-codes/regenerate", response_model=TwoFactorBackupCodesResponse)
@limiter.limit(get_rate_limit())
def regenerate_backup_codes(
    request: Request,
    verify_data: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Regenerate backup codes. Requires TOTP verification.

    WARNING: This invalidates all existing backup codes.
    """
    if not current_user.two_factor_enabled or not current_user.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA is not enabled")

    # Verify TOTP code
    if not TwoFactorService.verify_code(current_user.two_factor_secret, verify_data.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid verification code"
        )

    # Generate new backup codes
    plain_codes, hashed_codes_json = TwoFactorService.generate_backup_codes()
    current_user.two_factor_backup_codes = hashed_codes_json

    db.commit()
    db.refresh(current_user)

    return TwoFactorBackupCodesResponse(
        backup_codes=plain_codes,
        remaining=len(plain_codes),
        message="New backup codes generated. Save these in a secure location. Old codes are now invalid.",
    )


@router.post("/verify-backup", response_model=TwoFactorVerifyResponse)
@limiter.limit(get_rate_limit())
def verify_backup_code(
    request: Request,
    backup_data: TwoFactorBackupVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verify and consume a backup code.

    Backup codes are one-time use only. After verification, the code is marked as used.
    """
    if not current_user.two_factor_enabled or not current_user.two_factor_backup_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled or no backup codes available",
        )

    is_valid, updated_codes = TwoFactorService.verify_backup_code(
        current_user.two_factor_backup_codes, backup_data.code
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or already used backup code"
        )

    # Update backup codes (mark as used)
    current_user.two_factor_backup_codes = updated_codes
    db.commit()
    db.refresh(current_user)

    remaining = TwoFactorService.count_remaining_backup_codes(updated_codes)

    return TwoFactorVerifyResponse(
        success=True, message=f"Backup code verified successfully. {remaining} codes remaining."
    )
