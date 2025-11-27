"""
Security audit logging for Bakalr CMS

Enhanced audit logging for security-related events with structured logging.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import Request

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Security event types for audit logging"""

    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token.refresh"
    PASSWORD_RESET_REQUEST = "auth.password_reset.request"
    PASSWORD_RESET_COMPLETE = "auth.password_reset.complete"
    PASSWORD_CHANGE = "auth.password.change"

    # Authorization events
    ACCESS_DENIED = "authz.access_denied"
    PERMISSION_VIOLATION = "authz.permission_violation"
    ROLE_CHANGE = "authz.role.change"

    # Two-Factor Authentication
    TWO_FACTOR_ENABLED = "auth.2fa.enabled"
    TWO_FACTOR_DISABLED = "auth.2fa.disabled"
    TWO_FACTOR_VERIFIED = "auth.2fa.verified"
    TWO_FACTOR_FAILURE = "auth.2fa.failure"

    # Account security
    ACCOUNT_LOCKED = "account.locked"
    ACCOUNT_UNLOCKED = "account.unlocked"
    ACCOUNT_DELETED = "account.deleted"
    ACCOUNT_CREATED = "account.created"

    # API security
    API_KEY_CREATED = "api.key.created"
    API_KEY_REVOKED = "api.key.revoked"
    API_KEY_USED = "api.key.used"
    RATE_LIMIT_EXCEEDED = "api.rate_limit.exceeded"

    # Data security
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    DATA_DELETION = "data.deletion"
    BULK_OPERATION = "data.bulk_operation"

    # Security violations
    CSRF_VIOLATION = "security.csrf.violation"
    SQL_INJECTION_ATTEMPT = "security.sql_injection.attempt"
    XSS_ATTEMPT = "security.xss.attempt"
    SUSPICIOUS_REQUEST = "security.suspicious_request"
    INVALID_TOKEN = "security.invalid_token"

    # System security
    CONFIG_CHANGE = "system.config.change"
    ADMIN_ACTION = "system.admin.action"
    SECURITY_SETTING_CHANGE = "system.security.change"


class SecurityAuditLogger:
    """
    Security audit logger with structured logging

    Logs security events with context information for compliance and monitoring.
    """

    def __init__(self):
        self.logger = logging.getLogger("security.audit")

    def log_event(
        self,
        event_type: SecurityEventType,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ):
        """
        Log a security event

        Args:
            event_type: Type of security event
            user_id: User ID involved in the event
            username: Username involved in the event
            organization_id: Organization ID
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether the event was successful
            details: Additional event details
            request: FastAPI request object (will extract IP/user agent)
        """
        # Extract request information if provided
        if request:
            if not ip_address:
                ip_address = request.client.host if request.client else None
            if not user_agent:
                user_agent = request.headers.get("user-agent")

        # Build audit log entry
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "success": success,
            "user_id": user_id,
            "username": username,
            "organization_id": organization_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
        }

        # Log based on severity
        log_message = f"Security Event: {event_type.value}"

        if success:
            self.logger.info(log_message, extra={"audit": audit_entry})
        else:
            self.logger.warning(log_message, extra={"audit": audit_entry})

    def log_login_success(
        self,
        user_id: int,
        username: str,
        organization_id: int,
        request: Optional[Request] = None,
        method: str = "password",
    ):
        """Log successful login"""
        self.log_event(
            SecurityEventType.LOGIN_SUCCESS,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            request=request,
            success=True,
            details={"auth_method": method},
        )

    def log_login_failure(
        self,
        username: str,
        request: Optional[Request] = None,
        reason: str = "invalid_credentials",
    ):
        """Log failed login attempt"""
        self.log_event(
            SecurityEventType.LOGIN_FAILURE,
            username=username,
            request=request,
            success=False,
            details={"reason": reason},
        )

    def log_access_denied(
        self,
        user_id: int,
        username: str,
        resource: str,
        action: str,
        request: Optional[Request] = None,
    ):
        """Log access denied event"""
        self.log_event(
            SecurityEventType.ACCESS_DENIED,
            user_id=user_id,
            username=username,
            request=request,
            success=False,
            details={
                "resource": resource,
                "action": action,
            },
        )

    def log_permission_violation(
        self,
        user_id: int,
        username: str,
        required_permission: str,
        request: Optional[Request] = None,
    ):
        """Log permission violation"""
        self.log_event(
            SecurityEventType.PERMISSION_VIOLATION,
            user_id=user_id,
            username=username,
            request=request,
            success=False,
            details={"required_permission": required_permission},
        )

    def log_rate_limit_exceeded(
        self,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        limit: Optional[int] = None,
    ):
        """Log rate limit exceeded"""
        self.log_event(
            SecurityEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            success=False,
            details={
                "endpoint": endpoint,
                "limit": limit,
            },
        )

    def log_csrf_violation(
        self,
        request: Optional[Request] = None,
        user_id: Optional[int] = None,
    ):
        """Log CSRF token violation"""
        self.log_event(
            SecurityEventType.CSRF_VIOLATION,
            user_id=user_id,
            request=request,
            success=False,
            details={"endpoint": request.url.path if request else None},
        )

    def log_sql_injection_attempt(
        self,
        request: Optional[Request] = None,
        pattern: Optional[str] = None,
        location: Optional[str] = None,
    ):
        """Log SQL injection attempt"""
        self.log_event(
            SecurityEventType.SQL_INJECTION_ATTEMPT,
            request=request,
            success=False,
            details={
                "pattern": pattern,
                "location": location,
                "endpoint": request.url.path if request else None,
            },
        )

    def log_data_export(
        self,
        user_id: int,
        username: str,
        organization_id: int,
        export_type: str,
        record_count: int,
        request: Optional[Request] = None,
    ):
        """Log data export operation"""
        self.log_event(
            SecurityEventType.DATA_EXPORT,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            request=request,
            success=True,
            details={
                "export_type": export_type,
                "record_count": record_count,
            },
        )

    def log_bulk_operation(
        self,
        user_id: int,
        username: str,
        organization_id: int,
        operation: str,
        record_count: int,
        request: Optional[Request] = None,
    ):
        """Log bulk operation"""
        self.log_event(
            SecurityEventType.BULK_OPERATION,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            request=request,
            success=True,
            details={
                "operation": operation,
                "record_count": record_count,
            },
        )

    def log_admin_action(
        self,
        user_id: int,
        username: str,
        action: str,
        target: Optional[str] = None,
        request: Optional[Request] = None,
    ):
        """Log admin action"""
        self.log_event(
            SecurityEventType.ADMIN_ACTION,
            user_id=user_id,
            username=username,
            request=request,
            success=True,
            details={
                "action": action,
                "target": target,
            },
        )


# Global security audit logger instance
security_audit_logger = SecurityAuditLogger()


# Convenience functions
def log_security_event(*args, **kwargs):
    """Log a security event"""
    security_audit_logger.log_event(*args, **kwargs)


def log_login_success(*args, **kwargs):
    """Log successful login"""
    security_audit_logger.log_login_success(*args, **kwargs)


def log_login_failure(*args, **kwargs):
    """Log failed login"""
    security_audit_logger.log_login_failure(*args, **kwargs)


def log_access_denied(*args, **kwargs):
    """Log access denied"""
    security_audit_logger.log_access_denied(*args, **kwargs)


def log_permission_violation(*args, **kwargs):
    """Log permission violation"""
    security_audit_logger.log_permission_violation(*args, **kwargs)
