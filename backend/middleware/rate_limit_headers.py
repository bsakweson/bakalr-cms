"""
Rate Limit Headers Middleware

Adds X-RateLimit-* headers to all responses to inform clients of their rate limit status.
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
import redis
import time


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add rate limit headers to all responses.
    
    Headers added:
    - X-RateLimit-Limit: Maximum requests allowed in the time window
    - X-RateLimit-Remaining: Requests remaining in current window
    - X-RateLimit-Reset: Unix timestamp when the limit resets
    """
    
    def __init__(self, app, redis_client: redis.Redis, default_limit: int = 100):
        super().__init__(app)
        self.redis_client = redis_client
        self.default_limit = default_limit
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add rate limit headers to response"""
        
        # Get identifier (same logic as rate limiter)
        identifier = self._get_identifier(request)
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        try:
            # Get rate limit info from Redis
            # SlowAPI uses keys like: LIMITER/{identifier}/{endpoint}/{limit}
            # We'll query for the key pattern
            limit, remaining, reset_time = self._get_rate_limit_info(identifier, request.url.path)
            
            # Add headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(reset_time)
            
        except Exception as e:
            # If we can't get rate limit info, add default headers
            current_time = int(time.time())
            response.headers["X-RateLimit-Limit"] = str(self.default_limit)
            response.headers["X-RateLimit-Remaining"] = str(self.default_limit)
            response.headers["X-RateLimit-Reset"] = str(current_time + 60)  # Next minute
        
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Get identifier for rate limiting (matches rate_limit.py logic)"""
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
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"
    
    def _get_rate_limit_info(self, identifier: str, path: str) -> tuple[int, int, int]:
        """
        Get rate limit information from Redis.
        
        Returns:
            (limit, remaining, reset_time)
        """
        # SlowAPI stores rate limit keys in Redis
        # Key pattern: LIMITER/{identifier}/{limit_string}
        # We need to find the key and check remaining calls
        
        try:
            # Look for keys matching the identifier
            # SlowAPI uses format: LIMITER/100 per 1 minute/{identifier}
            pattern = f"LIMITER/100 per 1 minute/{identifier}"
            
            # Try to get the key value
            value = self.redis_client.get(pattern)
            
            if value is not None:
                # Value is the count of requests made
                count = int(value)
                remaining = self.default_limit - count
                
                # Get TTL for reset time
                ttl = self.redis_client.ttl(pattern)
                reset_time = int(time.time()) + (ttl if ttl > 0 else 60)
                
                return self.default_limit, remaining, reset_time
            
        except Exception:
            pass
        
        # Default if we can't get info from Redis
        current_time = int(time.time())
        return self.default_limit, self.default_limit, current_time + 60


def setup_rate_limit_headers_middleware(app, redis_url: str, default_limit: int = 100):
    """
    Setup rate limit headers middleware.
    
    Args:
        app: FastAPI application
        redis_url: Redis connection URL
        default_limit: Default rate limit per minute
    """
    redis_client = redis.from_url(redis_url, decode_responses=True)
    app.add_middleware(RateLimitHeadersMiddleware, redis_client=redis_client, default_limit=default_limit)
