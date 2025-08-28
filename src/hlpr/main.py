"""Application factory for hlpr FastAPI app."""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from hlpr.core.errors import AppError, app_error_handler, validation_error_handler
from hlpr.core.settings import get_settings
from hlpr.routers import example
from hlpr.routers import health as health_router
from hlpr.routers import meetings as meetings_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="hlpr API",
        version="0.1.0",
        description="API for hlpr built on DSPy and FastAPI",
    )
    app.include_router(example.router, prefix=f"{settings.api_prefix}/example", tags=["example"])
    app.include_router(health_router.router, prefix=settings.api_prefix)
    app.include_router(meetings_router.router, prefix=settings.api_prefix)

    # Error handlers
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    return app


app = create_app()
