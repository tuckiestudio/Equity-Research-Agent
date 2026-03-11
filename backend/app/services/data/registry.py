"""
Data provider registry — config-driven provider selection.

Switch providers by changing user settings or env vars.
"""
from __future__ import annotations

from typing import Optional, TYPE_CHECKING
import threading

from app.core.config import settings as global_settings
from app.core.logging import get_logger
from app.services.data.protocols import (
    FundamentalsProvider,
    NewsProvider,
    PriceProvider,
    ProfileProvider,
)

if TYPE_CHECKING:
    from app.models.user_settings import UserSettings

logger = get_logger(__name__)

# Provider implementations will register themselves here
_fundamentals_providers: dict[str, type] = {}
_price_providers: dict[str, type] = {}
_profile_providers: dict[str, type] = {}
_news_providers: dict[str, type] = {}

# Cached provider instances keyed by (provider_name, api_key)
_fundamentals_instances: dict[tuple[str, str], FundamentalsProvider] = {}
_price_instances: dict[tuple[str, str], PriceProvider] = {}
_profile_instances: dict[tuple[str, str], ProfileProvider] = {}
_news_instances: dict[tuple[str, str], NewsProvider] = {}

_lock = threading.Lock()

def register_fundamentals(name: str, cls: type) -> None:
    _fundamentals_providers[name] = cls

def register_prices(name: str, cls: type) -> None:
    _price_providers[name] = cls

def register_profiles(name: str, cls: type) -> None:
    _profile_providers[name] = cls

def register_news(name: str, cls: type) -> None:
    _news_providers[name] = cls

def _get_api_key(provider: str, user_settings: Optional[UserSettings] = None) -> str:
    """Look up the API key for a provider from user settings with fallback to env."""
    # First try user settings
    if user_settings:
        if provider == "fmp" and user_settings.fmp_api_key:
            return user_settings.fmp_api_key
        elif provider == "finnhub" and user_settings.finnhub_api_key:
            return user_settings.finnhub_api_key
        elif provider == "alpha_vantage" and user_settings.alpha_vantage_api_key:
            return user_settings.alpha_vantage_api_key
        elif provider == "eodhd" and user_settings.eodhd_api_key:
            return user_settings.eodhd_api_key
        elif provider == "polygon" and user_settings.polygon_api_key:
            return user_settings.polygon_api_key

    # Fallback to global config
    key_map = {
        "fmp": global_settings.FMP_API_KEY,
        "finnhub": global_settings.FINNHUB_API_KEY,
        "alpha_vantage": global_settings.ALPHA_VANTAGE_API_KEY,
        "eodhd": global_settings.EODHD_API_KEY,
        "polygon": global_settings.POLYGON_API_KEY,
        "yfinance": "",
        "sec_edgar": "",
    }
    return key_map.get(provider, "")

def initialize_providers() -> None:
    """Initialize providers to trigger registration and preload global providers."""
    # Import all provider modules to trigger registration
    try:
        from app.services.data.providers import fmp  # noqa: F401
    except ImportError:
        pass

    try:
        from app.services.data.providers import finnhub  # noqa: F401
    except ImportError:
        pass

    try:
        from app.services.data.providers import yfinance_provider  # noqa: F401
    except ImportError:
        pass

    # Pre-warm global providers (those without UserSettings) so background tasks work
    try:
        get_fundamentals()
    except Exception as e:
        logger.warning(f"Failed to pre-warm global fundamentals provider: {e}")
        
    try:
        get_prices()
    except Exception as e:
        logger.warning(f"Failed to pre-warm global price provider: {e}")
        
    try:
        get_profiles()
    except Exception as e:
        logger.warning(f"Failed to pre-warm global profile provider: {e}")
        
    try:
        get_news()
    except Exception as e:
        logger.warning(f"Failed to pre-warm global news provider: {e}")


def get_fundamentals(user_settings: Optional[UserSettings] = None) -> FundamentalsProvider:
    provider_name = user_settings.fundamentals_provider if user_settings else global_settings.FUNDAMENTALS_PROVIDER
    if provider_name not in _fundamentals_providers:
        raise RuntimeError(f"Unknown fundamentals provider: {provider_name}")

    api_key = _get_api_key(provider_name, user_settings)

    # Fall back to yfinance if provider requires API key but none is provided
    if provider_name != "yfinance" and not api_key:
        logger.warning(f"{provider_name} requires API key but none found, falling back to yfinance")
        provider_name = "yfinance"
        api_key = ""

    cache_key = (provider_name, api_key)

    with _lock:
        if cache_key not in _fundamentals_instances:
            _fundamentals_instances[cache_key] = _fundamentals_providers[provider_name](api_key=api_key)
        return _fundamentals_instances[cache_key]

def get_prices(user_settings: Optional[UserSettings] = None) -> PriceProvider:
    provider_name = user_settings.price_provider if user_settings else global_settings.PRICE_PROVIDER
    if provider_name not in _price_providers:
        raise RuntimeError(f"Unknown price provider: {provider_name}")

    api_key = _get_api_key(provider_name, user_settings)

    # Fall back to yfinance if provider requires API key but none is provided
    if provider_name != "yfinance" and not api_key:
        logger.warning(f"{provider_name} requires API key but none found, falling back to yfinance")
        provider_name = "yfinance"
        api_key = ""

    cache_key = (provider_name, api_key)

    with _lock:
        if cache_key not in _price_instances:
            _price_instances[cache_key] = _price_providers[provider_name](api_key=api_key)
        return _price_instances[cache_key]

def get_profiles(user_settings: Optional[UserSettings] = None) -> ProfileProvider:
    provider_name = user_settings.profile_provider if user_settings else global_settings.PROFILE_PROVIDER
    if provider_name not in _profile_providers:
        raise RuntimeError(f"Unknown profile provider: {provider_name}")

    api_key = _get_api_key(provider_name, user_settings)

    # Fall back to yfinance if provider requires API key but none is provided
    if provider_name != "yfinance" and not api_key:
        logger.warning(f"{provider_name} requires API key but none found, falling back to yfinance")
        provider_name = "yfinance"
        api_key = ""

    cache_key = (provider_name, api_key)

    with _lock:
        if cache_key not in _profile_instances:
            _profile_instances[cache_key] = _profile_providers[provider_name](api_key=api_key)
        return _profile_instances[cache_key]

def get_news(user_settings: Optional[UserSettings] = None) -> NewsProvider:
    provider_name = user_settings.news_provider if user_settings else global_settings.NEWS_PROVIDER
    if provider_name not in _news_providers:
        raise RuntimeError(f"Unknown news provider: {provider_name}")

    api_key = _get_api_key(provider_name, user_settings)

    # Fall back to yfinance if provider requires API key but none is provided
    # yfinance provides free news via RSS feeds (no API key required)
    if provider_name != "yfinance" and not api_key:
        logger.warning(f"{provider_name} requires API key but none found, falling back to yfinance for news")
        provider_name = "yfinance"
        api_key = ""

    cache_key = (provider_name, api_key)

    with _lock:
        if cache_key not in _news_instances:
            _news_instances[cache_key] = _news_providers[provider_name](api_key=api_key)
        return _news_instances[cache_key]
