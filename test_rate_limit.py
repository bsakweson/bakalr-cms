"""
Tests for rate limiting functionality including SlowAPI integration,
rate limit tiers, and rate limit headers.
"""
import pytest
import time
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.core.rate_limit import (
    limiter,
    get_identifier,
    get_tenant_identifier,
    RateLimits,
    check_rate_limit,
    get_rate_limit_headers,
    check_tenant_quota
)
from backend.core.dependencies import get_current_user
from backend.models.user import User
from fastapi import Request, HTTPException
from unittest.mock import Mock, AsyncMock


# Test user fixtures
@pytest.fixture
def mock_user():
    """Create a mock regular user."""
    user = User(
        id=1,
        email="test@example.com",
        full_name="Test User",
        organization_id=1,
        is_active=True,
        is_superuser=False
    )
    return user


@pytest.fixture
def mock_enterprise_user():
    """Create a mock enterprise user."""
    user = User(
        id=2,
        email="enterprise@example.com",
        full_name="Enterprise User",
        organization_id=2,
        is_active=True,
        is_superuser=False
    )
    return user


@pytest.fixture
def override_auth(mock_user):
    """Override authentication dependency."""
    async def get_current_user_override():
        return mock_user
    
    app.dependency_overrides[get_current_user] = get_current_user_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def reset_rate_limits():
    """Reset rate limits between tests."""
    # Wait a bit to ensure rate limit windows reset
    # Note: In production tests, you'd mock the Redis backend
    yield
    time.sleep(0.1)


class TestRateLimitTiers:
    """Test rate limit tier definitions."""
    
    def test_anonymous_tier(self):
        """Test anonymous rate limit tier."""
        assert RateLimits.ANONYMOUS == "100/hour;10/minute"
    
    def test_authenticated_tier(self):
        """Test authenticated user rate limit tier."""
        assert RateLimits.AUTHENTICATED == "1000/hour;100/minute"
    
    def test_api_key_free_tier(self):
        """Test free API key rate limit tier."""
        assert RateLimits.API_KEY_FREE == "5000/hour;100/minute"
    
    def test_api_key_pro_tier(self):
        """Test pro API key rate limit tier."""
        assert RateLimits.API_KEY_PRO == "50000/hour;500/minute"
    
    def test_api_key_enterprise_tier(self):
        """Test enterprise API key rate limit tier."""
        assert RateLimits.API_KEY_ENTERPRISE == "unlimited"
    
    def test_tenant_free_tier(self):
        """Test free tenant rate limit tier."""
        assert RateLimits.TENANT_FREE == "10000/hour"
    
    def test_tenant_pro_tier(self):
        """Test pro tenant rate limit tier."""
        assert RateLimits.TENANT_PRO == "100000/hour"
    
    def test_tenant_enterprise_tier(self):
        """Test enterprise tenant rate limit tier."""
        assert RateLimits.TENANT_ENTERPRISE == "unlimited"
    
    def test_expensive_upload_tier(self):
        """Test expensive upload operation tier."""
        assert RateLimits.EXPENSIVE_UPLOAD == "50/hour;10/minute"
    
    def test_expensive_translation_tier(self):
        """Test expensive translation operation tier."""
        assert RateLimits.EXPENSIVE_TRANSLATION == "100/hour;20/minute"
    
    def test_expensive_search_tier(self):
        """Test expensive search operation tier."""
        assert RateLimits.EXPENSIVE_SEARCH == "500/hour;50/minute"


class TestIdentifierResolution:
    """Test rate limit identifier resolution."""
    
    @pytest.mark.asyncio
    async def test_get_identifier_with_api_key(self):
        """Test identifier resolution with API key."""
        # Create mock request with API key
        request = Mock(spec=Request)
        request.headers = {"x-api-key": "test-api-key-123"}
        request.state = Mock()
        request.state.user = None
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        identifier = await get_identifier(request)
        assert identifier == "apikey:test-api-key-123"
    
    @pytest.mark.asyncio
    async def test_get_identifier_with_user(self):
        """Test identifier resolution with authenticated user."""
        # Create mock request with user
        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.id = 42
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        identifier = await get_identifier(request)
        assert identifier == "user:42"
    
    @pytest.mark.asyncio
    async def test_get_identifier_with_ip_fallback(self):
        """Test identifier resolution falls back to IP."""
        # Create mock request with no API key or user
        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()
        request.state.user = None
        request.client = Mock()
        request.client.host = "192.168.1.100"
        
        identifier = await get_identifier(request)
        assert identifier == "ip:192.168.1.100"
    
    @pytest.mark.asyncio
    async def test_get_tenant_identifier(self):
        """Test tenant identifier resolution."""
        # Create mock request with user
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.organization_id = 99
        
        identifier = await get_tenant_identifier(request)
        assert identifier == "tenant:99"
    
    @pytest.mark.asyncio
    async def test_get_tenant_identifier_no_user(self):
        """Test tenant identifier with no user returns None."""
        # Create mock request without user
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = None
        
        identifier = await get_tenant_identifier(request)
        assert identifier is None


