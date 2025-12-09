"""
Session Service for managing user sessions during authentication.
Handles session creation, validation, and cleanup.
"""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session as DBSession
from user_agents import parse as parse_user_agent

from backend.core.config import settings
from backend.models.device import Device, DeviceStatus
from backend.models.session import RefreshTokenRecord, UserSession
from backend.models.user import User

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing user authentication sessions"""

    def __init__(self, db: DBSession):
        self.db = db

    def create_session(
        self,
        user: User,
        ip_address: str,
        user_agent_string: Optional[str] = None,
        device_id: Optional[str] = None,
        login_method: str = "password",
        mfa_verified: bool = False,
        refresh_token: Optional[str] = None,
    ) -> UserSession:
        """
        Create a new user session after successful login.

        Args:
            user: The authenticated user
            ip_address: Client IP address
            user_agent_string: HTTP User-Agent header
            device_id: Optional device identifier
            login_method: How user authenticated (password, 2fa, api_key, refresh)
            mfa_verified: Whether MFA was used
            refresh_token: The refresh token issued for this session

        Returns:
            Created UserSession instance
        """
        # Parse user agent
        ua_data = self._parse_user_agent(user_agent_string)

        # Get or create device if device_id provided
        device = None
        if device_id:
            device = self._get_or_create_device(user, device_id, ua_data, ip_address)

        # Calculate session expiry (match refresh token expiry)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Create session
        session = UserSession(
            user_id=user.id,
            organization_id=user.organization_id,
            device_id=device.id if device else None,
            ip_address=ip_address,
            user_agent=user_agent_string,
            browser=ua_data.get("browser"),
            browser_version=ua_data.get("browser_version"),
            os=ua_data.get("os"),
            os_version=ua_data.get("os_version"),
            device_type=ua_data.get("device_type"),
            login_method=login_method,
            mfa_verified=mfa_verified,
            expires_at=expires_at,
            is_active=True,
        )

        # Hash refresh token for lookup
        if refresh_token:
            session.refresh_token_hash = self._hash_token(refresh_token)

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        logger.info(f"Created session {session.id} for user {user.email}")

        return session

    def create_refresh_token_record(
        self,
        user: User,
        token: str,
        session: Optional[UserSession] = None,
        device: Optional[Device] = None,
        token_family: Optional[str] = None,
    ) -> RefreshTokenRecord:
        """
        Create a refresh token record for tracking and revocation.

        Args:
            user: Token owner
            token: The raw refresh token
            session: Associated session
            device: Associated device
            token_family: Token family for rotation tracking

        Returns:
            Created RefreshTokenRecord
        """
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        record = RefreshTokenRecord(
            user_id=user.id,
            session_id=session.id if session else None,
            device_id=device.id if device else None,
            token_hash=self._hash_token(token),
            token_family=token_family,
            expires_at=expires_at,
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return record

    def validate_refresh_token(self, token: str) -> Optional[RefreshTokenRecord]:
        """
        Validate a refresh token and return its record.

        Args:
            token: Raw refresh token

        Returns:
            RefreshTokenRecord if valid, None otherwise
        """
        token_hash = self._hash_token(token)

        record = (
            self.db.query(RefreshTokenRecord)
            .filter(
                RefreshTokenRecord.token_hash == token_hash,
                RefreshTokenRecord.is_revoked == False,
                RefreshTokenRecord.expires_at > datetime.now(timezone.utc),
            )
            .first()
        )

        if record:
            # Update usage tracking
            record.used_at = datetime.now(timezone.utc)
            use_count = int(record.use_count or "0")
            record.use_count = str(use_count + 1)
            self.db.commit()

        return record

    def revoke_refresh_token(self, token: str, reason: str = "logout") -> bool:
        """
        Revoke a refresh token.

        Args:
            token: Raw refresh token to revoke
            reason: Reason for revocation

        Returns:
            True if token was found and revoked
        """
        token_hash = self._hash_token(token)

        record = (
            self.db.query(RefreshTokenRecord)
            .filter(RefreshTokenRecord.token_hash == token_hash)
            .first()
        )

        if record:
            record.revoke(reason)
            self.db.commit()
            return True

        return False

    def revoke_token_family(self, family: str, reason: str = "rotation_reuse") -> int:
        """
        Revoke all tokens in a token family (for detecting token reuse attacks).

        Args:
            family: Token family identifier
            reason: Reason for revocation

        Returns:
            Number of tokens revoked
        """
        now = datetime.now(timezone.utc)

        result = (
            self.db.query(RefreshTokenRecord)
            .filter(
                RefreshTokenRecord.token_family == family,
                RefreshTokenRecord.is_revoked == False,
            )
            .update(
                {
                    "is_revoked": True,
                    "revoked_at": now,
                    "revoked_reason": reason,
                }
            )
        )

        self.db.commit()

        if result > 0:
            logger.warning(
                f"Revoked {result} tokens in family {family} - possible token reuse attack"
            )

        return result

    def update_session_activity(self, session_id: UUID, ip_address: Optional[str] = None) -> None:
        """Update the last_active_at timestamp for a session"""
        session = self.db.query(UserSession).filter(UserSession.id == session_id).first()
        if session:
            session.last_active_at = datetime.now(timezone.utc)
            if ip_address:
                session.ip_address = ip_address
            self.db.commit()

    def terminate_session(self, session_id: UUID, reason: str = "logout") -> bool:
        """Terminate a specific session"""
        session = self.db.query(UserSession).filter(UserSession.id == session_id).first()
        if session and session.is_active:
            session.terminate(reason)

            # Revoke associated refresh tokens
            self.db.query(RefreshTokenRecord).filter(
                RefreshTokenRecord.session_id == session_id,
                RefreshTokenRecord.is_revoked == False,
            ).update(
                {
                    "is_revoked": True,
                    "revoked_at": datetime.now(timezone.utc),
                    "revoked_reason": reason,
                }
            )

            self.db.commit()
            return True
        return False

    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions and tokens.
        Should be called periodically (e.g., via scheduled task).

        Returns:
            Number of sessions cleaned up
        """
        now = datetime.now(timezone.utc)

        # Terminate expired active sessions
        result = (
            self.db.query(UserSession)
            .filter(
                UserSession.is_active == True,
                UserSession.expires_at < now,
            )
            .update(
                {
                    "is_active": False,
                    "terminated_at": now,
                    "termination_reason": "expired",
                }
            )
        )

        self.db.commit()

        if result > 0:
            logger.info(f"Cleaned up {result} expired sessions")

        return result

    def _parse_user_agent(self, user_agent_string: Optional[str]) -> dict:
        """Parse user agent string into components"""
        if not user_agent_string:
            return {}

        try:
            ua = parse_user_agent(user_agent_string)
            return {
                "browser": ua.browser.family,
                "browser_version": ua.browser.version_string,
                "os": ua.os.family,
                "os_version": ua.os.version_string,
                "device_type": (
                    "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop")
                ),
            }
        except Exception as e:
            logger.warning(f"Failed to parse user agent: {e}")
            return {}

    def _get_or_create_device(
        self,
        user: User,
        device_id: str,
        ua_data: dict,
        ip_address: str,
    ) -> Device:
        """Get existing device or create new one"""
        device = (
            self.db.query(Device)
            .filter(Device.user_id == user.id, Device.device_id == device_id)
            .first()
        )

        if device:
            # Update last used info
            device.last_used_at = datetime.now(timezone.utc)
            device.last_ip_address = ip_address
            if ua_data.get("browser"):
                device.browser = ua_data["browser"]
            if ua_data.get("browser_version"):
                device.browser_version = ua_data["browser_version"]
            self.db.commit()
            return device

        # Create new device
        device = Device(
            user_id=user.id,
            organization_id=user.organization_id,
            device_id=device_id,
            browser=ua_data.get("browser"),
            browser_version=ua_data.get("browser_version"),
            os=ua_data.get("os"),
            os_version=ua_data.get("os_version"),
            device_type=ua_data.get("device_type"),
            last_ip_address=ip_address,
            status=DeviceStatus.UNVERIFIED,
        )

        self.db.add(device)
        self.db.commit()
        self.db.refresh(device)

        return device

    @staticmethod
    def _hash_token(token: str) -> str:
        """Create a hash of a token for storage and lookup"""
        return hashlib.sha256(token.encode()).hexdigest()


def get_session_service(db: DBSession) -> SessionService:
    """Dependency to get session service"""
    return SessionService(db)
