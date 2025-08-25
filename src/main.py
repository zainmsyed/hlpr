"""
Initialize FastAPI application and include routers.
"""
from fastapi import FastAPI

from hlpr.routers import example


def create_app() -> FastAPI:
    app = FastAPI(
        title="hlpr API",
        version="0.1.0",
        description="API for hlpr built on DSPy and FastAPI",
    )
    app.include_router(example.router, prefix="/example", tags=["example"])
    return app


app = create_app()
