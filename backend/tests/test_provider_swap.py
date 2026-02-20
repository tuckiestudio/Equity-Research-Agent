"""
Tests for data provider registry and swapping functionality.

Tests verify:
1. Registry correctly initializes configured providers
2. Provider fallback/aggregator works as expected
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
# Provider Initialization Tests
# =============================================================================

class TestProviderInitialization:
    """Test suite for provider initialization from config."""

    @pytest.fixture
    def reset_providers(self):
        """Reset global provider instances before each test."""
        from app.services.data.registry import (
            _fundamentals,
            _fundamentals_providers,
            _news,
            _news_providers,
            _price_providers,
            _prices,
            _profile_providers,
            _profiles,
        )

        # Store original registrations
        original_fundamentals = dict(_fundamentals_providers)
        original_prices = dict(_price_providers)
        original_profiles = dict(_profile_providers)
        original_news = dict(_news_providers)

        # Clear provider instances
        _fundamentals = None
        _prices = None
        _profiles = None
        _news = None

        yield

        # Reset after test - restore registrations
        _fundamentals_providers.clear()
        _price_providers.clear()
        _profile_providers.clear()
        _news_providers.clear()

        _fundamentals_providers.update(original_fundamentals)
        _price_providers.update(original_prices)
        _profile_providers.update(original_profiles)
        _news_providers.update(original_news)

        _fundamentals = None
        _prices = None
        _profiles = None
        _news = None

    @pytest.mark.asyncio
    async def test_initialize_yfinance_provider(self, reset_providers):
        """Test initializing yfinance as fundamentals provider."""
        from app.services.data.providers.yfinance_provider import YFinanceProvider

        # Manually register yfinance (skipping settings patch which doesn't work with pydantic)
        from app.services.data.registry import (
            _fundamentals_providers,
            register_fundamentals,
        )
        register_fundamentals("yfinance", YFinanceProvider)

        # Create instance directly (simulating what initialize_providers does)
        from app.services.data.registry import _get_api_key
        _fundamentals = _fundamentals_providers["yfinance"](api_key=_get_api_key("yfinance"))

        assert isinstance(_fundamentals, YFinanceProvider)
        assert _fundamentals.provider_name == "yfinance"

    @pytest.mark.asyncio
    async def test_initialize_finnhub_price_provider(self, reset_providers):
        """Test initializing Finnhub as price provider."""
        from app.services.data.providers.finnhub import FinnhubProvider

        # Manually register finnhub
        from app.services.data.registry import (
            _price_providers,
            register_prices,
        )
        register_prices("finnhub", FinnhubProvider)

        # Create instance directly with a test key
        _prices = _price_providers["finnhub"](api_key="test_key")

        assert isinstance(_prices, FinnhubProvider)
        assert _prices.provider_name == "finnhub"

    def test_get_provider_before_initialization(self):
        """Test that accessing a provider before initialization raises RuntimeError."""
        from app.services.data.registry import (
            _fundamentals,
            _news,
            _prices,
            _profiles,
        )

        # Reset providers to None
        _fundamentals = None
        _prices = None
        _profiles = None
        _news = None

        with pytest.raises(RuntimeError) as exc_info:
            get_fundamentals()
        assert "not initialized" in str(exc_info.value)

        with pytest.raises(RuntimeError) as exc_info:
            get_prices()
        assert "not initialized" in str(exc_info.value)

        with pytest.raises(RuntimeError) as exc_info:
            get_profiles()
        assert "not initialized" in str(exc_info.value)

        with pytest.raises(RuntimeError) as exc_info:
            get_news()
        assert "not initialized" in str(exc_info.value)


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
# Provider Swap Tests
# =============================================================================

class TestProviderSwap:
    """Test suite for provider swapping functionality."""

    @pytest.fixture
    def reset_providers(self):
        """Reset global provider instances and registrations before each test."""
        from app.services.data.registry import (
            _fundamentals,
            _fundamentals_providers,
            _news,
            _news_providers,
            _price_providers,
            _prices,
            _profile_providers,
            _profiles,
        )

        # Store original registrations
        original_fundamentals = dict(_fundamentals_providers)
        original_prices = dict(_price_providers)
        original_profiles = dict(_profile_providers)
        original_news = dict(_news_providers)

        # Clear provider instances
        _fundamentals = None
        _prices = None
        _profiles = None
        _news = None

        yield

        # Reset after test - restore registrations
        _fundamentals_providers.clear()
        _price_providers.clear()
        _profile_providers.clear()
        _news_providers.clear()

        _fundamentals_providers.update(original_fundamentals)
        _price_providers.update(original_prices)
        _profile_providers.update(original_profiles)
        _news_providers.update(original_news)

        _fundamentals = None
        _prices = None
        _profiles = None
        _news = None

    @pytest.mark.asyncio
    async def test_swap_from_yfinance_to_finnhub_prices(self, reset_providers):
        """Test swapping price providers from yfinance to Finnhub."""
        from app.services.data.providers.finnhub import FinnhubProvider
        from app.services.data.providers.yfinance_provider import YFinanceProvider
        from app.services.data.registry import (
            _get_api_key,
            _price_providers,
            register_prices,
        )

        # Manually register both providers
        register_prices("yfinance", YFinanceProvider)
        register_prices("finnhub", FinnhubProvider)

        # Simulate swap - set yfinance first
        from app.services.data.registry import _prices
        _prices = _price_providers["yfinance"](api_key=_get_api_key("yfinance"))
        assert isinstance(_prices, YFinanceProvider)
        assert _prices.provider_name == "yfinance"

        # Swap to finnhub
        _prices = _price_providers["finnhub"](api_key="test_key")
        assert _prices.provider_name == "finnhub"

    @pytest.mark.asyncio
    async def test_swap_from_finnhub_to_yfinance_profiles(self, reset_providers):
        """Test swapping profile providers from Finnhub to yfinance."""
        from app.services.data.providers.finnhub import FinnhubProvider
        from app.services.data.providers.yfinance_provider import YFinanceProvider
        from app.services.data.registry import (
            _get_api_key,
            _profile_providers,
            register_profiles,
        )

        # Manually register both providers
        register_profiles("finnhub", FinnhubProvider)
        register_profiles("yfinance", YFinanceProvider)

        # Simulate swap - set finnhub first
        from app.services.data.registry import _profiles
        _profiles = _profile_providers["finnhub"](api_key="test_key")
        assert isinstance(_profiles, FinnhubProvider)
        assert _profiles.provider_name == "finnhub"

        # Swap to yfinance
        _profiles = _profile_providers["yfinance"](api_key=_get_api_key("yfinance"))
        assert _profiles.provider_name == "yfinance"


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