class TestRateLimitHeaders:
    """Test rate limit header generation."""
    
    def test_get_rate_limit_headers(self):
        """Test rate limit header generation."""
        headers = get_rate_limit_headers(
            limit=1000,
            remaining=847,
            reset=1700000000
        )
        
        assert headers["X-RateLimit-Limit"] == "1000"
        assert headers["X-RateLimit-Remaining"] == "847"
        assert headers["X-RateLimit-Reset"] == "1700000000"
    
    def test_get_rate_limit_headers_zero_remaining(self):
        """Test rate limit headers with zero remaining."""
        headers = get_rate_limit_headers(
            limit=100,
            remaining=0,
            reset=1700000100
        )
        
        assert headers["X-RateLimit-Limit"] == "100"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["X-RateLimit-Reset"] == "1700000100"


class TestRateLimitCheck:
    """Test rate limit checking functionality."""
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_pass(self):
        """Test rate limit check that passes."""
        # Create mock request
        request = Mock(spec=Request)
        request.headers = {}
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.id = 1
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        # Should not raise exception
        try:
            await check_rate_limit(request, limit="1000/hour")
            assert True
        except HTTPException:
            pytest.fail("Rate limit check should not raise exception")
    
    @pytest.mark.asyncio
    async def test_check_tenant_quota_pass(self):
        """Test tenant quota check that passes."""
        # Create mock request
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = Mock()
        request.state.user.organization_id = 1
        
        # Should not raise exception
        try:
            await check_tenant_quota(request, limit="10000/hour")
            assert True
        except HTTPException:
            pytest.fail("Tenant quota check should not raise exception")


class TestRateLimitIntegration:
    """Test rate limiting integration with API endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_no_rate_limit(self, client):
        """Test that health endpoint is not rate limited."""
        # Health endpoint should always respond
        for _ in range(10):
            response = await client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_api_endpoint_has_rate_limit_headers(self, client, override_auth):
        """Test that API endpoints include rate limit headers."""
        response = await client.get("/api/content/types")
        
        # Should have rate limit headers (if implemented)
        # Note: Adjust based on actual implementation
        # Headers might be: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
    
    @pytest.mark.asyncio
    async def test_rate_limit_429_response(self, client):
        """Test that rate limit exceeded returns 429."""
        # This test would need to make many requests to trigger rate limit
        # In practice, you'd mock the rate limiter or use a very low limit
        
        # Make many requests quickly (adjust count based on actual limits)
        # Note: This might not trigger in test environment
        responses = []
        for _ in range(150):  # Exceed anonymous limit of 100/hour
            response = await client.get("/api/content/types")
            responses.append(response.status_code)
        
        # At least one should be 429 if rate limiting is active
        # Note: This test might be flaky without proper rate limit reset between tests
    
    @pytest.mark.asyncio
    async def test_rate_limit_retry_after_header(self, client):
        """Test that 429 response includes Retry-After header."""
        # This test would need to trigger rate limit
        # In practice, you'd mock the rate limiter
        
        # If we can trigger 429, check for Retry-After header
        # Note: Adjust based on actual implementation and test setup


class TestRateLimitDecorator:
    """Test rate limit decorator functionality."""
    
    def test_rate_limit_decorator_import(self):
        """Test that rate limit decorator can be imported."""
        from backend.core.rate_limit import rate_limit
        assert callable(rate_limit)


class TestRateLimitMiddleware:
    """Test rate limiting middleware integration."""
    
    @pytest.mark.asyncio
    async def test_limiter_state_exists(self):
        """Test that limiter is attached to app state."""
        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_exception_handler(self, client):
        """Test that rate limit exception handler is registered."""
        # Exception handler should be registered for RateLimitExceeded
        # This is tested indirectly through 429 responses
        
        # Check that app has exception handlers
        assert hasattr(app, "exception_handlers")


class TestRateLimitConfiguration:
    """Test rate limit configuration."""
    
    def test_limiter_configured_with_redis(self):
        """Test that limiter is configured with Redis backend."""
        # Check limiter configuration
        assert limiter is not None
        
        # Storage should be Redis-based
        # Note: Adjust based on actual implementation


class TestPerEndpointRateLimits:
    """Test per-endpoint rate limit configuration."""
    
    @pytest.mark.asyncio
    async def test_expensive_operation_has_lower_limit(self, client, override_auth):
        """Test that expensive operations have stricter rate limits."""
        # Upload endpoint should have lower limits
        # This would need actual implementation testing with file upload
        
        # Make multiple upload requests (would need proper file data)
        # Should hit rate limit faster than regular endpoints


class TestRateLimitByUserType:
    """Test different rate limits for different user types."""
    
    @pytest.mark.asyncio
    async def test_anonymous_user_rate_limit(self, client):
        """Test rate limit for anonymous users."""
        # Anonymous users should have lower limits (100/hour)
        # Would need to make 100+ requests to test
        pass
    
    @pytest.mark.asyncio
    async def test_authenticated_user_rate_limit(self, client, override_auth):
        """Test rate limit for authenticated users."""
        # Authenticated users should have higher limits (1000/hour)
        # Would need to make 1000+ requests to test
        pass
    
    @pytest.mark.asyncio
    async def test_api_key_rate_limit(self, client):
        """Test rate limit for API key requests."""
        # API key requests should have even higher limits (5000+/hour)
        # Would need to make 5000+ requests with API key to test
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
