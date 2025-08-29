"""Redis-based HTTP response caching middleware for FastAPI."""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from hlpr.core.redis_client import redis_delete, redis_get, redis_set
from hlpr.core.settings import get_settings

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching HTTP responses using Redis."""

    def __init__(
        self,
        app: Any,
        cache_prefix: str = "api_cache:",
        exclude_paths: list[str] | None = None,
        exclude_methods: list[str] | None = None,
    ):
        super().__init__(app)
        self.cache_prefix = cache_prefix
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
        self.exclude_methods = exclude_methods or ["POST", "PUT", "DELETE", "PATCH"]
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        """Process the request and handle caching."""
        # Skip caching for excluded paths or methods
        if self._should_skip_cache(request):
            response = await call_next(request)
            return response  # type: ignore

        # Generate cache key
        cache_key = self._generate_cache_key(request)

        # Try to get cached response
        cached_response = await self._get_cached_response(cache_key)
        if cached_response:
            logger.debug(f"Cache hit for key: {cache_key}")
            return cached_response

        # Process request
        response = await call_next(request)

        # Cache the response if it's cacheable
        if self._is_cacheable_response(response):
            await self._cache_response(cache_key, response)
            logger.debug(f"Cached response for key: {cache_key}")

        return response  # type: ignore

    def _should_skip_cache(self, request: Request) -> bool:
        """Determine if request should skip caching."""
        # Skip excluded paths
        if any(path in request.url.path for path in self.exclude_paths):
            return True

        # Skip excluded methods
        if request.method in self.exclude_methods:
            return True

        # Skip if cache control headers indicate no-cache
        cache_control = request.headers.get("Cache-Control", "")
        if "no-cache" in cache_control or "no-store" in cache_control:
            return True

        return False

    def _generate_cache_key(self, request: Request) -> str:
        """Generate a unique cache key for the request."""
        # Include method, path, query params, and user info
        key_components = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
        ]

        # Add user ID if available (from auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            key_components.append(f"user:{user_id}")

        # Create hash of key components
        key_string = "|".join(key_components)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

        return f"{self.cache_prefix}{key_hash}"

    async def _get_cached_response(self, cache_key: str) -> Response | None:
        """Retrieve cached response from Redis."""
        try:
            cached_data = await redis_get(cache_key)
            if not cached_data:
                return None

            # Parse cached response
            response_data = json.loads(cached_data)
            return JSONResponse(
                content=response_data["content"],
                status_code=response_data["status_code"],
                headers=response_data.get("headers", {}),
            )
        except Exception as e:
            logger.warning(f"Error retrieving cached response: {e}")
            return None

    def _is_cacheable_response(self, response: Response) -> bool:
        """Determine if response should be cached."""
        # Only cache successful JSON responses
        if not isinstance(response, JSONResponse):
            return False

        if response.status_code < 200 or response.status_code >= 300:
            return False

        # Check cache control headers
        cache_control = response.headers.get("Cache-Control", "")
        if "no-cache" in cache_control or "no-store" in cache_control:
            return False

        return True

    async def _cache_response(self, cache_key: str, response: Response) -> None:
        """Cache the response in Redis."""
        try:
            # Extract response data
            if hasattr(response, 'body') and response.body:
                if isinstance(response.body, bytes):
                    content = response.body.decode('utf-8')
                elif isinstance(response.body, memoryview):
                    content = bytes(response.body).decode('utf-8')
                else:
                    content = str(response.body)
            else:
                content = "{}"
            
            response_data = {
                "content": content,
                "status_code": response.status_code,
                "headers": dict(response.headers),
            }

            # Cache with TTL
            await redis_set(
                cache_key,
                json.dumps(response_data),
                ttl=self.settings.redis_cache_ttl
            )
        except Exception as e:
            logger.warning(f"Error caching response: {e}")


def invalidate_cache_pattern(pattern: str) -> None:
    """Invalidate cache keys matching a pattern."""
    # This would require Redis SCAN operation - implement if needed
    logger.info(f"Cache invalidation requested for pattern: {pattern}")


async def invalidate_cache_key(cache_key: str) -> None:
    """Invalidate a specific cache key."""
    try:
        await redis_delete(cache_key)
        logger.debug(f"Invalidated cache key: {cache_key}")
    except Exception as e:
        logger.warning(f"Error invalidating cache key {cache_key}: {e}")


async def warm_cache(cache_key: str, data: Any, ttl: int | None = None) -> None:
    """Pre-populate cache with data."""
    try:
        ttl = ttl or get_settings().redis_cache_ttl
        await redis_set(cache_key, json.dumps(data), ttl=ttl)
        logger.debug(f"Warmed cache for key: {cache_key}")
    except Exception as e:
        logger.warning(f"Error warming cache for key {cache_key}: {e}")