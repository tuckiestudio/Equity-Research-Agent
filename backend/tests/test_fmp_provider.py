from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from app.core.errors import ProviderError, RateLimitError
from app.schemas.financial import (
    BalanceSheet,
    CashFlow,
    CompanyProfile,
    FinancialRatios,
    IncomeStatement,
    PeriodType,
    PriceBar,
    StockQuote,
    TickerSearchResult,
)
from app.services.data.providers.fmp import FMPProvider


class TestFMPProvider:
    """Test suite for FMP provider."""

    @pytest.fixture
    def provider(self):
        return FMPProvider(api_key="test_key")

    @pytest.fixture
    def mock_http_client(self):
        return AsyncMock()

    async def test_get_income_statement_success(self, provider, mock_http_client):
        """Test income statement retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "date": "2023-09-30",
                "symbol": "AAPL",
                "fillingDate": "2023-11-03",
                "period": "FY",
                "revenue": 383285000000,
                "costOfRevenue": 214137000000,
                "grossProfit": 169148000000,
                "researchAndDevelopmentExpenses": 29915000000,
                "sellingGeneralAndAdministrativeExpenses": 24932000000,
                "operatingIncome": 114301000000,
                "ebitda": 125820000000,
                "netIncome": 96995000000,
                "eps": 6.13,
                "epsdiluted": 6.13,
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            statements = await provider.get_income_statement("AAPL", period="annual")

            assert len(statements) == 1
            assert isinstance(statements[0], IncomeStatement)
            assert statements[0].ticker == "AAPL"
            assert statements[0].period_type == PeriodType.ANNUAL
            assert statements[0].revenue == 383285000000
            assert statements[0].gross_profit == 169148000000
            assert statements[0].source == "fmp"

    async def test_get_balance_sheet_success(self, provider, mock_http_client):
        """Test balance sheet retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "date": "2023-09-30",
                "totalAssets": 352583000000,
                "totalLiabilities": 290437000000,
                "totalStockholdersEquity": 62146000000,
                "totalCurrentAssets": 143666000000,
                "totalCurrentLiabilities": 145322000000,
                "cashAndCashEquivalents": 29965000000,
                "shortTermInvestments": 31590000000,
                "netReceivables": 60915000000,
                "inventory": 6331000000,
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            statements = await provider.get_balance_sheet("AAPL", period="annual")

            assert len(statements) == 1
            assert isinstance(statements[0], BalanceSheet)
            assert statements[0].ticker == "AAPL"
            assert statements[0].period_type == PeriodType.ANNUAL
            assert statements[0].total_assets == 352583000000
            assert statements[0].total_liabilities == 290437000000
            assert statements[0].source == "fmp"

    async def test_get_cash_flow_success(self, provider, mock_http_client):
        """Test cash flow retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "date": "2023-09-30",
                "operatingCashFlow": 110543000000,
                "capitalExpenditure": -10952000000,
                "freeCashFlow": 99591000000,
                "dividendsPaid": -14662000000,
                "commonStockRepurchased": -77500000000,
                "netCashUsedForFinancingActivites": -112804000000,
                "netCashUsedForInvestingActivites": -57634000000,
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            statements = await provider.get_cash_flow("AAPL", period="annual")

            assert len(statements) == 1
            assert isinstance(statements[0], CashFlow)
            assert statements[0].ticker == "AAPL"
            assert statements[0].period_type == PeriodType.ANNUAL
            assert statements[0].operating_cash_flow == 110543000000
            assert statements[0].free_cash_flow == 99591000000
            assert statements[0].source == "fmp"

    async def test_get_financial_ratios_success(self, provider, mock_http_client):
        """Test financial ratios retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "priceEarningsRatio": 25.5,
                "enterpriseValueOverEBITDA": 18.3,
                "priceToBookRatio": 35.2,
                "priceToSalesRatio": 7.1,
                "returnOnEquity": 0.45,
                "returnOnAssets": 0.25,
                "returnOnInvestedCapital": 0.3,
                "grossProfitMargin": 0.45,
                "operatingProfitMargin": 0.30,
                "netProfitMargin": 0.25,
                "debtEquityRatio": 1.2,
                "currentRatio": 1.5,
                "freeCashFlowYield": 0.03,
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            ratios = await provider.get_financial_ratios("AAPL")

            assert isinstance(ratios, FinancialRatios)
            assert ratios.ticker == "AAPL"
            assert ratios.pe_ratio == 25.5
            assert ratios.price_to_book == 35.2
            assert ratios.current_ratio == 1.5
            assert ratios.source == "fmp"

    async def test_get_quote_success(self, provider, mock_http_client):
        """Test quote retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "symbol": "AAPL",
                "price": 178.72,
                "change": 1.23,
                "changesPercentage": 0.6929,
                "dayHigh": 179.61,
                "dayLow": 177.33,
                "open": 178.55,
                "previousClose": 177.49,
                "volume": 54232112,
                "marketCap": 2800000000000,
                "timestamp": 1704067200,
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            quote = await provider.get_quote("AAPL")

            assert isinstance(quote, StockQuote)
            assert quote.ticker == "AAPL"
            assert quote.price == 178.72
            assert quote.change == 1.23
            assert quote.change_percent == 0.6929
            assert quote.high == 179.61
            assert quote.low == 177.33
            assert quote.source == "fmp"

    async def test_get_historical_prices_success(self, provider, mock_http_client):
        """Test historical prices retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "historical": [
                {
                    "date": "2024-01-05",
                    "open": 150.00,
                    "high": 151.50,
                    "low": 149.50,
                    "close": 151.00,
                    "volume": 45000000,
                },
                {
                    "date": "2024-01-04",
                    "open": 149.50,
                    "high": 151.00,
                    "low": 149.00,
                    "close": 150.25,
                    "volume": 50000000,
                },
            ],
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
            assert prices[0].date == date(2024, 1, 4)
            assert prices[0].open == 149.50
            assert prices[0].source == "fmp"

    async def test_get_company_profile_success(self, provider, mock_http_client):
        """Test company profile retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "exchange": "NASDAQ",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "mktCap": 2800000000000,
                "description": "Apple Inc. designs...",
                "website": "https://www.apple.com",
                "ceo": "Tim Cook",
                "country": "US",
                "fullTimeEmployees": "164000",
                "ipoDate": "1980-12-12",
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            profile = await provider.get_company_profile("AAPL")

            assert isinstance(profile, CompanyProfile)
            assert profile.ticker == "AAPL"
            assert profile.company_name == "Apple Inc."
            assert profile.exchange == "NASDAQ"
            assert profile.sector == "Technology"
            assert profile.market_cap == 2800000000000
            assert profile.source == "fmp"

    async def test_search_ticker_success(self, provider, mock_http_client):
        """Test ticker search retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchangeShortName": "NASDAQ",
                "type": "stock",
            },
            {
                "symbol": "APLE",
                "name": "Apple Pie LLC",
                "exchangeShortName": "NYSE",
                "type": "stock",
            },
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            results = await provider.search_ticker("apple")

            assert len(results) == 2
            assert all(isinstance(r, TickerSearchResult) for r in results)
            assert results[0].ticker == "AAPL"
            assert results[0].name == "Apple Inc."

    async def test_empty_response_error(self, provider, mock_http_client):
        """Test error on empty response."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            with pytest.raises(ProviderError) as exc_info:
                await provider.get_income_statement("AAPL")

            assert "No data returned" in str(exc_info.value)

    async def test_rate_limit_error(self, provider, mock_http_client):
        """Test rate limit handling."""
        request = httpx.Request("GET", "https://financialmodelingprep.com/api/v3")
        response = httpx.Response(429, request=request, text="Too Many Requests")
        error = httpx.HTTPStatusError(
            "Rate limit exceeded", request=request, response=response
        )

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.side_effect = error

            with pytest.raises(RateLimitError) as exc_info:
                await provider.get_quote("AAPL")

            assert "fmp" in str(exc_info.value)

    async def test_api_error_handling(self, provider, mock_http_client):
        """Test non-rate limit HTTP errors."""
        request = httpx.Request("GET", "https://financialmodelingprep.com/api/v3")
        response = httpx.Response(500, request=request, text="Server error")
        error = httpx.HTTPStatusError("Server error", request=request, response=response)

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.side_effect = error

            with pytest.raises(ProviderError) as exc_info:
                await provider.get_quote("AAPL")

            assert "HTTP 500" in str(exc_info.value)

    async def test_field_mapping_camelcase(self, provider, mock_http_client):
        """Test camelCase to snake_case mapping."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "date": "2023-09-30",
                "revenue": 383285000000,
                "costOfRevenue": 214137000000,
                "researchAndDevelopmentExpenses": 29915000000,
                "sellingGeneralAndAdministrativeExpenses": 24932000000,
                "epsdiluted": 6.13,
            }
        ]
        mock_response.raise_for_status = Mock()

        with patch.object(provider, "_get_client", return_value=mock_http_client):
            mock_http_client.request.return_value = mock_response

            statements = await provider.get_income_statement("AAPL")

            assert statements[0].cost_of_revenue == 214137000000
            assert statements[0].research_and_development == 29915000000
            assert statements[0].selling_general_admin == 24932000000
            assert statements[0].eps_diluted == 6.13
