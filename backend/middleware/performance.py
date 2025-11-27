"""
Performance tracking middleware for FastAPI
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from backend.core.performance import performance_monitor

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track request performance metrics"""

    async def dispatch(self, request: Request, call_next):
        # Start timing
        start_time = time.time()

        # Get endpoint path
        endpoint = f"{request.method} {request.url.path}"

        # Process request
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"Request failed: {endpoint} - {str(e)}")
            raise
        finally:
            # Record metrics
            duration = time.time() - start_time
            performance_monitor.record_request(endpoint, duration, status_code)

            # Add performance headers
            if response is not None and hasattr(response, "headers"):
                response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"
                response.headers["X-Process-Time"] = f"{duration:.6f}"

        return response
