"""
Redis caching utilities for Bakalr CMS
"""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional

import redis as sync_redis
import redis.asyncio as redis

from backend.core.config import settings


class RedisCache:
    """Redis cache manager with async support"""

    _instance: Optional["RedisCache"] = None
    _redis_client: Optional[redis.Redis] = None
    _sync_redis_client: Optional[sync_redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self):
        """Initialize Redis connection"""
        if self._redis_client is None:
            self._redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )

    def _get_sync_client(self) -> Optional[sync_redis.Redis]:
        """Get or create synchronous Redis client"""
        if self._sync_redis_client is None:
            try:
                self._sync_redis_client = sync_redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                )
            except Exception as e:
                print(f"Sync Redis connection error: {e}")
                return None
        return self._sync_redis_client

    async def disconnect(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.aclose()
            self._redis_client = None
        if self._sync_redis_client:
            self._sync_redis_client.close()
            self._sync_redis_client = None

    @property
    def client(self) -> redis.Redis:
        """Get Redis client"""
        if self._redis_client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis_client

    # ==================== Synchronous Methods ====================

    def get_sync(self, key: str) -> Optional[str]:
        """Get value from cache (synchronous version)"""
        try:
            client = self._get_sync_client()
            if client:
                return client.get(key)
            return None
        except Exception as e:
            print(f"Sync cache get error: {e}")
            return None

    def set_sync(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache (synchronous version)"""
        try:
            client = self._get_sync_client()
            if not client:
                return False

            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)

            if ttl:
                client.setex(key, ttl, value)
            else:
                client.set(key, value)
            return True
        except Exception as e:
            print(f"Sync cache set error: {e}")
            return False

    def get_json_sync(self, key: str) -> Optional[Any]:
        """Get and deserialize JSON value from cache (synchronous version)"""
        value = self.get_sync(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    # ==================== Async Methods ====================

    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return await self.client.get(key)
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            True if successful
        """
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif not isinstance(value, str):
                value = str(value)

            if ttl:
                await self.client.setex(key, ttl, value)
            else:
                await self.client.set(key, value)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Pattern to match (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    async def get_json(self, key: str) -> Optional[Any]:
        """Get and deserialize JSON value from cache"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return await self.client.incrby(key, amount)
        except Exception as e:
            print(f"Cache increment error: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key"""
        try:
            return await self.client.expire(key, ttl)
        except Exception as e:
            print(f"Cache expire error: {e}")
            return False


# Global cache instance
cache = RedisCache()


def generate_cache_key(*parts: str) -> str:
    """
    Generate cache key from parts

    Args:
        parts: Key parts (e.g., 'user', '123', 'profile')

    Returns:
        Cache key string (e.g., 'user:123:profile')
    """
    return ":".join(str(part) for part in parts)


def generate_content_hash(*args, **kwargs) -> str:
    """
    Generate hash of content for cache key

    Args:
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        SHA256 hash of arguments
    """
    content = f"{args}:{sorted(kwargs.items())}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def cached(ttl: int = 300, key_prefix: str = "cache", key_builder: Optional[Callable] = None):
    """
    Decorator for caching function results

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        key_builder: Custom function to build cache key

    Example:
        @cached(ttl=600, key_prefix="user")
        async def get_user(user_id: int):
            return await db.get_user(user_id)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                content_hash = generate_content_hash(*args, **kwargs)
                cache_key = generate_cache_key(key_prefix, func.__name__, content_hash)

            # Try to get from cache
            cached_value = await cache.get_json(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


async def invalidate_cache_pattern(pattern: str):
    """
    Invalidate all cache keys matching pattern

    Args:
        pattern: Pattern to match (e.g., "content:*")
    """
    await cache.delete_pattern(pattern)


# Cache key helpers
class CacheKeys:
    """Cache key patterns for different resources"""

    # Content
    CONTENT_ENTRY = "content:entry:{org_id}:{entry_id}"
    CONTENT_LIST = "content:list:{org_id}:{type_id}:{page}:{size}"
    CONTENT_TYPE = "content:type:{org_id}:{type_id}"

    # Translation
    TRANSLATION = "translation:{org_id}:{entry_id}:{locale}"
    TRANSLATION_LIST = "translation:list:{org_id}:{locale}"

    # Media
    MEDIA_ENTRY = "media:entry:{org_id}:{media_id}"
    MEDIA_LIST = "media:list:{org_id}:{page}:{size}"
    MEDIA_STATS = "media:stats:{org_id}"

    # SEO
    SEO_META = "seo:meta:{org_id}:{entry_id}"
    SEO_SITEMAP = "seo:sitemap:{org_id}"

    # User
    USER_PROFILE = "user:profile:{user_id}"
    USER_PERMISSIONS = "user:permissions:{user_id}"

    @staticmethod
    def format(pattern: str, **kwargs) -> str:
        """Format cache key pattern with values"""
        return pattern.format(**kwargs)


# Alias for backwards compatibility
cache_response = cached
