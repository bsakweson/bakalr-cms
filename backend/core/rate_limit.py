"""
Rate limiting for Bakalr CMS API
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.core.config import settings


def get_rate_limit(endpoint_name: str = None) -> str:
    """
    Get rate limit value for an endpoint.
    Uses RATE_LIMIT_DEFAULT for all endpoints.

    Args:
        endpoint_name: Name of the endpoint (ignored, for future customization)

    Returns:
        Rate limit string like "1000/hour;100/minute"
    """
    # If rate limiting is disabled, return effectively unlimited
    if not settings.RATE_LIMIT_ENABLED:
        return "1000000/minute"

    return settings.RATE_LIMIT_DEFAULT


def get_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting

    Priority:
    1. API key from header
    2. User ID from auth token
    3. IP address as fallback
    """
    # Try API key first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key}"

    # Try authenticated user
    if hasattr(request.state, "user") and request.state.user:
        user_id = request.state.user.id
        org_id = request.state.user.organization_id
        return f"user:{org_id}:{user_id}"

    # Fallback to IP
    return f"ip:{get_remote_address(request)}"


def get_tenant_identifier(request: Request) -> str:
    """
    Get tenant identifier for tenant-based rate limiting
    """
    if hasattr(request.state, "user") and request.state.user:
        return f"tenant:{request.state.user.organization_id}"
    return get_identifier(request)


# Create limiter instance
limiter = Limiter(
    key_func=get_identifier,
    storage_uri=settings.REDIS_URL,
    strategy="fixed-window",  # or "moving-window" for sliding window
    default_limits=["1000/hour", "100/minute"],  # Default limits
)


# Rate limit configurations for different tiers
class RateLimits:
    """Rate limit tiers for different user types"""

    # Anonymous/IP-based
    ANONYMOUS = ["100/hour", "10/minute"]

    # Authenticated users
    AUTHENTICATED = ["1000/hour", "100/minute"]

    # API keys
    API_KEY_FREE = ["5000/hour", "100/minute"]
    API_KEY_PRO = ["50000/hour", "500/minute"]
    API_KEY_ENTERPRISE = ["unlimited"]

    # Per-tenant limits
    TENANT_FREE = ["10000/hour"]
    TENANT_PRO = ["100000/hour"]
    TENANT_ENTERPRISE = ["unlimited"]

    # Expensive operations
    UPLOAD = ["50/hour", "10/minute"]
    TRANSLATION = ["1000/hour", "50/minute"]
    SEARCH = ["500/hour", "50/minute"]

    # Admin operations
    ADMIN = ["unlimited"]


def check_rate_limit(request: Request, limit: str) -> bool:
    """
    Check if request exceeds rate limit

    Args:
        request: FastAPI request
        limit: Rate limit string (e.g., "100/minute")

    Returns:
        True if within limit, False if exceeded
    """
    try:
        # This will raise RateLimitExceeded if limit is exceeded
        limiter.check_request_limit(request, [limit])
        return True
    except RateLimitExceeded:
        return False


def get_rate_limit_headers(request: Request) -> dict:
    """
    Get rate limit headers for response

    Returns headers:
    - X-RateLimit-Limit: Maximum requests per window
    - X-RateLimit-Remaining: Remaining requests
    - X-RateLimit-Reset: Time when limit resets (Unix timestamp)
    """
    # This is populated by slowapi middleware
    return {
        "X-RateLimit-Limit": request.state.view_rate_limit or "0",
        "X-RateLimit-Remaining": str(getattr(request.state, "view_rate_limit_remaining", 0)),
        "X-RateLimit-Reset": str(getattr(request.state, "view_rate_limit_reset", 0)),
    }


async def check_tenant_quota(request: Request, resource_type: str, amount: int = 1) -> bool:
    """
    Check if tenant has quota for resource

    Args:
        request: FastAPI request
        resource_type: Type of resource (e.g., "storage", "api_calls", "translations")
        amount: Amount to check

    Returns:
        True if within quota, False if exceeded

    Raises:
        HTTPException: If quota exceeded
    """
    if not hasattr(request.state, "user") or not request.state.user:
        return True

    org_id = request.state.user.organization_id

    # TODO: Implement quota checking from database
    # This would check organization subscription tier and usage
    # For now, return True

    return True


def rate_limit_by_tier(request: Request) -> str:
    """
    Get rate limit string based on user tier

    Returns appropriate rate limit based on:
    - API key tier
    - User subscription
    - Organization tier
    """
    # Check for API key
    api_key = request.headers.get("X-API-Key")
    if api_key:
        # TODO: Look up API key tier from database
        # For now, use default API key limits
        return RateLimits.API_KEY_FREE[0]

    # Check for authenticated user
    if hasattr(request.state, "user") and request.state.user:
        # TODO: Look up user/org tier from database
        return RateLimits.AUTHENTICATED[0]

    # Anonymous user
    return RateLimits.ANONYMOUS[0]


# Decorator for custom rate limits
def rate_limit(*limits: str):
    """
    Decorator to apply rate limits to endpoint

    Args:
        limits: Rate limit strings (e.g., "100/minute", "1000/hour")

    Example:
        @router.get("/expensive")
        @rate_limit("10/minute", "100/hour")
        async def expensive_endpoint():
            pass
    """

    def decorator(func):
        # Apply slowapi limit decorator
        return limiter.limit(";".join(limits))(func)

    return decorator
