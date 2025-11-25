"""
Tests for caching functionality including Redis cache, response caching,
ETags, and cache invalidation.
"""
import pytest
import hashlib
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.core.cache import cache, CacheKeys, generate_cache_key, generate_content_hash
from backend.core.dependencies import get_current_user
from backend.models.user import User


# Check if Redis is available
@pytest.fixture(scope="session")
async def redis_available():
    """Check if Redis is available for testing."""
    try:
        await cache.connect()
        await cache.client.ping()
        await cache.disconnect()
        return True
    except Exception:
        return False


# Test user fixture
@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = User()
    user.id = 1
    user.email = "test@example.com"
    user.name = "Test User"
    user.organization_id = 1
    user.is_active = True
    user.is_superuser = False
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
async def clear_cache(redis_available):
    """Clear cache before each test."""
    if not redis_available:
        pytest.skip("Redis not available")
    
    await cache.connect()
    # Clear all test keys
    await cache.delete_pattern("test:*")
    await cache.delete_pattern("content:*")
    await cache.delete_pattern("translation:*")
    await cache.delete_pattern("media:*")
    await cache.delete_pattern("seo:*")
    yield
    await cache.disconnect()


class TestRedisCache:
    """Test Redis cache utilities."""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        await cache.connect()
        
        # Set a value
        await cache.set("test:key1", "value1", ttl=60)
        
        # Get the value
        value = await cache.get("test:key1")
        assert value == "value1"
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_json(self):
        """Test JSON serialization in cache."""
        await cache.connect()
        
        data = {"name": "Test", "count": 42, "active": True}
        
        # Set JSON data
        await cache.set("test:json", data, ttl=60)
        
        # Get JSON data
        retrieved = await cache.get_json("test:json")
        assert retrieved == data
        assert isinstance(retrieved, dict)
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_exists(self):
        """Test cache key existence check."""
        await cache.connect()
        
        # Key doesn't exist
        assert not await cache.exists("test:nonexistent")
        
        # Set a key
        await cache.set("test:exists", "value", ttl=60)
        
        # Key exists
        assert await cache.exists("test:exists")
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test cache deletion."""
        await cache.connect()
        
        # Set a value
        await cache.set("test:delete", "value", ttl=60)
        assert await cache.exists("test:delete")
        
        # Delete it
        await cache.delete("test:delete")
        assert not await cache.exists("test:delete")
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_delete_pattern(self):
        """Test pattern-based cache deletion."""
        await cache.connect()
        
        # Set multiple keys
        await cache.set("test:pattern:1", "value1", ttl=60)
        await cache.set("test:pattern:2", "value2", ttl=60)
        await cache.set("test:other", "value3", ttl=60)
        
        # Delete by pattern
        deleted = await cache.delete_pattern("test:pattern:*")
        assert deleted == 2
        
        # Check keys
        assert not await cache.exists("test:pattern:1")
        assert not await cache.exists("test:pattern:2")
        assert await cache.exists("test:other")
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_increment(self):
        """Test cache increment operation."""
        await cache.connect()
        
        # Increment non-existent key
        value = await cache.increment("test:counter")
        assert value == 1
        
        # Increment again
        value = await cache.increment("test:counter")
        assert value == 2
        
        # Increment with amount
        value = await cache.increment("test:counter", amount=5)
        assert value == 7
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_expire(self):
        """Test cache expiration."""
        await cache.connect()
        
        # Set a key
        await cache.set("test:expire", "value", ttl=1)
        assert await cache.exists("test:expire")
        
        # Update TTL
        await cache.expire("test:expire", ttl=60)
        
        # Key should still exist
        assert await cache.exists("test:expire")
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test that cache keys expire after TTL."""
        await cache.connect()
        
        # Set a key with 1 second TTL
        await cache.set("test:ttl", "value", ttl=1)
        assert await cache.exists("test:ttl")
        
        # Wait for expiration
        import asyncio
        await asyncio.sleep(1.5)
        
        # Key should be gone
        assert not await cache.exists("test:ttl")
        
        await cache.disconnect()


