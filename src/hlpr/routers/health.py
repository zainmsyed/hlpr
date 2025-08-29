"""Health and readiness endpoints."""
from fastapi import APIRouter

from hlpr.core.cache_manager import get_cache_info
from hlpr.core.redis_client import test_redis_connection
from hlpr.core.settings import get_settings

router = APIRouter()

@router.get("/health", tags=["meta"])  # simple health
async def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.environment,
        "debug": settings.debug,
        "version": "0.1.0",
    }


@router.get("/health/cache", tags=["meta"])
async def cache_health() -> dict[str, object]:
    """Cache health check with Redis connection and statistics."""
    try:
        redis_ok = await test_redis_connection()
        cache_info = await get_cache_info()
        
        return {
            "status": "ok" if redis_ok else "error",
            "redis_connected": redis_ok,
            "cache_info": cache_info,
        }
    except Exception as e:
        return {
            "status": "error",
            "redis_connected": False,
            "error": str(e),
        }


@router.get("/cache/stats", tags=["cache"])
async def cache_stats() -> dict[str, object]:
    """Get detailed cache statistics."""
    try:
        cache_info = await get_cache_info()
        return {
            "status": "ok",
            "cache_statistics": cache_info,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
