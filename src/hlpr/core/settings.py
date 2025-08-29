"""Application settings using Pydantic Settings."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="dev", description="Deployment environment")
    debug: bool = Field(default=True, description="Enable debug features")
    api_prefix: str = "/api"
    database_url: str = Field(
        default="postgresql+asyncpg://hlpr:hlprpass@db:5432/hlpr",
        description="SQLAlchemy database URL (async). Use postgres+asyncpg://user:pass@host:5432/db",
    )
    sql_echo: bool = Field(default=False, description="Enable SQLAlchemy echo for debugging")
    
    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    redis_db: int = Field(default=0, description="Redis database number")
    redis_cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    redis_session_ttl: int = Field(default=86400, description="Session TTL in seconds (24 hours)")

    model_config = SettingsConfigDict(
        env_prefix="HLPR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from .env file
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
