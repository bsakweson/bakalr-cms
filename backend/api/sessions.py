"""
Session Management API endpoints
Migrated from boutique-platform keycloak-bff
"""

from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from backend.api.schemas.session import (
    LoginActivityListResponse,
    LoginActivityResponse,
    SecurityOverviewResponse,
    SessionListResponse,
    SessionResponse,
    SessionRevokeRequest,
    SessionRevokeResponse,
)
from backend.core.dependencies import get_current_user
from backend.db.session import get_db
from backend.models.device import Device
from backend.models.session import RefreshTokenRecord, UserSession
from backend.models.user import User

router = APIRouter(prefix="/sessions", tags=["Sessions"])


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _session_to_response(
    session: UserSession, current_session_id: Optional[UUID] = None
) -> SessionResponse:
    """Convert UserSession model to response schema"""
    return SessionResponse(
        id=session.id,
        device_id=session.device_id,
        ip_address=session.ip_address,
        browser=session.browser,
        browser_version=session.browser_version,
        os=session.os,
        os_version=session.os_version,
        device_type=session.device_type,
        country=session.country,
        city=session.city,
        is_active=session.is_active,
        is_current=session.id == current_session_id if current_session_id else False,
        login_method=session.login_method,
        mfa_verified=session.mfa_verified,
        is_suspicious=session.is_suspicious,
        created_at=session.created_at,
        last_active_at=session.last_active_at,
        expires_at=session.expires_at,
        location_display=session.location_display,
        device_display=session.device_display,
    )


def _session_to_activity(session: UserSession) -> LoginActivityResponse:
    """Convert UserSession to login activity response"""
    duration = None
    if session.terminated_at and session.created_at:
        delta = session.terminated_at - session.created_at
        duration = int(delta.total_seconds() / 60)
    elif session.is_active and session.created_at:
        delta = datetime.now(timezone.utc) - session.created_at
        duration = int(delta.total_seconds() / 60)

    return LoginActivityResponse(
        id=session.id,
        ip_address=session.ip_address,
        location_display=session.location_display,
        device_display=session.device_display,
        login_method=session.login_method,
        mfa_verified=session.mfa_verified,
        is_suspicious=session.is_suspicious,
        suspicious_reason=session.suspicious_reason,
        created_at=session.created_at,
        terminated_at=session.terminated_at,
        termination_reason=session.termination_reason,
        session_duration_minutes=duration,
    )


# ============ Active Sessions ============


@router.get("", response_model=SessionListResponse)
async def list_active_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    List all active sessions for the current user.

    The current session is marked with is_current=true.
    """
    sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        )
        .order_by(desc(UserSession.last_active_at))
        .all()
    )

    current_session_id = None
    if x_session_id:
        try:
            current_session_id = UUID(x_session_id)
        except ValueError:
            pass

    return SessionListResponse(
        sessions=[_session_to_response(s, current_session_id) for s in sessions],
        total=len(sessions),
        current_session_id=current_session_id,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """Get details of a specific session"""
    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    current_session_id = None
    if x_session_id:
        try:
            current_session_id = UUID(x_session_id)
        except ValueError:
            pass

    return _session_to_response(session, current_session_id)


# ============ Session Revocation ============


@router.delete("/{session_id}", response_model=SessionRevokeResponse)
async def revoke_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    reason: Optional[str] = None,
):
    """
    Revoke (terminate) a specific session.

    This will log the user out from that device/browser.
    """
    session = (
        db.query(UserSession)
        .filter(
            UserSession.id == session_id,
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active session not found",
        )

    # Terminate the session
    session.terminate(reason or "revoked")

    # Also revoke associated refresh tokens
    db.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.session_id == session_id,
        RefreshTokenRecord.is_revoked == False,
    ).update(
        {
            "is_revoked": True,
            "revoked_at": datetime.now(timezone.utc),
            "revoked_reason": reason or "session_revoked",
        }
    )

    db.commit()

    return SessionRevokeResponse(
        success=True,
        message="Session revoked successfully",
        revoked_count=1,
    )


@router.post("/revoke", response_model=SessionRevokeResponse)
async def revoke_sessions(
    request: Request,
    revoke_data: SessionRevokeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Revoke multiple sessions at once.

    Options:
    - Provide specific session_ids to revoke
    - Set revoke_all_except_current=true to logout everywhere else
    """
    now = datetime.now(timezone.utc)
    reason = revoke_data.reason or "bulk_revoke"

    current_session_uuid = None
    if x_session_id:
        try:
            current_session_uuid = UUID(x_session_id)
        except ValueError:
            pass

    if revoke_data.revoke_all_except_current:
        # Revoke all sessions except current
        query = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        )

        if current_session_uuid:
            query = query.filter(UserSession.id != current_session_uuid)

        sessions_to_revoke = query.all()
        revoked_count = len(sessions_to_revoke)

        for session in sessions_to_revoke:
            session.is_active = False
            session.terminated_at = now
            session.termination_reason = reason

        # Revoke refresh tokens for these sessions
        session_ids = [s.id for s in sessions_to_revoke]
        if session_ids:
            db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.session_id.in_(session_ids),
                RefreshTokenRecord.is_revoked == False,
            ).update(
                {
                    "is_revoked": True,
                    "revoked_at": now,
                    "revoked_reason": "sessions_revoked",
                },
                synchronize_session=False,
            )

    elif revoke_data.session_ids:
        # Revoke specific sessions
        sessions_to_revoke = (
            db.query(UserSession)
            .filter(
                UserSession.id.in_(revoke_data.session_ids),
                UserSession.user_id == current_user.id,
                UserSession.is_active == True,
            )
            .all()
        )
        revoked_count = len(sessions_to_revoke)

        for session in sessions_to_revoke:
            session.is_active = False
            session.terminated_at = now
            session.termination_reason = reason

        # Revoke refresh tokens
        if revoke_data.session_ids:
            db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.session_id.in_(revoke_data.session_ids),
                RefreshTokenRecord.is_revoked == False,
            ).update(
                {
                    "is_revoked": True,
                    "revoked_at": now,
                    "revoked_reason": "sessions_revoked",
                },
                synchronize_session=False,
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide session_ids or set revoke_all_except_current=true",
        )

    db.commit()

    return SessionRevokeResponse(
        success=True,
        message=f"Revoked {revoked_count} session(s)",
        revoked_count=revoked_count,
    )


