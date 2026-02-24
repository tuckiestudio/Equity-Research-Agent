"""
Tests for data provider registry and swapping functionality.

Tests verify:
1. Registry correctly initializes configured providers
2. Provider caching works correctly with different API keys
3. Invalid provider configurations are handled gracefully

Note: Provider classes are imported within tests rather than at module level
to avoid premature self-registration with default settings.
"""
from __future__ import annotations

from unittest import mock

import pytest

from app.services.data.protocols import (
    FundamentalsProvider,
    NewsProvider,
    PriceProvider,
    ProfileProvider,
)
from app.services.data.registry import (
    get_fundamentals,
    get_news,
    get_prices,
    get_profiles,
    register_fundamentals,
    register_news,
    register_prices,
    register_profiles,
)

# =============================================================================
# Registry Tests
# =============================================================================


class TestProviderRegistry:
    """Test suite for provider registry functionality."""

    def test_register_fundamentals_provider(self):
        """Test registering a fundamentals provider."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider
        from app.services.data.registry import _fundamentals_providers

        # Store original state
        original = dict(_fundamentals_providers)

        try:
            _fundamentals_providers.clear()
            register_fundamentals("test_provider", YFinanceProvider)

            assert "test_provider" in _fundamentals_providers
            assert _fundamentals_providers["test_provider"] == YFinanceProvider
        finally:
            _fundamentals_providers.clear()
            _fundamentals_providers.update(original)

    def test_register_prices_provider(self):
        """Test registering a price provider."""
        from app.services.data.providers.finnhub import FinnhubProvider
        from app.services.data.registry import _price_providers

        original = dict(_price_providers)

        try:
            _price_providers.clear()
            register_prices("test_provider", FinnhubProvider)

            assert "test_provider" in _price_providers
            assert _price_providers["test_provider"] == FinnhubProvider
        finally:
            _price_providers.clear()
            _price_providers.update(original)

    def test_register_profiles_provider(self):
        """Test registering a profile provider."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider
        from app.services.data.registry import _profile_providers

        original = dict(_profile_providers)

        try:
            _profile_providers.clear()
            register_profiles("test_provider", YFinanceProvider)

            assert "test_provider" in _profile_providers
            assert _profile_providers["test_provider"] == YFinanceProvider
        finally:
            _profile_providers.clear()
            _profile_providers.update(original)

    def test_register_news_provider(self):
        """Test registering a news provider."""
        from app.services.data.providers.finnhub import FinnhubProvider
        from app.services.data.registry import _news_providers

        original = dict(_news_providers)

        try:
            _news_providers.clear()
            register_news("test_provider", FinnhubProvider)

            assert "test_provider" in _news_providers
            assert _news_providers["test_provider"] == FinnhubProvider
        finally:
            _news_providers.clear()
            _news_providers.update(original)


# =============================================================================
# Provider Caching Tests
# =============================================================================


class TestProviderCaching:
    """Test suite for provider instance caching."""

    @pytest.fixture
    def reset_provider_instances(self):
        """Reset provider instance caches before each test."""
        from app.services.data.registry import (
            _fundamentals_instances,
            _news_instances,
            _price_instances,
            _profile_instances,
        )

        # Store original state
        original_fundamentals = dict(_fundamentals_instances)
        original_prices = dict(_price_instances)
        original_profiles = dict(_profile_instances)
        original_news = dict(_news_instances)

        try:
            # Clear instances
            _fundamentals_instances.clear()
            _price_instances.clear()
            _profile_instances.clear()
            _news_instances.clear()

            yield
        finally:
            # Restore original state
            _fundamentals_instances.clear()
            _price_instances.clear()
            _profile_instances.clear()
            _news_instances.clear()

            _fundamentals_instances.update(original_fundamentals)
            _price_instances.update(original_prices)
            _profile_instances.update(original_profiles)
            _news_instances.update(original_news)

    def test_get_fundamentals_cached(self, reset_provider_instances, monkeypatch):
        """Test that get_fundamentals returns cached instance."""
        from app.services.data.registry import _fundamentals_instances, _fundamentals_providers
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        # Register yfinance and set as default
        if "yfinance" not in _fundamentals_providers:
            register_fundamentals("yfinance", YFinanceProvider)

        monkeypatch.setattr("app.services.data.registry.global_settings.FUNDAMENTALS_PROVIDER", "yfinance")

        # Clear any existing yfinance instances
        keys_to_remove = [k for k in _fundamentals_instances if k[0] == "yfinance"]
        for key in keys_to_remove:
            del _fundamentals_instances[key]

        # First call creates instance
        provider1 = get_fundamentals()

        # Second call returns same instance
        provider2 = get_fundamentals()

        assert provider1 is provider2

    def test_get_prices_cached(self, reset_provider_instances, monkeypatch):
        """Test that get_prices returns cached instance."""
        from app.services.data.registry import _price_instances, _price_providers
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        # Register yfinance and set as default
        if "yfinance" not in _price_providers:
            register_prices("yfinance", YFinanceProvider)

        monkeypatch.setattr("app.services.data.registry.global_settings.PRICE_PROVIDER", "yfinance")

        # Clear any existing yfinance instances
        keys_to_remove = [k for k in _price_instances if k[0] == "yfinance"]
        for key in keys_to_remove:
            del _price_instances[key]

        provider1 = get_prices()
        provider2 = get_prices()

        assert provider1 is provider2

    def test_get_profiles_cached(self, reset_provider_instances, monkeypatch):
        """Test that get_profiles returns cached instance."""
        from app.services.data.registry import _profile_instances, _profile_providers
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        # Register yfinance and set as default
        if "yfinance" not in _profile_providers:
            register_profiles("yfinance", YFinanceProvider)

        monkeypatch.setattr("app.services.data.registry.global_settings.PROFILE_PROVIDER", "yfinance")

        # Clear any existing yfinance instances
        keys_to_remove = [k for k in _profile_instances if k[0] == "yfinance"]
        for key in keys_to_remove:
            del _profile_instances[key]

        provider1 = get_profiles()
        provider2 = get_profiles()

        assert provider1 is provider2

    def test_get_news_cached(self, reset_provider_instances, monkeypatch):
        """Test that get_news returns cached instance."""
        from app.services.data.registry import _news_instances, _news_providers
        from app.services.data.providers.finnhub import FinnhubProvider

        # Register finnhub and set as default with a test key
        if "finnhub" not in _news_providers:
            register_news("finnhub", FinnhubProvider)

        monkeypatch.setattr("app.services.data.registry.global_settings.NEWS_PROVIDER", "finnhub")
        monkeypatch.setattr("app.services.data.registry.global_settings.FINNHUB_API_KEY", "test_key")

        # Clear any existing finnhub instances
        keys_to_remove = [k for k in _news_instances if k[0] == "finnhub"]
        for key in keys_to_remove:
            del _news_instances[key]

        provider1 = get_news()
        provider2 = get_news()

        assert provider1 is provider2


