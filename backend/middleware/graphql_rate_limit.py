"""
ASGI middleware for GraphQL rate limiting.

Required because SlowAPI's decorator-based rate limiting doesn't work
with Strawberry GraphQL's routing architecture.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.core.config import settings


class GraphQLRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware specifically for the GraphQL endpoint.

    Applies rate limits at the ASGI middleware level before the request
    reaches Strawberry's GraphQL router.

    Uses Redis-based rate limiting with fixed-window strategy.
    """

    def __init__(self, app, redis_client=None):
        super().__init__(app)
        self.redis_client = redis_client
        # Parse rate limit from settings: "100/hour;20/minute"
        self.rate_limits = self._parse_rate_limit(settings.RATE_LIMIT_GRAPHQL)

    def _parse_rate_limit(self, limit_string: str) -> list:
        """Parse rate limit string into list of (count, seconds) tuples"""
        limits = []
        for limit in limit_string.split(";"):
            parts = limit.strip().split("/")
            if len(parts) == 2:
                count = int(parts[0])
                period = parts[1].lower()

                # Convert period to seconds
                if period == "second":
                    seconds = 1
                elif period == "minute":
                    seconds = 60
                elif period == "hour":
                    seconds = 3600
                elif period == "day":
                    seconds = 86400
                else:
                    seconds = 60  # default to minute

                limits.append((count, seconds))
        return limits

    async def dispatch(self, request: Request, call_next):
        # Only apply rate limiting to GraphQL endpoint
        if request.url.path == "/api/v1/graphql":
            try:
                # Get rate limit identifier
                identifier = self._get_identifier(request)

                # Check rate limits
                for limit_count, limit_seconds in self.rate_limits:
                    if not await self._check_rate_limit(identifier, limit_count, limit_seconds):
                        return self._rate_limit_response(limit_seconds)

            except Exception as e:
                # Log error but don't block request on rate limit failures
                print(f"Rate limit check failed: {e}")

        # Continue to next middleware/handler
        response = await call_next(request)

        # Add rate limit headers to GraphQL responses
        if request.url.path == "/api/v1/graphql" and response.status_code < 500:
            # Add headers showing limits
            response.headers["X-RateLimit-Limit"] = (
                str(self.rate_limits[0][0]) if self.rate_limits else "100"
            )

        return response

    def _get_identifier(self, request: Request) -> str:
        """
        Get rate limit identifier with priority:
        1. API Key
        2. User ID from JWT
        3. IP Address
        """
        # Priority 1: API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"graphql:apikey:{api_key}"

        # Priority 2: Check if user is in request state (from auth middleware)
        if hasattr(request.state, "user") and request.state.user:
            return f"graphql:user:{request.state.user.id}"

        # Priority 3: IP Address (fallback)
        client_ip = request.client.host if request.client else "unknown"
        return f"graphql:ip:{client_ip}"

    async def _check_rate_limit(self, identifier: str, limit: int, seconds: int) -> bool:
        """
        Check if request is within rate limit using Redis.
        Returns True if allowed, False if rate limit exceeded.
        """
        # Import redis here to avoid circular imports
        from backend.core.cache import cache

        if not cache.client:
            # If Redis is not available, allow the request
            return True

        # Create Redis key for this time window
        current_window = int(time.time() / seconds)
        key = f"ratelimit:{identifier}:{seconds}:{current_window}"

        try:
            # Increment counter
            current = await cache.client.incr(key)

            # Set expiry on first increment
            if current == 1:
                await cache.client.expire(key, seconds * 2)  # Keep for 2 windows

            # Check if over limit
            return current <= limit

        except Exception as e:
            print(f"Redis rate limit error: {e}")
            # On error, allow the request
            return True

    def _rate_limit_response(self, retry_after: int) -> JSONResponse:
        """Return GraphQL-compliant rate limit error response"""
        return JSONResponse(
            status_code=429,
            content={
                "errors": [
                    {
                        "message": "GraphQL rate limit exceeded. Please try again later.",
                        "extensions": {"code": "RATE_LIMIT_EXCEEDED", "retry_after": retry_after},
                    }
                ]
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(self.rate_limits[0][0]) if self.rate_limits else "100",
                "X-RateLimit-Remaining": "0",
            },
        )
