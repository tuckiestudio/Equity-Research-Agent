from __future__ import annotations
from typing import Optional, Any
"""
Financial Modeling Prep (FMP) data provider implementation.

https://financialmodelingprep.com/developer/docs/

Implements FundamentalsProvider, PriceProvider, and ProfileProvider protocols.
"""

import asyncio
from datetime import date, datetime
from typing import Any

import httpx

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


class FMPProvider:
    """Financial Modeling Prep API client for financial data."""

    provider_name = "fmp"

    BASE_URL = "https://financialmodelingprep.com/api/v3"
    RATE_LIMIT_CALLS = 300  # 300 calls/minute on starter plan
    RATE_LIMIT_SECONDS = 60

    def __init__(self, api_key: str) -> None:
        """
        Initialize FMP client.

        Args:
            api_key: FMP API key from https://financialmodelingprep.com/
        """
        if not api_key:
            raise ValueError("FMP API key is required")
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(10)  # Concurrent request limit

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                params={"apikey": self._api_key},
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> Any:
        """
        Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments passed to httpx

        Returns:
            Parsed JSON response

        Raises:
            ProviderError: API request failed
            RateLimitError: Rate limit exceeded
        """
        async with self._semaphore:
            client = await self._get_client()

            try:
                response = await client.request(method, endpoint, **kwargs)
                response.raise_for_status()

                data = response.json()

                # FMP returns empty list or error message on failure
                if isinstance(data, list) and len(data) == 0:
                    raise ProviderError("fmp", "No data returned")

                if isinstance(data, dict) and data.get("error"):
                    raise ProviderError("fmp", data["error"])

                return data

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError("fmp")
                raise ProviderError(
                    "fmp", f"HTTP {e.response.status_code}: {e.response.text}"
                )
            except httpx.RequestError as e:
                raise ProviderError("fmp", f"Request failed: {e}")

    # ========================================================================
    # FundamentalsProvider Implementation
    # ========================================================================

    async def get_income_statement(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[IncomeStatement]:
        """
        Get income statement data.

        Endpoint: /income-statement/{ticker}?period={period}&limit={limit}

        Args:
            ticker: Stock symbol (e.g., "AAPL")
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of IncomeStatement objects
        """
        data = await self._request(
            "GET",
            f"/income-statement/{ticker}",
            params={"period": period, "limit": limit},
        )

        if not isinstance(data, list) or len(data) == 0:
            raise ProviderError("fmp", f"No income statement data for {ticker}")

        period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

        statements = []
        for item in data:
            period_date = self._parse_date(item.get("date", item.get("fillingDate")))
            statements.append(
                IncomeStatement(
                    ticker=ticker,
                    period_date=period_date,
                    period_type=period_type,
                    currency=item.get("reportedCurrency", "USD"),
                    revenue=self._to_float(item.get("revenue")),
                    cost_of_revenue=self._to_float(item.get("costOfRevenue")),
                    gross_profit=self._to_float(item.get("grossProfit")),
                    research_and_development=self._to_float(
                        item.get("researchAndDevelopmentExpenses")
                    ),
                    selling_general_admin=self._to_float(
                        item.get("sellingGeneralAndAdministrativeExpenses")
                    ),
                    total_operating_expenses=self._to_float(
                        item.get("operatingExpenses")
                    ),
                    operating_income=self._to_float(item.get("operatingIncome")),
                    ebitda=self._to_float(item.get("ebitda")),
                    depreciation_amortization=self._to_float(
                        item.get("depreciationAndAmortization")
                    ),
                    interest_expense=self._to_float(item.get("interestExpense")),
                    income_before_tax=self._to_float(item.get("incomeBeforeTax")),
                    income_tax_expense=self._to_float(item.get("incomeTaxExpense")),
                    net_income=self._to_float(item.get("netIncome")),
                    eps=self._to_float(item.get("eps")),
                    eps_diluted=self._to_float(item.get("epsdiluted")),
                    shares_outstanding=self._to_float(
                        item.get("weightedAverageShsOut")
                    ),
                    shares_diluted=self._to_float(
                        item.get("weightedAverageShsOutDil")
                    ),
                    source="fmp",
                    fetched_at=datetime.utcnow(),
                )
            )

        return statements

    async def get_balance_sheet(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[BalanceSheet]:
        """
        Get balance sheet data.

        Endpoint: /balance-sheet-statement/{ticker}?period={period}&limit={limit}

        Args:
            ticker: Stock symbol (e.g., "AAPL")
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of BalanceSheet objects
        """
        data = await self._request(
            "GET",
            f"/balance-sheet-statement/{ticker}",
            params={"period": period, "limit": limit},
        )

        if not isinstance(data, list) or len(data) == 0:
            raise ProviderError("fmp", f"No balance sheet data for {ticker}")

        period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

        statements = []
        for item in data:
            period_date = self._parse_date(item.get("date", item.get("fillingDate")))
            statements.append(
                BalanceSheet(
                    ticker=ticker,
                    period_date=period_date,
                    period_type=period_type,
                    currency=item.get("reportedCurrency", "USD"),
                    cash_and_equivalents=self._to_float(
                        item.get("cashAndCashEquivalents")
                    ),
                    short_term_investments=self._to_float(
                        item.get("shortTermInvestments")
                    ),
                    accounts_receivable=self._to_float(
                        item.get("netReceivables")
                    ),
                    inventory=self._to_float(item.get("inventory")),
                    total_current_assets=self._to_float(item.get("totalCurrentAssets")),
                    property_plant_equipment=self._to_float(
                        item.get("propertyPlantEquipmentNet")
                    ),
                    goodwill=self._to_float(item.get("goodwill")),
                    intangible_assets=self._to_float(item.get("intangibleAssets")),
                    total_assets=self._to_float(item.get("totalAssets")),
                    accounts_payable=self._to_float(item.get("accountPayables")),
                    short_term_debt=self._to_float(
                        item.get("shortTermDebt") or item.get("currentDebt")
                    ),
                    total_current_liabilities=self._to_float(
                        item.get("totalCurrentLiabilities")
                    ),
                    long_term_debt=self._to_float(item.get("longTermDebt")),
                    total_liabilities=self._to_float(item.get("totalLiabilities")),
                    total_stockholders_equity=self._to_float(
                        item.get("totalStockholdersEquity")
                    ),
                    shares_outstanding=self._to_float(
                        item.get("commonStockSharesOutstanding")
                    ),
                    source="fmp",
                    fetched_at=datetime.utcnow(),
                )
            )

        return statements

    async def get_cash_flow(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[CashFlow]:
        """
        Get cash flow statement data.

        Endpoint: /cash-flow-statement/{ticker}?period={period}&limit={limit}

        Args:
            ticker: Stock symbol (e.g., "AAPL")
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of CashFlow objects
        """
        data = await self._request(
            "GET",
            f"/cash-flow-statement/{ticker}",
            params={"period": period, "limit": limit},
        )

        if not isinstance(data, list) or len(data) == 0:
            raise ProviderError("fmp", f"No cash flow data for {ticker}")

        period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

        statements = []
        for item in data:
            period_date = self._parse_date(item.get("date", item.get("fillingDate")))

            # Calculate free cash flow if not provided
            operating_cf = self._to_float(item.get("operatingCashFlow"))
            capex = self._to_float(item.get("capitalExpenditure"))
            free_cf = self._to_float(item.get("freeCashFlow"))
            if free_cf is None and operating_cf is not None and capex is not None:
                free_cf = operating_cf - capex

            statements.append(
                CashFlow(
                    ticker=ticker,
                    period_date=period_date,
                    period_type=period_type,
                    currency=item.get("reportedCurrency", "USD"),
                    operating_cash_flow=operating_cf,
                    capital_expenditure=capex,
                    free_cash_flow=free_cf,
                    dividends_paid=self._to_float(item.get("dividendsPaid")),
                    share_repurchase=self._to_float(
                        item.get("commonStockRepurchased")
                    ),
                    financing_cash_flow=self._to_float(
                        item.get("netCashUsedForFinancingActivites")
                    ),
                    investing_cash_flow=self._to_float(
                        item.get("netCashUsedForInvestingActivites")
                    ),
                    source="fmp",
                    fetched_at=datetime.utcnow(),
                )
            )

        return statements

    async def get_financial_ratios(self, ticker: str) -> FinancialRatios:
        """
        Get financial ratios.

        Endpoint: /ratios/{ticker}?limit=1

        Args:
            ticker: Stock symbol (e.g., "AAPL")

        Returns:
            FinancialRatios object
        """
        data = await self._request(
            "GET", f"/ratios/{ticker}", params={"limit": 1}
        )

        if not isinstance(data, list) or len(data) == 0:
            raise ProviderError("fmp", f"No financial ratios data for {ticker}")

        item = data[0]

        return FinancialRatios(
            ticker=ticker,
            pe_ratio=self._to_float(item.get("priceEarningsRatio")),
            ev_to_ebitda=self._to_float(item.get("enterpriseValueOverEBITDA")),
            price_to_book=self._to_float(item.get("priceToBookRatio")),
            price_to_sales=self._to_float(item.get("priceToSalesRatio")),
            return_on_equity=self._to_float(item.get("returnOnEquity")),
            return_on_assets=self._to_float(item.get("returnOnAssets")),
            return_on_invested_capital=self._to_float(
                item.get("returnOnInvestedCapital")
            ),
            gross_margin=self._to_float(item.get("grossProfitMargin")),
            operating_margin=self._to_float(item.get("operatingProfitMargin")),
            net_margin=self._to_float(item.get("netProfitMargin")),
            debt_to_equity=self._to_float(item.get("debtEquityRatio")),
            current_ratio=self._to_float(item.get("currentRatio")),
            fcf_yield=self._to_float(item.get("freeCashFlowYield")),
            dividend_yield=self._to_float(item.get("dividendYield")),
            peg_ratio=self._to_float(item.get("priceEarningsToGrowthRatio")),
            source="fmp",
            fetched_at=datetime.utcnow(),
        )

    # ========================================================================
    # PriceProvider Implementation
    # ========================================================================

    async def get_quote(self, ticker: str) -> StockQuote:
        """
        Get real-time stock quote.

        Endpoint: /quote/{ticker}

        Args:
            ticker: Stock symbol (e.g., "AAPL")

        Returns:
            StockQuote with current price and change
        """
        data = await self._request("GET", f"/quote/{ticker}")

        # FMP returns an array for quote endpoint
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            raise ProviderError("fmp", f"No quote data for {ticker}")

        return StockQuote(
            ticker=ticker,
            price=float(item.get("price", 0)),
            change=self._to_float(item.get("change")),
            change_percent=self._to_float(item.get("changesPercentage")),
            volume=int(item.get("volume", 0)) if item.get("volume") else None,
            market_cap=self._to_float(item.get("marketCap")),
            high=self._to_float(item.get("dayHigh")),
            low=self._to_float(item.get("dayLow")),
            open=self._to_float(item.get("open")),
            previous_close=self._to_float(item.get("previousClose")),
            timestamp=datetime.fromtimestamp(item.get("timestamp", 0))
            if item.get("timestamp")
            else datetime.utcnow(),
            source="fmp",
        )

    async def get_historical_prices(
        self,
        ticker: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> list[PriceBar]:
        """
        Get historical OHLCV price bars.

        Endpoint: /historical-price-full/{ticker}?from={start}&to={end}

        Args:
            ticker: Stock symbol
            start: Start date
            end: End date
            interval: Bar width (1d, 1w, 1m, etc.)
                        Note: FMP free tier primarily supports daily

        Returns:
            List of PriceBar objects
        """
        # FMP uses YYYY-MM-DD format
        from_str = start.isoformat() if start else None
        to_str = end.isoformat() if end else None

        params: dict[str, Any] = {}
        if from_str:
            params["from"] = from_str
        if to_str:
            params["to"] = to_str

        data = await self._request(
            "GET", f"/historical-price-full/{ticker}", params=params
        )

        # FMP returns {"symbol": "AAPL", "historical": [...]}
        historical = data.get("historical", []) if isinstance(data, dict) else []

        if not isinstance(historical, list) or len(historical) == 0:
            return []

        price_bars = []
        for item in historical:
            bar_date = self._parse_date(item.get("date"))
            price_bars.append(
                PriceBar(
                    ticker=ticker,
                    date=bar_date,
                    open=float(item.get("open", 0)),
                    high=float(item.get("high", 0)),
                    low=float(item.get("low", 0)),
                    close=float(item.get("close", 0)),
                    volume=int(item.get("volume", 0)),
                    adjusted_close=self._to_float(item.get("adjClose")),
                    source="fmp",
                )
            )

        # FMP returns most recent first, so reverse to chronological order
        price_bars.reverse()

        return price_bars

    # ========================================================================
    # ProfileProvider Implementation
    # ========================================================================

    async def get_company_profile(self, ticker: str) -> CompanyProfile:
        """
        Get company profile information.

        Endpoint: /profile/{ticker}

        Args:
            ticker: Stock symbol

        Returns:
            CompanyProfile with company details
        """
        data = await self._request("GET", f"/profile/{ticker}")

        # FMP returns an array for profile endpoint
        if isinstance(data, list) and len(data) > 0:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            raise ProviderError("fmp", f"No profile data for {ticker}")

        # Parse IPO date
        ipo_date = None
        if item.get("ipoDate"):
            try:
                ipo_date = datetime.strptime(item["ipoDate"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        # Market cap might be in different fields depending on endpoint
        market_cap = item.get("mktCap") or item.get("marketCap")

        return CompanyProfile(
            ticker=ticker,
            company_name=item.get("companyName", ""),
            exchange=item.get("exchange"),
            sector=item.get("sector"),
            industry=item.get("industry"),
            market_cap=self._to_float(market_cap),
            description=item.get("description"),
            website=item.get("website"),
            ceo=item.get("ceo"),
            country=item.get("country"),
            employees=int(item["fullTimeEmployees"])
            if item.get("fullTimeEmployees")
            else None,
            ipo_date=ipo_date,
            source="fmp",
            fetched_at=datetime.utcnow(),
        )

    async def search_ticker(self, query: str) -> list[TickerSearchResult]:
        """
        Search for tickers by company name or symbol.

        Endpoint: /search?query={query}&limit=10

        Args:
            query: Search query (company name or symbol)

        Returns:
            List of matching ticker results
        """
        data = await self._request(
            "GET", "/search", params={"query": query, "limit": 10}
        )

        # FMP returns [{"symbol": "AAPL", "name": "Apple Inc.", ...}]
        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            if item.get("symbol"):
                results.append(
                    TickerSearchResult(
                        ticker=item.get("symbol", ""),
                        name=item.get("name", ""),
                        exchange=item.get("exchangeShortName"),
                        type=item.get("type"),
                    )
                )

        return results

    # ========================================================================
    # Helper Methods
    # ========================================================================

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> date:
        """Parse date string to date object."""
        if not date_str:
            return date.today()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            try:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").date()
            except (ValueError, TypeError):
                return date.today()

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """Safely convert value to float or None."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# Self-registration
from app.services.data.registry import (
    register_fundamentals,
    register_prices,
    register_profiles,
)

register_fundamentals("fmp", FMPProvider)
register_prices("fmp", FMPProvider)
register_profiles("fmp", FMPProvider)