# =============================================================================
# Provider Protocol Conformance Tests
# =============================================================================


class TestProviderProtocols:
    """Test that providers correctly implement their protocols."""

    @pytest.mark.asyncio
    async def test_finnhub_price_provider_conformance(self):
        """Test that FinnhubProvider implements PriceProvider protocol."""
        from app.services.data.providers.finnhub import FinnhubProvider

        provider = FinnhubProvider(api_key="test_key")

        assert isinstance(provider, PriceProvider)
        assert hasattr(provider, "get_quote")
        assert hasattr(provider, "get_historical_prices")

    @pytest.mark.asyncio
    async def test_finnhub_profile_provider_conformance(self):
        """Test that FinnhubProvider implements ProfileProvider protocol."""
        from app.services.data.providers.finnhub import FinnhubProvider

        provider = FinnhubProvider(api_key="test_key")

        assert isinstance(provider, ProfileProvider)
        assert hasattr(provider, "get_company_profile")
        assert hasattr(provider, "search_ticker")

    @pytest.mark.asyncio
    async def test_finnhub_news_provider_conformance(self):
        """Test that FinnhubProvider implements NewsProvider protocol."""
        from app.services.data.providers.finnhub import FinnhubProvider

        provider = FinnhubProvider(api_key="test_key")

        assert isinstance(provider, NewsProvider)
        assert hasattr(provider, "get_news")

    @pytest.mark.asyncio
    async def test_yfinance_fundamentals_provider_conformance(self):
        """Test that YFinanceProvider implements FundamentalsProvider protocol."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        provider = YFinanceProvider(api_key="")

        assert isinstance(provider, FundamentalsProvider)
        assert hasattr(provider, "get_income_statement")
        assert hasattr(provider, "get_balance_sheet")
        assert hasattr(provider, "get_cash_flow")
        assert hasattr(provider, "get_financial_ratios")

    @pytest.mark.asyncio
    async def test_yfinance_price_provider_conformance(self):
        """Test that YFinanceProvider implements PriceProvider protocol."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        provider = YFinanceProvider(api_key="")

        assert isinstance(provider, PriceProvider)
        assert hasattr(provider, "get_quote")
        assert hasattr(provider, "get_historical_prices")

    @pytest.mark.asyncio
    async def test_yfinance_profile_provider_conformance(self):
        """Test that YFinanceProvider implements ProfileProvider protocol."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        provider = YFinanceProvider(api_key="")

        assert isinstance(provider, ProfileProvider)
        assert hasattr(provider, "get_company_profile")
        assert hasattr(provider, "search_ticker")


# =============================================================================
# Provider Error Handling Tests
# =============================================================================


class TestProviderErrorHandling:
    """Test suite for provider error handling."""

    @pytest.mark.asyncio
    async def test_finnhub_missing_api_key(self):
        """Test that FinnhubProvider raises ValueError without API key."""
        from app.services.data.providers.finnhub import FinnhubProvider

        # Empty string should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            FinnhubProvider(api_key="")
        assert "API key is required" in str(exc_info.value)

        # Also test with None
        with pytest.raises(ValueError) as exc_info:
            FinnhubProvider(api_key=None)  # type: ignore[arg-type]
        assert "API key is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_yfinance_provider_without_api_key(self):
        """Test that YFinanceProvider works without API key."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        # Should not raise an error
        provider = YFinanceProvider(api_key="")
        assert provider.provider_name == "yfinance"

    def test_unknown_provider_raises_runtimeerror(self):
        """Test that unknown provider raises RuntimeError."""
        from unittest.mock import patch

        # Patch settings to return unknown provider
        with patch("app.services.data.registry.global_settings") as mock_settings:
            mock_settings.FUNDAMENTALS_PROVIDER = "unknown_provider"
            mock_settings.FMP_API_KEY = ""

            with pytest.raises(RuntimeError) as exc_info:
                get_fundamentals()
            assert "Unknown fundamentals provider" in str(exc_info.value)


