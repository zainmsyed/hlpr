"""Cache management utilities for Redis-based caching."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from hlpr.core.redis_client import (
    get_redis_client,
    redis_delete,
    redis_exists,
    redis_get,
    redis_set,
)
from hlpr.core.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    hit_ratio: float = 0.0
    total_requests: int = 0


class CacheManager:
    """Manager for Redis-based caching operations with monitoring."""

    def __init__(self, prefix: str = "hlpr_cache:"):
        self.prefix = prefix
        self.settings = get_settings()
        self._stats = CacheStats()
        self._stats_lock = asyncio.Lock()

    def _make_key(self, key: str) -> str:
        """Create a prefixed cache key."""
        return f"{self.prefix}{key}"

    async def get(self, key: str) -> Any | None:
        """Get a value from cache."""
        cache_key = self._make_key(key)

        try:
            value = await redis_get(cache_key)
            if value is not None:
                # Try to parse as JSON
                try:
                    parsed_value = json.loads(value)
                    await self._record_hit()
                    return parsed_value
                except json.JSONDecodeError:
                    # Return raw string if not JSON
                    await self._record_hit()
                    return value
            else:
                await self._record_miss()
                return None
        except Exception as e:
            logger.warning(f"Error getting cache key {cache_key}: {e}")
            await self._record_miss()
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        serialize: bool = True
    ) -> bool:
        """Set a value in cache."""
        cache_key = self._make_key(key)
        ttl = ttl or self.settings.redis_cache_ttl

        try:
            # Serialize value if needed
            if serialize and not isinstance(value, str):
                value = json.dumps(value)

            success = await redis_set(cache_key, value, ttl=ttl)
            if success:
                await self._record_set()
            return bool(success)
        except Exception as e:
            logger.warning(f"Error setting cache key {cache_key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a value from cache."""
        cache_key = self._make_key(key)

        try:
            result = await redis_delete(cache_key)
            if result > 0:
                await self._record_delete()
            return bool(result > 0)
        except Exception as e:
            logger.warning(f"Error deleting cache key {cache_key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache."""
        cache_key = self._make_key(key)

        try:
            result = await redis_exists(cache_key)
            return bool(result)
        except Exception as e:
            logger.warning(f"Error checking cache key {cache_key}: {e}")
            return False

    async def get_or_set(
        self,
        key: str,
        default_func: Callable[[], Any],
        ttl: int | None = None
    ) -> Any:
        """Get a value from cache, or set it using the default function if not found."""
        # Try to get from cache first
        value = await self.get(key)
        if value is not None:
            return value

        # Generate value using default function
        value = await default_func()

        # Cache the value
        await self.set(key, value, ttl=ttl)

        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern."""
        try:
            client = await get_redis_client()
            # Use SCAN to find keys matching pattern
            deleted_count = 0
            async for key in client.scan_iter(f"{self.prefix}{pattern}"):
                result = await client.delete(key)
                deleted_count += result
                if result > 0:
                    await self._record_delete()

            logger.info(f"Invalidated {deleted_count} cache keys matching pattern: {pattern}")
            return deleted_count
        except Exception as e:
            logger.warning(f"Error invalidating cache pattern {pattern}: {e}")
            return 0

    async def clear_all(self) -> int:
        """Clear all cache keys with this manager's prefix."""
        return await self.invalidate_pattern("*")

    async def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        async with self._stats_lock:
            # Calculate hit ratio
            if self._stats.total_requests > 0:
                self._stats.hit_ratio = self._stats.hits / self._stats.total_requests
            return self._stats

    async def reset_stats(self) -> None:
        """Reset cache statistics."""
        async with self._stats_lock:
            self._stats = CacheStats()

    async def _record_hit(self) -> None:
        """Record a cache hit."""
        async with self._stats_lock:
            self._stats.hits += 1
            self._stats.total_requests += 1

    async def _record_miss(self) -> None:
        """Record a cache miss."""
        async with self._stats_lock:
            self._stats.misses += 1
            self._stats.total_requests += 1

    async def _record_set(self) -> None:
        """Record a cache set operation."""
        async with self._stats_lock:
            self._stats.sets += 1

    async def _record_delete(self) -> None:
        """Record a cache delete operation."""
        async with self._stats_lock:
            self._stats.deletes += 1


# Global cache manager instances
api_cache = CacheManager(prefix="api:")
meeting_cache = CacheManager(prefix="meeting:")
document_cache = CacheManager(prefix="document:")
summarization_cache = CacheManager(prefix="summarization:")


async def get_cache_info() -> dict[str, Any]:
    """Get comprehensive cache information."""
    try:
        client = await get_redis_client()
        info = await client.info()

        cache_managers = [api_cache, meeting_cache, document_cache, summarization_cache]
        manager_stats = {}

        for manager in cache_managers:
            stats = await manager.get_stats()
            manager_stats[manager.prefix.rstrip(":")] = {
                "hits": stats.hits,
                "misses": stats.misses,
                "sets": stats.sets,
                "deletes": stats.deletes,
                "hit_ratio": round(stats.hit_ratio * 100, 2),
                "total_requests": stats.total_requests,
            }

        return {
            "redis_info": {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_connections_received": info.get("total_connections_received", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            },
            "cache_managers": manager_stats,
        }
    except Exception as e:
        logger.error(f"Error getting cache info: {e}")
        return {"error": str(e)}


async def warm_meeting_cache(meeting_id: int, meeting_data: dict[str, Any]) -> None:
    """Warm cache with meeting data."""
    cache_key = f"meeting:{meeting_id}"
    await meeting_cache.set(cache_key, meeting_data, ttl=3600)  # 1 hour TTL


async def warm_summarization_cache(meeting_id: int, summary_data: dict[str, Any]) -> None:
    """Warm cache with summarization data."""
    cache_key = f"summary:{meeting_id}"
    await summarization_cache.set(cache_key, summary_data, ttl=1800)  # 30 minutes TTL


async def invalidate_meeting_cache(meeting_id: int) -> None:
    """Invalidate all cache entries related to a meeting."""
    patterns = [
        f"meeting:{meeting_id}",
        f"summary:{meeting_id}",
    ]

    for pattern in patterns:
        await meeting_cache.invalidate_pattern(pattern)
        await summarization_cache.invalidate_pattern(pattern)