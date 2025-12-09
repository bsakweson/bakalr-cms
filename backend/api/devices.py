"""
Device Management API endpoints
Migrated from boutique-platform keycloak-bff
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.api.schemas.device import (
    DeviceListResponse,
    DevicePushTokenRequest,
    DeviceRegisterRequest,
    DeviceRegistrationResponse,
    DeviceResponse,
    DeviceSuspendRequest,
    DeviceTrustRequest,
    DeviceUpdateRequest,
    DeviceVerificationCodeSentResponse,
    DeviceVerificationResponse,
    DeviceVerifyRequest,
    MessageResponse,
)
from backend.core.dependencies import get_current_user, get_optional_user
from backend.db.session import get_db
from backend.models.device import Device, DevicePlatform, DeviceStatus
from backend.models.user import User

router = APIRouter(prefix="/devices", tags=["Devices"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _device_to_response(device: Device) -> DeviceResponse:
    """Convert Device model to response schema"""
    return DeviceResponse(
        id=device.id,
        device_id=device.device_id,
        name=device.name,
        device_type=device.device_type,
        platform=device.platform,
        os=device.os,
        os_version=device.os_version,
        model=device.model,
        browser=device.browser,
        browser_version=device.browser_version,
        app_version=device.app_version,
        status=device.status,
        verified=device.verified,
        verified_at=device.verified_at,
        is_trusted=device.is_trusted,
        push_enabled=device.push_enabled,
        last_used_at=device.last_used_at,
        last_ip_address=device.last_ip_address,
        last_location=device.last_location,
        created_at=device.created_at,
        display_name=device.display_name,
        is_mobile=device.is_mobile,
        can_receive_push=device.can_receive_push(),
    )


def _generate_verification_code() -> str:
    """Generate a 6-digit verification code"""
    return "".join([str(secrets.randbelow(10)) for _ in range(6)])


# ============ Device Registration ============


@router.post(
    "/register", response_model=DeviceRegistrationResponse, status_code=status.HTTP_201_CREATED
)
async def register_device(
    request: Request,
    device_data: DeviceRegisterRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """
    Register a new device.

    Can be called:
    - By authenticated user: Device linked to user immediately
    - Without auth: Device registered but not linked (for pre-registration)

    If device already exists for user, updates it instead.
    """
    device_id = device_data.device_id or x_device_id
    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device ID is required (in body or X-Device-ID header)",
        )

    client_ip = _get_client_ip(request)

    # Check if device already exists for this user
    existing_device = None
    if current_user:
        existing_device = (
            db.query(Device)
            .filter(Device.device_id == device_id, Device.user_id == current_user.id)
            .first()
        )

    if existing_device:
        # Update existing device
        existing_device.name = device_data.name or existing_device.name
        existing_device.device_type = device_data.device_type or existing_device.device_type
        existing_device.platform = device_data.platform
        existing_device.os = device_data.os or existing_device.os
        existing_device.os_version = device_data.os_version or existing_device.os_version
        existing_device.model = device_data.model or existing_device.model
        existing_device.browser = device_data.browser or existing_device.browser
        existing_device.browser_version = (
            device_data.browser_version or existing_device.browser_version
        )
        existing_device.app_version = device_data.app_version or existing_device.app_version
        existing_device.fcm_token = device_data.fcm_token or existing_device.fcm_token
        existing_device.apns_token = device_data.apns_token or existing_device.apns_token
        existing_device.push_enabled = bool(device_data.fcm_token or device_data.apns_token)
        existing_device.browser_fingerprint = (
            device_data.browser_fingerprint or existing_device.browser_fingerprint
        )
        existing_device.hardware_fingerprint = (
            device_data.hardware_fingerprint or existing_device.hardware_fingerprint
        )
        existing_device.screen_resolution = (
            device_data.screen_resolution or existing_device.screen_resolution
        )
        existing_device.timezone = device_data.timezone or existing_device.timezone
        existing_device.capabilities = device_data.capabilities or existing_device.capabilities
        existing_device.last_used_at = datetime.now(timezone.utc)
        existing_device.last_ip_address = client_ip

        db.commit()
        db.refresh(existing_device)

        return DeviceRegistrationResponse(
            device=_device_to_response(existing_device),
            verification_required=not existing_device.verified,
            message="Device updated successfully",
        )

    # Create new device
    new_device = Device(
        device_id=device_id,
        user_id=current_user.id if current_user else None,
        organization_id=current_user.organization_id if current_user else None,
        name=device_data.name,
        device_type=device_data.device_type,
        platform=device_data.platform,
        os=device_data.os,
        os_version=device_data.os_version,
        model=device_data.model,
        browser=device_data.browser,
        browser_version=device_data.browser_version,
        app_version=device_data.app_version,
        fcm_token=device_data.fcm_token,
        apns_token=device_data.apns_token,
        push_enabled=bool(device_data.fcm_token or device_data.apns_token),
        browser_fingerprint=device_data.browser_fingerprint,
        hardware_fingerprint=device_data.hardware_fingerprint,
        screen_resolution=device_data.screen_resolution,
        timezone=device_data.timezone,
        capabilities=device_data.capabilities,
        status=DeviceStatus.UNVERIFIED,
        verified=False,
        last_ip_address=client_ip,
    )

    db.add(new_device)
    db.commit()
    db.refresh(new_device)

    return DeviceRegistrationResponse(
        device=_device_to_response(new_device),
        verification_required=True,
        message="Device registered successfully. Verification required.",
    )


# ============ Device Listing ============


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[DeviceStatus] = None,
    platform_filter: Optional[DevicePlatform] = None,
):
    """
    List all devices for the current user.

    Optionally filter by status or platform.
    """
    query = db.query(Device).filter(Device.user_id == current_user.id)

    if status_filter:
        query = query.filter(Device.status == status_filter)
    if platform_filter:
        query = query.filter(Device.platform == platform_filter)

    devices = query.order_by(Device.last_used_at.desc()).all()

    return DeviceListResponse(
        devices=[_device_to_response(d) for d in devices],
        total=len(devices),
    )


@router.get("/{device_uuid}", response_model=DeviceResponse)
async def get_device(
    device_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific device by ID"""
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return _device_to_response(device)


