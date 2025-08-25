"""Application settings using Pydantic Settings."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = Field(default="dev", description="Deployment environment")
    debug: bool = Field(default=True, description="Enable debug features")
    api_prefix: str = "/api"

    class Config:
        env_prefix = "HLPR_"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
