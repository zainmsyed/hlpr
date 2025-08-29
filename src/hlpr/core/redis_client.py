"""Redis client and connection management for hlpr."""
from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from hlpr.core.settings import get_settings

logger = logging.getLogger(__name__)

# Global Redis connection pool
_redis_pool: ConnectionPool | None = None


async def get_redis_client() -> redis.Redis:
    """Get a Redis client instance with connection pooling."""
    global _redis_pool

    settings = get_settings()

    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            settings.redis_url,
            db=settings.redis_db,
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
        )
        logger.info(f"Created Redis connection pool: {settings.redis_url}")

    return redis.Redis(connection_pool=_redis_pool)


async def test_redis_connection() -> bool:
    """Test Redis connection and return True if successful."""
    try:
        client = await get_redis_client()
        result = await client.ping()
        logger.info("Redis connection test successful")
        return result is True  # ping() returns True on success when decode_responses=True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False


async def close_redis_connection():
    """Close Redis connection pool."""
    global _redis_pool

    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
        logger.info("Redis connection pool closed")


# Utility functions for common Redis operations
async def redis_get(key: str) -> str | None:
    """Get a value from Redis."""
    client = await get_redis_client()
    return await client.get(key)


async def redis_set(key: str, value: Any, ttl: int | None = None) -> bool:
    """Set a value in Redis with optional TTL."""
    client = await get_redis_client()
    return await client.set(key, value, ex=ttl)


async def redis_delete(key: str) -> int:
    """Delete a key from Redis."""
    client = await get_redis_client()
    return await client.delete(key)


async def redis_exists(key: str) -> bool:
    """Check if a key exists in Redis."""
    client = await get_redis_client()
    return await client.exists(key) == 1