# ============ Device Update ============


@router.patch("/{device_uuid}", response_model=DeviceResponse)
async def update_device(
    device_uuid: UUID,
    update_data: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update device information"""
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    # Update only provided fields
    if update_data.name is not None:
        device.name = update_data.name
    if update_data.fcm_token is not None:
        device.fcm_token = update_data.fcm_token
    if update_data.apns_token is not None:
        device.apns_token = update_data.apns_token
    if update_data.push_enabled is not None:
        device.push_enabled = update_data.push_enabled
    if update_data.app_version is not None:
        device.app_version = update_data.app_version
    if update_data.os is not None:
        device.os = update_data.os
    if update_data.os_version is not None:
        device.os_version = update_data.os_version

    db.commit()
    db.refresh(device)

    return _device_to_response(device)


@router.put("/{device_uuid}/push-token", response_model=DeviceResponse)
async def update_push_token(
    device_uuid: UUID,
    token_data: DevicePushTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update push notification token for a device"""
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    device.fcm_token = token_data.fcm_token
    device.apns_token = token_data.apns_token
    device.push_enabled = token_data.push_enabled

    db.commit()
    db.refresh(device)

    return _device_to_response(device)


# ============ Device Verification ============


@router.post("/{device_uuid}/send-verification", response_model=DeviceVerificationCodeSentResponse)
async def send_verification_code(
    device_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a verification code to verify device ownership.

    The code is sent via email to the user's registered email address.
    """
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if device.verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is already verified",
        )

    # Generate verification code
    verification_code = _generate_verification_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    device.verification_code = verification_code
    device.verification_code_expires = expires_at

    db.commit()

    # Send verification email (uses CMS template with translation support)
    try:
        from backend.core.email_service import email_service

        await email_service.send_device_verification_email(
            db=db,
            to_email=current_user.email,
            user_name=current_user.first_name or current_user.email,
            device_name=device.display_name,
            verification_code=verification_code,
            organization_id=current_user.organization_id,
            locale=getattr(current_user, "preferred_locale", "en") or "en",
            expires_minutes=15,
        )
    except Exception as e:
        print(f"Failed to send device verification email: {e}")
        # Continue anyway - code is stored

    return DeviceVerificationCodeSentResponse(
        success=True,
        message=f"Verification code sent to {current_user.email}",
        expires_at=expires_at,
    )


@router.post("/{device_uuid}/verify", response_model=DeviceVerificationResponse)
async def verify_device(
    device_uuid: UUID,
    verify_data: DeviceVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify a device with the verification code"""
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if device.verified:
        return DeviceVerificationResponse(
            success=True,
            message="Device is already verified",
            device=_device_to_response(device),
        )

    # Check verification code
    if not device.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code sent. Please request a new code.",
        )

    if device.verification_code_expires and device.verification_code_expires < datetime.now(
        timezone.utc
    ):
        device.verification_code = None
        device.verification_code_expires = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new code.",
        )

    if device.verification_code != verify_data.verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    # Verify the device
    device.verified = True
    device.verified_at = datetime.now(timezone.utc)
    device.status = DeviceStatus.ACTIVE
    device.verification_code = None
    device.verification_code_expires = None

    db.commit()
    db.refresh(device)

    return DeviceVerificationResponse(
        success=True,
        message="Device verified successfully",
        device=_device_to_response(device),
    )