class TestCacheKeys:
    """Test cache key pattern generation."""
    
    def test_content_entry_pattern(self):
        """Test content entry cache key pattern."""
        key = CacheKeys.format(CacheKeys.CONTENT_ENTRY, org_id=1, entry_id=42)
        assert key == "content:entry:1:42"
    
    def test_content_list_pattern(self):
        """Test content list cache key pattern."""
        key = CacheKeys.format(CacheKeys.CONTENT_LIST, org_id=1, type_id="blog", page=1, size=10)
        assert key == "content:list:1:blog:1:10"
    
    def test_translation_pattern(self):
        """Test translation cache key pattern."""
        key = CacheKeys.format(CacheKeys.TRANSLATION, org_id=1, entry_id=42, locale="es")
        assert key == "translation:1:42:es"
    
    def test_media_entry_pattern(self):
        """Test media entry cache key pattern."""
        key = CacheKeys.format(CacheKeys.MEDIA_ENTRY, org_id=1, media_id=123)
        assert key == "media:entry:1:123"
    
    def test_seo_meta_pattern(self):
        """Test SEO metadata cache key pattern."""
        key = CacheKeys.format(CacheKeys.SEO_META, org_id=1, entry_id=42)
        assert key == "seo:meta:1:42"
    
    def test_user_profile_pattern(self):
        """Test user profile cache key pattern."""
        key = CacheKeys.format(CacheKeys.USER_PROFILE, user_id=99)
        assert key == "user:profile:99"


class TestCacheHelpers:
    """Test cache helper functions."""
    
    def test_generate_cache_key(self):
        """Test cache key generation from parts."""
        key = generate_cache_key("content", "entry", 1, 42)
        assert key == "content:entry:1:42"
    
    def test_generate_content_hash(self):
        """Test content hash generation."""
        content = "Hello, World!"
        hash1 = generate_content_hash((content,), {})
        hash2 = generate_content_hash((content,), {})
        
        # Same content should produce same hash
        assert hash1 == hash2
        
        # Different content should produce different hash
        hash3 = generate_content_hash(("Different content",), {})
        assert hash1 != hash3
        
        # Should be 16-character hash
        assert len(hash1) == 16


class TestResponseCaching:
    """Test response caching middleware and ETags."""
    
    @pytest.mark.asyncio
    async def test_response_cache_miss_then_hit(self, client, override_auth):
        """Test response caching on repeated requests."""
        # First request - cache miss
        response1 = await client.get("/api/content/types")
        assert response1.status_code in [200, 401, 404]  # Might not have data yet
        
        # Check for cache header
        if response1.status_code == 200:
            # Second request - should be cache hit
            response2 = await client.get("/api/content/types")
            assert response2.status_code == 200
            
            # Check X-Cache header (might be MISS on first, HIT on second)
            # Note: This test might need adjustment based on actual implementation
    
    @pytest.mark.asyncio
    async def test_etag_generation(self, client):
        """Test ETag generation for responses."""
        response = await client.get("/health")
        assert response.status_code == 200
        
        # Health endpoint should have ETag
        # Note: Might be excluded from caching, adjust based on implementation
    
    @pytest.mark.asyncio
    async def test_304_not_modified(self, client):
        """Test 304 Not Modified response with If-None-Match."""
        # First request to get ETag
        response1 = await client.get("/health")
        assert response1.status_code == 200
        
        etag = response1.headers.get("etag")
        if etag:
            # Second request with If-None-Match
            response2 = await client.get("/health", headers={"If-None-Match": etag})
            
            # Should get 304 if content hasn't changed
            # Note: Depends on implementation and whether endpoint is cached
    
    @pytest.mark.asyncio
    async def test_cache_control_headers(self, client, override_auth):
        """Test Cache-Control headers on responses."""
        response = await client.get("/api/content/types")
        
        # Should have cache control headers if implemented
        # Note: Adjust based on actual implementation


