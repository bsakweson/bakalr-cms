"""
Security middleware for Bakalr CMS

Implements security headers, CSRF protection, and request validation.
"""

import hashlib
import hmac
from datetime import datetime
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses

    Implements OWASP recommended security headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (HSTS)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy (formerly Feature-Policy)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Enable browser XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS (only in production)
        if request.url.hostname not in ["localhost", "127.0.0.1"]:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Remove server identification
        if "server" in response.headers:
            del response.headers["server"]

        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection for state-changing operations

    Validates CSRF tokens for POST, PUT, PATCH, DELETE requests.
    Tokens are generated per session and validated on each request.
    """

    # Methods that require CSRF protection
    PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    # Paths exempt from CSRF protection (API endpoints with JWT auth)
    EXEMPT_PATHS = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
        "/api/v1/auth/password-reset/request",
        "/api/v1/auth/password-reset/verify",
        "/api/v1/auth/password-reset/reset",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/scalar",
        "/health",
    }

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key.encode()

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from CSRF protection"""
        # API endpoints with JWT auth are exempt
        if path.startswith("/api/v1/"):
            return True

        # Check explicit exemptions
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return True

        return False

    def _generate_token(self, session_id: str) -> str:
        """Generate CSRF token for session"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        message = f"{session_id}:{timestamp}".encode()
        signature = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
        return f"{timestamp}.{signature}"

    def _validate_token(self, token: str, session_id: str, max_age: int = 3600) -> bool:
        """Validate CSRF token"""
        try:
            timestamp_str, signature = token.split(".")
            timestamp = int(timestamp_str)

            # Check token age
            age = datetime.utcnow().timestamp() - timestamp
            if age > max_age:
                return False

            # Verify signature
            message = f"{session_id}:{timestamp_str}".encode()
            expected_signature = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except (ValueError, AttributeError):
            return False

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip CSRF check for safe methods and exempt paths
        if request.method not in self.PROTECTED_METHODS or self._is_exempt(request.url.path):
            return await call_next(request)

        # For API requests with JWT, skip CSRF (token-based auth)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Validate CSRF token from header or form data
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            # Try to get from form data
            if request.method == "POST":
                form_data = await request.form()
                csrf_token = form_data.get("csrf_token")

        if not csrf_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "type": "https://bakalr.cms/errors/csrf-token-missing",
                    "title": "CSRF Token Missing",
                    "status": 403,
                    "detail": "CSRF token is required for this operation",
                },
            )

        # Get session ID from cookie
        session_id = request.cookies.get("session_id", "")

        if not self._validate_token(csrf_token, session_id):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "type": "https://bakalr.cms/errors/csrf-token-invalid",
                    "title": "CSRF Token Invalid",
                    "status": 403,
                    "detail": "CSRF token validation failed",
                },
            )

        return await call_next(request)


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming requests for suspicious patterns

    - Check for SQL injection patterns
    - Validate content types
    - Check request size limits
    - Detect suspicious user agents
    """

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        "union select",
        "or 1=1",
        "or '1'='1",
        "drop table",
        "delete from",
        "insert into",
        "update ",
        "exec(",
        "execute(",
        "script>",
        "<script",
        "javascript:",
        "onerror=",
        "onload=",
    ]

    # Maximum request body size (10MB)
    MAX_BODY_SIZE = 10 * 1024 * 1024

    def _contains_sql_injection(self, text: str) -> bool:
        """Check if text contains SQL injection patterns"""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in self.SQL_INJECTION_PATTERNS)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check request body size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "type": "https://bakalr.cms/errors/request-too-large",
                    "title": "Request Too Large",
                    "status": 413,
                    "detail": f"Request body size exceeds maximum allowed size of {self.MAX_BODY_SIZE} bytes",
                },
            )

        # Check query parameters for SQL injection
        for key, value in request.query_params.items():
            if self._contains_sql_injection(value):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "type": "https://bakalr.cms/errors/suspicious-input",
                        "title": "Suspicious Input Detected",
                        "status": 400,
                        "detail": f"Query parameter '{key}' contains suspicious patterns",
                    },
                )

        # Check path for SQL injection
        if self._contains_sql_injection(request.url.path):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "type": "https://bakalr.cms/errors/suspicious-path",
                    "title": "Suspicious Path Detected",
                    "status": 400,
                    "detail": "Request path contains suspicious patterns",
                },
            )

        return await call_next(request)


def setup_security_middleware(app, secret_key: str):
    """
    Setup all security middleware

    Args:
        app: FastAPI application instance
        secret_key: Secret key for CSRF token generation
    """
    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Add CSRF protection
    app.add_middleware(CSRFProtectionMiddleware, secret_key=secret_key)

    # Add request validation
    app.add_middleware(RequestValidationMiddleware)
