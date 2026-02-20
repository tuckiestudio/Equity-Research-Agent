"""
Data provider registry — config-driven provider selection.

Switch providers by changing env vars. Zero code changes needed.
"""
from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.services.data.protocols import (
    FundamentalsProvider,
    NewsProvider,
    PriceProvider,
    ProfileProvider,
)

logger = get_logger(__name__)

# Provider implementations will register themselves here
_fundamentals_providers: dict[str, type] = {}
_price_providers: dict[str, type] = {}
_profile_providers: dict[str, type] = {}
_news_providers: dict[str, type] = {}

# Active provider instances (set at startup)
_fundamentals: Optional[FundamentalsProvider] = None
_prices: Optional[PriceProvider] = None
_profiles: Optional[ProfileProvider] = None
_news: Optional[NewsProvider] = None


def register_fundamentals(name: str, cls: type) -> None:
    """Register a fundamentals provider class."""
    _fundamentals_providers[name] = cls


def register_prices(name: str, cls: type) -> None:
    """Register a price provider class."""
    _price_providers[name] = cls


def register_profiles(name: str, cls: type) -> None:
    """Register a profile provider class."""
    _profile_providers[name] = cls


def register_news(name: str, cls: type) -> None:
    """Register a news provider class."""
    _news_providers[name] = cls


def _get_api_key(provider: str) -> str:
    """Look up the API key for a provider from settings."""
    key_map = {
        "fmp": settings.FMP_API_KEY,
        "finnhub": settings.FINNHUB_API_KEY,
        "alpha_vantage": settings.ALPHA_VANTAGE_API_KEY,
        "eodhd": settings.EODHD_API_KEY,
        "polygon": settings.POLYGON_API_KEY,
        "yfinance": "",  # No key needed
        "sec_edgar": "",  # No key needed
    }
    return key_map.get(provider, "")


def initialize_providers() -> None:
    """Initialize active providers from config. Call once at startup."""
    global _fundamentals, _prices, _profiles, _news

    # Import all provider modules to trigger registration
    # Import each module individually to handle missing providers gracefully
    try:
        from app.services.data.providers import fmp  # noqa: F401
    except ImportError:
        pass  # FMP provider not implemented yet

    try:
        from app.services.data.providers import finnhub  # noqa: F401
    except ImportError:
        pass  # Finnhub provider not implemented yet

    try:
        from app.services.data.providers import yfinance_provider  # noqa: F401
    except ImportError:
        pass  # yfinance provider not implemented yet

    # Fundamentals
    fund_name = settings.FUNDAMENTALS_PROVIDER
    if fund_name in _fundamentals_providers:
        _fundamentals = _fundamentals_providers[fund_name](api_key=_get_api_key(fund_name))
        logger.info("Fundamentals provider: %s", fund_name)
    else:
        logger.warning("Unknown fundamentals provider: %s. Available: %s",
                        fund_name, list(_fundamentals_providers.keys()))

    # Prices
    price_name = settings.PRICE_PROVIDER
    if price_name in _price_providers:
        _prices = _price_providers[price_name](api_key=_get_api_key(price_name))
        logger.info("Price provider: %s", price_name)
    else:
        logger.warning("Unknown price provider: %s", price_name)

    # Profiles
    prof_name = settings.PROFILE_PROVIDER
    if prof_name in _profile_providers:
        _profiles = _profile_providers[prof_name](api_key=_get_api_key(prof_name))
        logger.info("Profile provider: %s", prof_name)
    else:
        logger.warning("Unknown profile provider: %s", prof_name)

    # News
    news_name = settings.NEWS_PROVIDER
    if news_name in _news_providers:
        _news = _news_providers[news_name](api_key=_get_api_key(news_name))
        logger.info("News provider: %s", news_name)
    else:
        logger.warning("Unknown news provider: %s", news_name)


def get_fundamentals() -> FundamentalsProvider:
    """Get the active fundamentals provider."""
    if _fundamentals is None:
        raise RuntimeError("Fundamentals provider not initialized. Call initialize_providers() first.")
    return _fundamentals


def get_prices() -> PriceProvider:
    """Get the active price provider."""
    if _prices is None:
        raise RuntimeError("Price provider not initialized. Call initialize_providers() first.")
    return _prices


def get_profiles() -> ProfileProvider:
    """Get the active profile provider."""
    if _profiles is None:
        raise RuntimeError("Profile provider not initialized. Call initialize_providers() first.")
    return _profiles


def get_news() -> NewsProvider:
    """Get the active news provider."""
    if _news is None:
        raise RuntimeError("News provider not initialized. Call initialize_providers() first.")
    return _news