# =============================================================================
# Integration Tests (with mocked providers)
# =============================================================================


class TestProviderIntegration:
    """Integration tests with mocked provider responses."""

    @pytest.mark.asyncio
    async def test_yfinance_get_quote_mocked(self):
        """Test yfinance quote with mocked response."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        provider = YFinanceProvider(api_key="")

        mock_info = {
            "regularMarketPrice": 150.25,
            "previousClose": 147.75,
            "regularMarketDayHigh": 151.00,
            "regularMarketDayLow": 149.00,
            "regularMarketOpen": 149.50,
            "regularMarketVolume": 50000000,
            "marketCap": 2500000000000,
            "regularMarketTime": 1704067200,
        }

        with mock.patch("asyncio.to_thread", new_callable=lambda: mock.AsyncMock(return_value=mock_info)):
            quote = await provider.get_quote("AAPL")

            assert quote.ticker == "AAPL"
            assert quote.price == 150.25
            assert quote.source == "yfinance"

    @pytest.mark.asyncio
    async def test_finnhub_get_quote_mocked(self):
        """Test Finnhub quote with mocked response."""
        from app.services.data.providers.finnhub import FinnhubProvider

        provider = FinnhubProvider(api_key="test_key")

        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "c": 150.25,
            "d": 2.50,
            "dp": 1.69,
            "h": 151.00,
            "l": 149.00,
            "o": 149.50,
            "pc": 147.75,
            "t": 1704067200,
            "v": 50000000,
        }
        mock_response.raise_for_status = mock.Mock()

        with mock.patch.object(provider, "_get_client", new=mock.AsyncMock(return_value=mock.AsyncMock())):
            client = await provider._get_client()
            client.request = mock.AsyncMock(return_value=mock_response)

            quote = await provider.get_quote("AAPL")

            assert quote.ticker == "AAPL"
            assert quote.price == 150.25
            assert quote.source == "finnhub"


# =============================================================================
# Provider Selection Tests
# =============================================================================


class TestProviderSelection:
    """Test provider selection based on settings."""

    def test_fundamentals_provider_selection_with_yfinance(self):
        """Test that yfinance fundamentals provider works without API key."""
        from unittest.mock import patch

        from app.services.data.providers.yfinance_provider import YFinanceProvider
        from app.services.data.registry import _fundamentals_providers

        # Store original
        original = dict(_fundamentals_providers)

        try:
            # Register yfinance and patch settings to use it
            _fundamentals_providers.clear()
            register_fundamentals("yfinance", YFinanceProvider)

            with patch("app.services.data.registry.global_settings") as mock_settings:
                mock_settings.FUNDAMENTALS_PROVIDER = "yfinance"
                mock_settings.FMP_API_KEY = ""

                provider = get_fundamentals()
                assert provider is not None
                assert provider.provider_name == "yfinance"
        finally:
            _fundamentals_providers.clear()
            _fundamentals_providers.update(original)

    def test_price_provider_selection_with_yfinance(self):
        """Test that yfinance price provider works without API key."""
        from unittest.mock import patch

        from app.services.data.providers.yfinance_provider import YFinanceProvider
        from app.services.data.registry import _price_providers

        # Store original
        original = dict(_price_providers)

        try:
            _price_providers.clear()
            register_prices("yfinance", YFinanceProvider)

            with patch("app.services.data.registry.global_settings") as mock_settings:
                mock_settings.PRICE_PROVIDER = "yfinance"

                provider = get_prices()
                assert provider is not None
                assert provider.provider_name == "yfinance"
        finally:
            _price_providers.clear()
            _price_providers.update(original)

    def test_profile_provider_selection_with_yfinance(self):
        """Test that yfinance profile provider works without API key."""
        from unittest.mock import patch

        from app.services.data.providers.yfinance_provider import YFinanceProvider
        from app.services.data.registry import _profile_providers

        # Store original
        original = dict(_profile_providers)

        try:
            _profile_providers.clear()
            register_profiles("yfinance", YFinanceProvider)

            with patch("app.services.data.registry.global_settings") as mock_settings:
                mock_settings.PROFILE_PROVIDER = "yfinance"

                provider = get_profiles()
                assert provider is not None
                assert provider.provider_name == "yfinance"
        finally:
            _profile_providers.clear()
            _profile_providers.update(original)
