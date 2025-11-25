"""
Response caching middleware for FastAPI
"""
import hashlib
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers
from backend.core.cache import cache
from backend.core.config import settings


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for caching HTTP responses
    
    Caches GET requests by default with configurable TTL.
    Respects Cache-Control headers and ETags.
    """
    
    def __init__(
        self,
        app,
        default_ttl: int = 300,  # 5 minutes
        cache_methods: tuple = ("GET",),
        exclude_paths: tuple = ("/health", "/api/docs", "/api/redoc", "/api/openapi.json"),
    ):
        super().__init__(app)
        self.default_ttl = default_ttl
        self.cache_methods = cache_methods
        self.exclude_paths = exclude_paths
    
    def should_cache(self, request: Request) -> bool:
        """Determine if request should be cached"""
        # Only cache specified methods
        if request.method not in self.cache_methods:
            return False
        
        # Don't cache excluded paths
        for path in self.exclude_paths:
            if request.url.path.startswith(path):
                return False
        
        # Don't cache if user is authenticated (for now)
        # TODO: Add user-specific caching
        if hasattr(request.state, "user") and request.state.user:
            return False
        
        return True
    
    def generate_cache_key(self, request: Request) -> str:
        """Generate cache key for request"""
        # Include method, path, and query params
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items()))
        ]
        
        # Include accept header for content negotiation
        accept = request.headers.get("accept", "")
        if accept:
            key_parts.append(accept)
        
        key_string = ":".join(key_parts)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
        return f"response:{key_hash}"
    
    def generate_etag(self, content: bytes) -> str:
        """Generate ETag for response content"""
        return f'"{hashlib.md5(content).hexdigest()}"'
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching"""
        # Check if should cache
        if not self.should_cache(request):
            return await call_next(request)
        
        # Generate cache key
        cache_key = self.generate_cache_key(request)
        
        # Check for If-None-Match header (ETag validation)
        if_none_match = request.headers.get("if-none-match")
        
        # Try to get from cache
        try:
            cached_data = await cache.get_json(cache_key)
            
            if cached_data:
                cached_etag = cached_data.get("etag")
                
                # Check ETag match
                if if_none_match and cached_etag == if_none_match:
                    # Return 304 Not Modified
                    return Response(
                        status_code=304,
                        headers={
                            "etag": cached_etag,
                            "x-cache": "HIT-304"
                        }
                    )
                
                # Return cached response
                response = Response(
                    content=cached_data["content"],
                    status_code=cached_data["status_code"],
                    headers=dict(cached_data["headers"]),
                    media_type=cached_data.get("media_type")
                )
                response.headers["x-cache"] = "HIT"
                response.headers["etag"] = cached_etag
                return response
                
        except Exception as e:
            print(f"Cache retrieval error: {e}")
        
        # Call endpoint
        response = await call_next(request)
        
        # Only cache successful responses
        if response.status_code == 200:
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                # Generate ETag
                etag = self.generate_etag(body)
                
                # Prepare cache data
                cache_data = {
                    "content": body.decode("utf-8") if body else "",
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type,
                    "etag": etag
                }
                
                # Cache the response
                await cache.set(cache_key, cache_data, self.default_ttl)
                
                # Create new response with ETag
                new_response = Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                new_response.headers["x-cache"] = "MISS"
                new_response.headers["etag"] = etag
                new_response.headers["cache-control"] = f"max-age={self.default_ttl}"
                
                return new_response
                
            except Exception as e:
                print(f"Cache storage error: {e}")
        
        return response


def add_cache_headers(
    response: Response,
    max_age: int = 300,
    public: bool = True,
    must_revalidate: bool = False
):
    """
    Add cache control headers to response
    
    Args:
        response: FastAPI Response object
        max_age: Cache duration in seconds
        public: If True, allows shared caches (CDN)
        must_revalidate: If True, requires revalidation after expiry
    """
    directives = []
    
    if public:
        directives.append("public")
    else:
        directives.append("private")
    
    directives.append(f"max-age={max_age}")
    
    if must_revalidate:
        directives.append("must-revalidate")
    
    response.headers["cache-control"] = ", ".join(directives)
    
    return response


def no_cache(response: Response):
    """Disable caching for response"""
    response.headers["cache-control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["pragma"] = "no-cache"
    response.headers["expires"] = "0"
    return response
