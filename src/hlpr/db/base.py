"""Database base configuration: engine, session and metadata."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from hlpr.core.settings import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_SessionFactory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _SessionFactory
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=settings.sql_echo, future=True)
        _SessionFactory = async_sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _SessionFactory is None:
        get_engine()
    assert _SessionFactory is not None
    return _SessionFactory


async def get_session() -> AsyncGenerator[AsyncSession]:  # FastAPI dependency style
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_models(drop: bool = False) -> None:
    """Create database tables (optionally dropping first)."""
    engine = get_engine()
    async with engine.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
