"""
Tests for data provider implementations.

Tests use mocking to avoid real API calls. Each test verifies:
1. Providers return correct canonical model types
2. Field mappings are correct
3. Error handling works as expected
"""
from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.errors import ProviderError, RateLimitError
from app.schemas.financial import (
    BalanceSheet,
    CashFlow,
    CompanyProfile,
    FinancialRatios,
    IncomeStatement,
    NewsItem,
    PeriodType,
    PriceBar,
    StockQuote,
    TickerSearchResult,
)
from app.services.data.providers.finnhub import FinnhubProvider
from app.services.data.providers.yfinance_provider import YFinanceProvider

# =============================================================================
# Finnhub Provider Tests
# =============================================================================

class TestFinnhubProvider:
    """Test suite for Finnhub provider."""

    @pytest.fixture
    def provider(self):
        """Create a Finnhub provider with test API key."""
        return FinnhubProvider(api_key="test_key")

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        mock = AsyncMock()
        return mock

    async def test_get_quote_success(self, provider, mock_http_client):
        """Test successful quote retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "c": 150.25,  # Current price
            "d": 2.50,   # Change
            "dp": 1.69,  # Percent change
            "h": 151.00, # High
            "l": 149.00, # Low
            "o": 149.50, # Open
            "pc": 147.75, # Previous close
            "t": 1704067200,  # Timestamp
            "v": 50000000,  # Volume
        }
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            quote = await provider.get_quote("AAPL")

            assert isinstance(quote, StockQuote)
            assert quote.ticker == "AAPL"
            assert quote.price == 150.25
            assert quote.change == 2.50
            assert quote.change_percent == 1.69
            assert quote.high == 151.00
            assert quote.low == 149.00
            assert quote.source == "finnhub"

    async def test_get_quote_error(self, provider, mock_http_client):
        """Test quote error handling."""
        mock_response = Mock()
        mock_response.json.return_value = {"s": "error", "errmsg": "Invalid symbol"}

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            with pytest.raises(ProviderError) as exc_info:
                await provider.get_quote("INVALID")

            assert "Invalid symbol" in str(exc_info.value)

    async def test_get_historical_prices_success(self, provider, mock_http_client):
        """Test successful historical prices retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "s": "ok",
            "t": [1704067200, 1704153600],  # Timestamps
            "o": [149.50, 150.00],          # Opens
            "h": [151.00, 151.50],          # Highs
            "l": [149.00, 149.50],          # Lows
            "c": [150.25, 151.00],          # Closes
            "v": [50000000, 45000000],       # Volumes
        }
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            prices = await provider.get_historical_prices(
                "AAPL",
                start=date(2024, 1, 1),
                end=date(2024, 1, 5),
            )

            assert len(prices) == 2
            assert all(isinstance(p, PriceBar) for p in prices)
            assert prices[0].ticker == "AAPL"
            assert prices[0].open == 149.50
            assert prices[0].high == 151.00
            assert prices[0].source == "finnhub"

    async def test_get_historical_prices_no_data(self, provider, mock_http_client):
        """Test historical prices with no data."""
        mock_response = Mock()
        mock_response.json.return_value = {"s": "no_data"}

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            prices = await provider.get_historical_prices(
                "AAPL",
                start=date(2024, 1, 1),
                end=date(2024, 1, 5),
            )

            assert prices == []

    async def test_get_company_profile_success(self, provider, mock_http_client):
        """Test successful company profile retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "name": "Apple Inc.",
            "exchange": "NASDAQ",
            "gics": "Technology",
            "subIndustry": "Consumer Electronics",
            "marketCapitalization": 2500000000000,
            "description": "Apple Inc. designs, manufactures...",
            "weburl": "https://www.apple.com",
            "ceo": "Tim Cook",
            "country": "US",
            "employeeCount": 150000,
            "ipo": "1980-12-12",
        }
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            profile = await provider.get_company_profile("AAPL")

            assert isinstance(profile, CompanyProfile)
            assert profile.ticker == "AAPL"
            assert profile.company_name == "Apple Inc."
            assert profile.exchange == "NASDAQ"
            assert profile.sector == "Technology"
            assert profile.market_cap == 2500000000000
            assert profile.source == "finnhub"

    async def test_search_ticker_success(self, provider, mock_http_client):
        """Test successful ticker search."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": [
                {"symbol": "AAPL", "description": "Apple Inc.", "displaySymbol": "AAPL"},
                {"symbol": "APLE", "description": "Apple Pie LLC", "displaySymbol": "APLE"},
            ]
        }
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            results = await provider.search_ticker("apple")

            assert len(results) == 2
            assert all(isinstance(r, TickerSearchResult) for r in results)
            assert results[0].ticker == "AAPL"
            assert results[0].name == "Apple Inc."

    async def test_get_news_success(self, provider, mock_http_client):
        """Test successful news retrieval."""
        mock_response = Mock()
        # Note: The provider sorts by datetime descending, so the earliest (smallest) timestamp comes last
        # After sorting desc by datetime: 1704067200 comes before 1703980800
        mock_response.json.return_value = [
            {
                "headline": "Apple Reports Strong Earnings",
                "summary": "Apple Inc. reported quarterly earnings...",
                "source": "Reuters",
                "url": "https://example.com/article1",
                "datetime": 1704067200,  # Later timestamp
                "sentiment": 0.5,
            },
            {
                "headline": "Tech Sector Rally",
                "summary": "Technology stocks surged today...",
                "source": "Bloomberg",
                "url": "https://example.com/article2",
                "datetime": 1703980800,  # Earlier timestamp
                "sentiment": -0.2,
            },
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            news = await provider.get_news("AAPL", limit=10)

            assert len(news) == 2
            assert all(isinstance(n, NewsItem) for n in news)
            # After sorting by datetime descending (newest first)
            assert news[0].headline == "Apple Reports Strong Earnings"
            assert news[0].ticker == "AAPL"
            assert news[0].sentiment_label == "positive"
            assert news[1].headline == "Tech Sector Rally"
            assert news[1].sentiment_label == "negative"
            assert news[0].source == "finnhub"

    async def test_rate_limit_error(self, provider, mock_http_client):
        """Test rate limit error handling."""
        import httpx

        mock_response = Mock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("Rate limit exceeded", request=Mock(), response=mock_response)

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.side_effect = error

            with pytest.raises(RateLimitError) as exc_info:
                await provider.get_quote("AAPL")

            assert "finnhub" in str(exc_info.value)


# =============================================================================
# YFinance Provider Tests
# =============================================================================

class TestYFinanceProvider:
    """Test suite for yfinance provider."""

    @pytest.fixture
    def provider(self):
        """Create a yfinance provider."""
        return YFinanceProvider(api_key="")

    async def test_get_quote_success(self, provider):
        """Test successful quote retrieval."""
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

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_info)):
            quote = await provider.get_quote("AAPL")

            assert isinstance(quote, StockQuote)
            assert quote.ticker == "AAPL"
            assert quote.price == 150.25
            assert quote.change == 2.5
            assert quote.change_percent == pytest.approx(1.69, rel=0.1)
            assert quote.source == "yfinance"

    async def test_get_quote_error(self, provider):
        """Test quote error handling."""
        with patch("asyncio.to_thread", new=AsyncMock(return_value=None)):
            with pytest.raises(ProviderError) as exc_info:
                await provider.get_quote("INVALID")

            assert "No quote data" in str(exc_info.value)

    async def test_get_historical_prices_success(self, provider):
        """Test successful historical prices retrieval."""
        import pandas as pd

        mock_df = pd.DataFrame(
            {
                "Open": [149.50, 150.00],
                "High": [151.00, 151.50],
                "Low": [149.00, 149.50],
                "Close": [150.25, 151.00],
                "Volume": [50000000, 45000000],
            },
            index=pd.date_range("2024-01-01", periods=2),
        )

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_df)):
            prices = await provider.get_historical_prices(
                "AAPL",
                start=date(2024, 1, 1),
                end=date(2024, 1, 5),
            )

            assert len(prices) == 2
            assert all(isinstance(p, PriceBar) for p in prices)
            assert prices[0].ticker == "AAPL"
            assert prices[0].open == 149.50
            assert prices[0].high == 151.00
            assert prices[0].source == "yfinance"

    async def test_get_historical_prices_empty(self, provider):
        """Test historical prices with no data."""
        with patch("asyncio.to_thread", new=AsyncMock(return_value=None)):
            prices = await provider.get_historical_prices(
                "AAPL",
                start=date(2024, 1, 1),
                end=date(2024, 1, 5),
            )

            assert prices == []

    async def test_get_company_profile_success(self, provider):
        """Test successful company profile retrieval."""
        mock_info = {
            "longName": "Apple Inc.",
            "exchange": "NMS",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "marketCap": 2500000000000,
            "longBusinessSummary": "Apple Inc. designs, manufactures...",
            "website": "https://www.apple.com",
            "companyOfficers": [{"name": "Tim Cook"}],
            "country": "United States",
            "fullTimeEmployees": 150000,
            "ipoDate": "1980-12-12",
        }

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_info)):
            profile = await provider.get_company_profile("AAPL")

            assert isinstance(profile, CompanyProfile)
            assert profile.ticker == "AAPL"
            assert profile.company_name == "Apple Inc."
            assert profile.sector == "Technology"
            assert profile.industry == "Consumer Electronics"
            assert profile.ceo == "Tim Cook"
            assert profile.source == "yfinance"

    async def test_get_financial_ratios_success(self, provider):
        """Test successful financial ratios retrieval."""
        mock_info = {
            "trailingPE": 25.5,
            "priceToBook": 35.2,
            "returnOnEquity": 0.45,
            "returnOnAssets": 0.25,
            "grossMargins": 0.45,
            "operatingMargins": 0.30,
            "profitMargins": 0.25,
            "currentRatio": 1.5,
            "dividendYield": 0.005,
            "pegRatio": 2.5,
        }

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_info)):
            ratios = await provider.get_financial_ratios("AAPL")

            assert isinstance(ratios, FinancialRatios)
            assert ratios.ticker == "AAPL"
            assert ratios.pe_ratio == 25.5
            assert ratios.price_to_book == 35.2
            assert ratios.return_on_equity == 0.45
            assert ratios.source == "yfinance"

    async def test_get_income_statement_success(self, provider):
        """Test successful income statement retrieval."""
        import pandas as pd

        mock_df = pd.DataFrame(
            {
                pd.Timestamp("2023-09-30"): {
                    "Total Revenue": 383285000000,
                    "Gross Profit": 169148000000,
                    "Net Income": 99803000000,
                    "Basic EPS": 6.16,
                    "Diluted EPS": 6.13,
                },
                pd.Timestamp("2022-09-30"): {
                    "Total Revenue": 365817000000,
                    "Gross Profit": 152836000000,
                    "Net Income": 93956000000,
                    "Basic EPS": 5.73,
                    "Diluted EPS": 5.67,
                },
            }
        )

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_df)):
            statements = await provider.get_income_statement("AAPL", period="annual")

            assert len(statements) == 2
            assert all(isinstance(s, IncomeStatement) for s in statements)
            assert statements[0].ticker == "AAPL"
            assert statements[0].period_type == PeriodType.ANNUAL
            assert statements[0].revenue == 383285000000
            assert statements[0].gross_profit == 169148000000
            assert statements[0].source == "yfinance"

    async def test_get_balance_sheet_success(self, provider):
        """Test successful balance sheet retrieval."""
        import pandas as pd

        mock_df = pd.DataFrame(
            {
                pd.Timestamp("2023-09-30"): {
                    "Total Assets": 352583000000,
                    "Total Liab": 290437000000,
                    "Total Stockholder Equity": 62146000000,
                    "Current Assets": 143666000000,
                    "Current Liabilities": 145322000000,
                },
                pd.Timestamp("2022-09-30"): {
                    "Total Assets": 338516000000,
                    "Total Liab": 283286000000,
                    "Total Stockholder Equity": 55216000000,
                    "Current Assets": 135405000000,
                    "Current Liabilities": 138559000000,
                },
            }
        )

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_df)):
            statements = await provider.get_balance_sheet("AAPL", period="annual")

            assert len(statements) == 2
            assert all(isinstance(s, BalanceSheet) for s in statements)
            assert statements[0].ticker == "AAPL"
            assert statements[0].period_type == PeriodType.ANNUAL
            assert statements[0].total_assets == 352583000000
            assert statements[0].source == "yfinance"

    async def test_get_cash_flow_success(self, provider):
        """Test successful cash flow retrieval."""
        import pandas as pd

        mock_df = pd.DataFrame(
            {
                pd.Timestamp("2023-09-30"): {
                    "Operating Cash Flow": 110543000000,
                    "Capital Expenditure": -10952000000,
                    "Cash Dividends Paid": -14662000000,
                    "Investing Cash Flow": -57634000000,
                    "Financing Cash Flow": -112804000000,
                },
                pd.Timestamp("2022-09-30"): {
                    "Operating Cash Flow": 122151000000,
                    "Capital Expenditure": -10277000000,
                    "Cash Dividends Paid": -14454000000,
                    "Investing Cash Flow": -8475000000,
                    "Financing Cash Flow": -110853000000,
                },
            }
        )

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_df)):
            statements = await provider.get_cash_flow("AAPL", period="annual")

            assert len(statements) == 2
            assert all(isinstance(s, CashFlow) for s in statements)
            assert statements[0].ticker == "AAPL"
            assert statements[0].period_type == PeriodType.ANNUAL
            assert statements[0].operating_cash_flow == 110543000000
            assert statements[0].source == "yfinance"

    async def test_search_ticker_found(self, provider):
        """Test ticker search when found."""
        mock_info = {
            "longName": "Apple Inc.",
            "shortName": "Apple",
            "exchange": "NMS",
        }

        with patch("asyncio.to_thread", new=AsyncMock(return_value=mock_info)):
            results = await provider.search_ticker("AAPL")

            assert len(results) == 1
            assert isinstance(results[0], TickerSearchResult)
            assert results[0].ticker == "AAPL"
            assert results[0].name == "Apple Inc."

    async def test_search_ticker_not_found(self, provider):
        """Test ticker search when not found."""
        with patch("asyncio.to_thread", new=AsyncMock(return_value=None)):
            results = await provider.search_ticker("INVALIDTICKER12345")

            assert results == []