# ============ Device Trust & Security ============


@router.put("/{device_uuid}/trust", response_model=DeviceResponse)
async def set_device_trust(
    device_uuid: UUID,
    trust_data: DeviceTrustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a device as trusted or untrusted"""
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if not device.verified and trust_data.is_trusted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot trust an unverified device. Please verify the device first.",
        )

    device.is_trusted = trust_data.is_trusted

    db.commit()
    db.refresh(device)

    return _device_to_response(device)


@router.put("/{device_uuid}/status", response_model=DeviceResponse)
async def change_device_status(
    device_uuid: UUID,
    status_data: DeviceSuspendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suspend, block, or reactivate a device"""
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if status_data.action == "suspend":
        device.status = DeviceStatus.SUSPENDED
        device.inactive_reason = status_data.reason or "Suspended by user"
    elif status_data.action == "block":
        device.status = DeviceStatus.BLOCKED
        device.blocked_reason = status_data.reason or "Blocked by user"
        device.blocked_at = datetime.now(timezone.utc)
        device.is_trusted = False
    elif status_data.action == "activate":
        if device.status == DeviceStatus.BLOCKED:
            device.blocked_reason = None
            device.blocked_at = None
        device.status = DeviceStatus.ACTIVE if device.verified else DeviceStatus.UNVERIFIED
        device.inactive_reason = None

    db.commit()
    db.refresh(device)

    return _device_to_response(device)


# ============ Device Deletion ============


@router.delete("/{device_uuid}", response_model=MessageResponse)
async def delete_device(
    device_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a device and all associated sessions.

    This action cannot be undone.
    """
    device = (
        db.query(Device).filter(Device.id == device_uuid, Device.user_id == current_user.id).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    # Delete the device (sessions will cascade)
    db.delete(device)
    db.commit()

    return MessageResponse(
        success=True,
        message="Device deleted successfully",
    )


# ============ Link Device to User ============


@router.post("/link/{device_id_str}", response_model=DeviceResponse)
async def link_device_to_user(
    device_id_str: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Link an unlinked device to the current user.

    Used when a device was pre-registered without authentication.
    """
    # Find unlinked device by device_id
    device = (
        db.query(Device).filter(Device.device_id == device_id_str, Device.user_id.is_(None)).first()
    )

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unlinked device not found",
        )

    # Check if user already has this device
    existing = (
        db.query(Device)
        .filter(Device.device_id == device_id_str, Device.user_id == current_user.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Device is already linked to your account",
        )

    # Link device to user
    device.user_id = current_user.id
    device.organization_id = current_user.organization_id

    db.commit()
    db.refresh(device)

    return _device_to_response(device)