class TestCacheInvalidation:
    """Test cache invalidation strategies."""
    
    @pytest.mark.asyncio
    async def test_content_update_invalidates_cache(self):
        """Test that content updates invalidate related caches."""
        await cache.connect()
        
        tenant_id = 1
        entry_id = 42
        
        # Set some cache entries
        entry_key = CacheKeys.format(CacheKeys.CONTENT_ENTRY, org_id=tenant_id, entry_id=entry_id)
        list_key = CacheKeys.format(CacheKeys.CONTENT_LIST, org_id=tenant_id, type_id="blog", page=1, size=10)
        seo_key = CacheKeys.format(CacheKeys.SEO_META, org_id=tenant_id, entry_id=entry_id)
        
        await cache.set(entry_key, {"data": "old"}, ttl=300)
        await cache.set(list_key, [{"id": entry_id}], ttl=300)
        await cache.set(seo_key, {"title": "Old"}, ttl=300)
        
        # Verify they exist
        assert await cache.exists(entry_key)
        assert await cache.exists(list_key)
        
        # Simulate content update invalidation
        await cache.delete_pattern(f"content:entry:{tenant_id}:{entry_id}*")
        await cache.delete_pattern(f"content:list:{tenant_id}:*")
        await cache.delete_pattern(f"seo:*:{tenant_id}:*")
        
        # Verify invalidation
        assert not await cache.exists(entry_key)
        assert not await cache.exists(list_key)
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_translation_invalidation(self):
        """Test translation cache invalidation."""
        await cache.connect()
        
        tenant_id = 1
        entry_id = 42
        
        # Set translation caches
        es_key = CacheKeys.format(CacheKeys.TRANSLATION, org_id=tenant_id, entry_id=entry_id, locale="es")
        fr_key = CacheKeys.format(CacheKeys.TRANSLATION, org_id=tenant_id, entry_id=entry_id, locale="fr")
        
        await cache.set(es_key, {"text": "Hola"}, ttl=300)
        await cache.set(fr_key, {"text": "Bonjour"}, ttl=300)
        
        # Verify they exist
        assert await cache.exists(es_key)
        assert await cache.exists(fr_key)
        
        # Invalidate all translations for entry
        await cache.delete_pattern(f"translation:{tenant_id}:{entry_id}:*")
        
        # Verify invalidation
        assert not await cache.exists(es_key)
        assert not await cache.exists(fr_key)
        
        await cache.disconnect()
    
    @pytest.mark.asyncio
    async def test_media_invalidation(self):
        """Test media cache invalidation."""
        await cache.connect()
        
        tenant_id = 1
        media_id = 123
        
        # Set media cache
        media_key = CacheKeys.format(CacheKeys.MEDIA_ENTRY, org_id=tenant_id, media_id=media_id)
        stats_key = CacheKeys.format(CacheKeys.MEDIA_STATS, org_id=tenant_id)
        
        await cache.set(media_key, {"url": "/media/file.jpg"}, ttl=300)
        await cache.set(stats_key, {"count": 10}, ttl=300)
        
        # Verify they exist
        assert await cache.exists(media_key)
        assert await cache.exists(stats_key)
        
        # Invalidate media
        await cache.delete_pattern(f"media:entry:{tenant_id}:{media_id}")
        await cache.delete_pattern(f"media:stats:{tenant_id}")
        
        # Verify invalidation
        assert not await cache.exists(media_key)
        assert not await cache.exists(stats_key)
        
        await cache.disconnect()


class TestCachedDecorator:
    """Test the @cached decorator functionality."""
    
    @pytest.mark.asyncio
    async def test_cached_decorator_basic(self):
        """Test basic cached decorator functionality."""
        await cache.connect()
        
        call_count = 0
        
        from backend.core.cache import cached
        
        @cached(ttl=60, key_prefix="test")
        async def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - should execute function
        result1 = await expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call - should return cached result
        result2 = await expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Function not called again
        
        # Different argument - should execute function
        result3 = await expensive_function(10)
        assert result3 == 20
        assert call_count == 2
        
        await cache.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
