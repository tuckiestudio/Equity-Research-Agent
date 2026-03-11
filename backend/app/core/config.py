"""
Application configuration settings.
All settings are loaded from environment variables or .env file.
"""
from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    APP_ENV: str = "development"
    SECRET_KEY: str  # Required - no default, must be set in environment
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # Admin emails (comma-separated) - users with these emails get admin privileges
    ADMIN_EMAILS: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://equity_user:equity_pass_dev@localhost:5432/equity_research"
    REDIS_URL: str = "redis://localhost:6379"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- AI Provider Keys ---
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GLM_API_KEY: str = ""
    KIMI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    CHUTES_API_KEY: str = ""

    # --- Data Provider Selection (hot-swappable) ---
    FUNDAMENTALS_PROVIDER: str = "fmp"          # fmp | alpha_vantage | finnhub | eodhd | yfinance
    PRICE_PROVIDER: str = "finnhub"             # finnhub | fmp | polygon | alpha_vantage | yfinance
    PROFILE_PROVIDER: str = "fmp"               # fmp | finnhub | alpha_vantage
    NEWS_PROVIDER: str = "finnhub"              # finnhub | alpha_vantage | eodhd | marketaux

    # --- Data Provider API Keys ---
    FMP_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    EODHD_API_KEY: str = ""
    POLYGON_API_KEY: str = ""

    @model_validator(mode='after')
    def validate_secret_key(self) -> Settings:
        """Validate SECRET_KEY is set and sufficiently long."""
        if not self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return self


settings = Settings()
