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

    model_config = SettingsConfigDict(
        env_prefix="HLPR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from .env file
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
