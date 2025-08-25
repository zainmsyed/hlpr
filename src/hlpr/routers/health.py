"""Health and readiness endpoints."""
from fastapi import APIRouter

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
