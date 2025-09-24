"""
Centralized environment/settings loader for the backend.

Usage:
- Import `settings` from this module anywhere in `backend/` to access env vars.
- `.env` is automatically read if present at project root or alongside backend.

Design:
- Uses pydantic-settings (v2) for typed, centralized configuration.
- Ignores unknown env vars to avoid tight coupling.
"""

from __future__ import annotations
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
try:
    # Populate os.environ for third-party libs (OpenAI, Serper, etc.)
    from dotenv import load_dotenv
    load_dotenv(".env")
    load_dotenv("backend/.env")
except Exception:
    # If python-dotenv isn't installed, pydantic will still read env files
    pass


class Settings(BaseSettings):
    """Typed application settings sourced from environment variables."""

    # LLM/model config
    LLM_MODEL: str = Field(default="openai/gpt-4o-mini", description="Default LLM model identifier")

    # Common provider API keys (optional; libraries may read directly from env as well)
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    SERPER_API_KEY: Optional[str] = Field(default=None, description="Serper.dev API key for web search tool")

    # FastAPI server config (optional convenience)
    API_HOST: str = Field(default="0.0.0.0", description="FastAPI host bind address")
    API_PORT: int = Field(default=8000, description="FastAPI port")

    # JWT/auth settings
    JWT_SECRET_KEY: str = Field(
        default="change-this-dev-secret",
        description="Symmetric key used to sign JWTs (HS algorithms)",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, description="Access token expiration window in minutes"
    )

    # Redis / rate limiting
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and rate limiting",
    )
    RATE_LIMIT_WINDOW_SECONDS: int = Field(
        default=60, description="Default rate limit window in seconds"
    )
    RATE_LIMIT_MAX_REQUESTS: int = Field(
        default=30, description="Default maximum requests per window per identity"
    )

    # Settings behavior
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance so env is parsed once."""
    return Settings()


# Eagerly instantiate for the common import pattern: `from config import settings`
settings = get_settings()


def reload_settings() -> Settings:
    """Re-read environment variables and return a fresh Settings object.

    Note: Prefer using `settings` for normal operation; this is only for tests or
    dynamic reload scenarios.
    """
    get_settings.cache_clear()  # type: ignore[attr-defined]
    return get_settings()


