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
from typing import Optional, Literal

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
    LLM_MODEL: str = Field(default="gemini/gemini-2.5-flash-preview", description="Default LLM model identifier")
    APP_ENV: Literal["dev", "prod"] = Field(default="dev", description="Default app environment")

    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Alias for Gemini API key; some libs use this name")
    SERPER_API_KEY: Optional[str] = Field(default=None, description="Serper.dev API key for web search tool")

    # LangTrace configuration
    OPIQ_API_KEY: Optional[str] = Field(default=None, description="LangTrace API key for database operations")

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

    # Cache TTLs (seconds)
    CACHE_TTL_DEFAULT_SECONDS: int = Field(
        default=60, description="Default TTL for cached list/detail endpoints"
    )
    CACHE_TTL_LONG_SECONDS: int = Field(
        default=300, description="Longer TTL for less volatile data"
    )

    # Uploads and processing limits
    MAX_UPLOAD_SIZE_BYTES: int = Field(
        default=100 * 1024 * 1024,  # 100MB
        description="Maximum allowed upload size in bytes",
    )
    ALLOWED_UPLOAD_MIME_TYPES: list[str] = Field(
        default_factory=lambda: ["application/pdf"],
        description="Allowed MIME types for uploaded documents",
    )
    MAX_QUERY_CHARS: int = Field(
        default=2000,
        description="Maximum allowed characters for analysis query/prompt",
    )
    ANALYSIS_TIMEOUT_SECONDS: int = Field(
        default=120,
        description="Timeout in seconds for document analysis crew execution",
    )

    # MongoDB
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI",
    )
    MONGODB_DB_NAME: str = Field(
        default="financial_analyzer",
        description="Default MongoDB database name",
    )

    # Settings behavior
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    CLIENT_URL: str = Field(
        default="http://localhost:5173",
        description="Client URL",
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