@router.post("/revoke-all", response_model=SessionRevokeResponse)
async def revoke_all_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke ALL sessions for the current user, including the current one.

    Use this for security incidents (password compromise, etc.)
    """
    now = datetime.now(timezone.utc)

    # Revoke all active sessions
    result = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
        )
        .update(
            {
                "is_active": False,
                "terminated_at": now,
                "termination_reason": "security_revoke_all",
            },
            synchronize_session=False,
        )
    )

    # Revoke all refresh tokens
    db.query(RefreshTokenRecord).filter(
        RefreshTokenRecord.user_id == current_user.id,
        RefreshTokenRecord.is_revoked == False,
    ).update(
        {
            "is_revoked": True,
            "revoked_at": now,
            "revoked_reason": "security_revoke_all",
        },
        synchronize_session=False,
    )

    db.commit()

    return SessionRevokeResponse(
        success=True,
        message=f"Revoked all {result} session(s). Please log in again.",
        revoked_count=result,
    )


# ============ Login Activity ============


@router.get("/activity/history", response_model=LoginActivityListResponse)
async def get_login_history(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get login activity history for the current user.

    Includes both active and terminated sessions.
    """
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 100:
        per_page = 20

    # Get total count
    total = (
        db.query(func.count(UserSession.id)).filter(UserSession.user_id == current_user.id).scalar()
    )

    # Get paginated results
    offset = (page - 1) * per_page
    sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == current_user.id)
        .order_by(desc(UserSession.created_at))
        .offset(offset)
        .limit(per_page)
        .all()
    )

    return LoginActivityListResponse(
        activities=[_session_to_activity(s) for s in sessions],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=ceil(total / per_page) if total > 0 else 1,
    )


# ============ Security Overview ============


@router.get("/security/overview", response_model=SecurityOverviewResponse)
async def get_security_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a security overview of the user's account.

    Includes device counts, session counts, and security status.
    """
    # Device counts
    total_devices = (
        db.query(func.count(Device.id)).filter(Device.user_id == current_user.id).scalar()
    )

    verified_devices = (
        db.query(func.count(Device.id))
        .filter(Device.user_id == current_user.id, Device.verified == True)
        .scalar()
    )

    trusted_devices = (
        db.query(func.count(Device.id))
        .filter(Device.user_id == current_user.id, Device.is_trusted == True)
        .scalar()
    )

    # Session counts
    active_sessions = (
        db.query(func.count(UserSession.id))
        .filter(UserSession.user_id == current_user.id, UserSession.is_active == True)
        .scalar()
    )

    suspicious_sessions = (
        db.query(func.count(UserSession.id))
        .filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True,
            UserSession.is_suspicious == True,
        )
        .scalar()
    )

    # Recent logins (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_logins = (
        db.query(func.count(UserSession.id))
        .filter(
            UserSession.user_id == current_user.id,
            UserSession.created_at >= thirty_days_ago,
        )
        .scalar()
    )

    return SecurityOverviewResponse(
        total_devices=total_devices or 0,
        verified_devices=verified_devices or 0,
        trusted_devices=trusted_devices or 0,
        active_sessions=active_sessions or 0,
        suspicious_sessions=suspicious_sessions or 0,
        recent_logins_count=recent_logins or 0,
        two_factor_enabled=current_user.two_factor_enabled or False,
        last_password_change=None,  # TODO: Track password changes
        account_created_at=current_user.created_at,
    )
