"""
API versioning middleware and utilities.

Supports URL-based versioning (/api/v1, /api/v2) with deprecation warnings.
"""
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone
import re


class APIVersion:
    """API version constants and metadata."""
    
    V1 = "v1"
    V2 = "v2"  # Future version
    
    # Current stable version
    CURRENT = V1
    
    # Version deprecation info
    DEPRECATIONS = {
        # V1: {
        #     "deprecated_at": "2025-06-01",
        #     "sunset_at": "2026-01-01",
        #     "message": "API v1 is deprecated. Please migrate to v2."
        # }
    }
    
    # Supported versions
    SUPPORTED = [V1]


class VersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API versioning.
    
    - Extracts version from URL path (/api/v1/...)
    - Adds deprecation warnings to response headers
    - Validates version is supported
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with versioning logic."""
        
        # Extract version from URL path
        version = self._extract_version(request.url.path)
        
        # Store version in request state for use in endpoints
        request.state.api_version = version
        
        # Process request
        response = await call_next(request)
        
        # Add version header
        if version:
            response.headers["X-API-Version"] = version
        
        # Add deprecation warnings if applicable
        if version and version in APIVersion.DEPRECATIONS:
            deprecation_info = APIVersion.DEPRECATIONS[version]
            response.headers["Deprecation"] = f"date=\"{deprecation_info['deprecated_at']}\""
            response.headers["Sunset"] = deprecation_info["sunset_at"]
            response.headers["Link"] = f'<https://docs.bakalr.cms/api/{APIVersion.CURRENT}>; rel="successor-version"'
            response.headers["X-API-Warn"] = deprecation_info["message"]
        
        return response
    
    def _extract_version(self, path: str) -> Optional[str]:
        """
        Extract API version from URL path.
        
        Args:
            path: Request URL path
        
        Returns:
            Version string (e.g., "v1") or None
        """
        # Match /api/v1, /api/v2, etc.
        match = re.match(r'^/api/(v\d+)', path)
        if match:
            return match.group(1)
        return None


def get_api_version(request: Request) -> str:
    """
    Get API version from request.
    
    Args:
        request: FastAPI request
    
    Returns:
        API version string (e.g., "v1")
    """
    return getattr(request.state, 'api_version', APIVersion.CURRENT)


def require_version(min_version: str):
    """
    Decorator to require minimum API version.
    
    Usage:
        @router.get("/endpoint")
        @require_version("v2")
        async def my_endpoint():
            pass
    """
    def decorator(func: Callable):
        async def wrapper(request: Request, *args, **kwargs):
            current = get_api_version(request)
            if not current or self._compare_versions(current, min_version) < 0:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail=f"This endpoint requires API version {min_version} or higher"
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def _compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    
    Returns:
        -1 if v1 < v2
        0 if v1 == v2
        1 if v1 > v2
    """
    v1_num = int(v1.replace('v', ''))
    v2_num = int(v2.replace('v', ''))
    
    if v1_num < v2_num:
        return -1
    elif v1_num > v2_num:
        return 1
    return 0
