"""
Redis caching service for AI responses and frequently accessed data.
"""
import json
import logging
from typing import Any, Optional, Union
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-based caching service."""

    def __init__(self):
        self._redis: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self._connected = False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Redis connection closed")

    async def health_check(self) -> bool:
        """Return whether Redis is reachable for shared production state."""
        if not self._redis:
            return False
        try:
            await self._redis.ping()
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self._connected or not self._redis:
            return None

        try:
            value = await self._redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        expire_seconds: int = 300,
    ) -> bool:
        """Set value in cache with expiration."""
        if not self._connected or not self._redis:
            return False

        try:
            serialized = json.dumps(value)
            await self._redis.setex(key, expire_seconds, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self._connected or not self._redis:
            return False

        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._connected or not self._redis:
            return False

        try:
            return await self._redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        if not self._connected or not self._redis:
            return 0

        try:
            keys = []
            async for key in self._redis.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0


# Global cache instance
cache_service = CacheService()


async def init_cache() -> None:
    """Initialize cache service."""
    await cache_service.connect()


async def close_cache() -> None:
    """Close cache service."""
    await cache_service.disconnect()