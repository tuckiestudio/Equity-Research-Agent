"""
yfinance data provider implementation.

https://github.com/ranaroussi/yfinance

Implements FundamentalsProvider, PriceProvider, and ProfileProvider protocols.
Uses asyncio.to_thread to wrap synchronous yfinance calls.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Optional

from app.core.errors import ProviderError
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


class YFinanceProvider:
    """
    yfinance data provider (free, no API key required).

    Uses Yahoo Finance via the yfinance library.
    All calls are wrapped in asyncio.to_thread for async compatibility.
    """

    provider_name = "yfinance"

    def __init__(self, api_key: str = "") -> None:
        """
        Initialize yfinance provider.

        Note: yfinance doesn't require an API key. The api_key parameter
        is kept for interface compatibility.

        Args:
            api_key: Ignored (kept for protocol compatibility)
        """
        self._ticker_cache: dict[str, object] = {}

    def _get_ticker(self, symbol: str):
        """Get or create a yfinance Ticker object (cached)."""
        if symbol not in self._ticker_cache:
            import yfinance as yf

            self._ticker_cache[symbol] = yf.Ticker(symbol)
        return self._ticker_cache[symbol]

    def _run_sync(self, func, *args, **kwargs):
        """
        Run a synchronous function in a thread pool.

        Args:
            func: Synchronous function to run
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        return asyncio.to_thread(func, *args, **kwargs)

    # ========================================================================
    # FundamentalsProvider Implementation
    # ========================================================================

    async def get_income_statement(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[IncomeStatement]:
        """
        Get income statement data.

        Args:
            ticker: Stock symbol
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of IncomeStatement objects
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            if period == "annual":
                df = ticker_obj.get_income_stmt(as_dict=False)
            else:
                df = ticker_obj.get_income_stmt(freq="quarterly", as_dict=False)
            return df

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        statements = []
        for col in df.columns[:limit]:
            period_date = col.to_pydatetime().date()
            period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

            # Extract values (yfinance uses specific index names)
            def get_value(index_name: str) -> Optional[float]:
                try:
                    val = df.loc[index_name, col]
                    return float(val) if val is not None and not (isinstance(val, float) and val != val) else None
                except (KeyError, ValueError):
                    return None

            # Map yfinance fields to our canonical model
            # Note: yfinance field names vary, using common ones
            stmt = IncomeStatement(
                ticker=ticker,
                period_date=period_date,
                period_type=period_type,
                currency="USD",  # yfinance doesn't always specify, assume USD for US stocks
                revenue=get_value("Total Revenue"),
                cost_of_revenue=get_value("Cost Of Revenue"),
                gross_profit=get_value("Gross Profit"),
                research_and_development=get_value("Research And Development"),
                selling_general_admin=get_value("Selling General Administrative"),
                total_operating_expenses=get_value("Total Operating Expenses"),
                operating_income=get_value("Operating Income"),
                ebitda=get_value("Ebitda"),
                depreciation_amortization=get_value("Reconciled Depreciation"),
                interest_expense=get_value("Interest Expense"),
                income_before_tax=get_value("Income Before Tax"),
                income_tax_expense=get_value("Income Tax Expense"),
                net_income=get_value("Net Income"),
                eps=get_value("Basic EPS"),
                eps_diluted=get_value("Diluted EPS"),
                shares_outstanding=get_value("Basic Average Shares"),
                shares_diluted=get_value("Diluted Average Shares"),
                source="yfinance",
            )
            statements.append(stmt)

        return statements

    async def get_balance_sheet(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[BalanceSheet]:
        """
        Get balance sheet data.

        Args:
            ticker: Stock symbol
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of BalanceSheet objects
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            if period == "annual":
                df = ticker_obj.get_balance_sheet(as_dict=False)
            else:
                df = ticker_obj.get_balance_sheet(freq="quarterly", as_dict=False)
            return df

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        statements = []
        for col in df.columns[:limit]:
            period_date = col.to_pydatetime().date()
            period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

            def get_value(index_name: str) -> Optional[float]:
                try:
                    val = df.loc[index_name, col]
                    return float(val) if val is not None and not (isinstance(val, float) and val != val) else None
                except (KeyError, ValueError):
                    return None

            stmt = BalanceSheet(
                ticker=ticker,
                period_date=period_date,
                period_type=period_type,
                currency="USD",
                cash_and_equivalents=get_value("Cash And Cash Equivalents"),
                short_term_investments=get_value("Short Term Investments"),
                accounts_receivable=get_value("Net Receivables"),
                inventory=get_value("Inventory"),
                total_current_assets=get_value("Current Assets"),
                property_plant_equipment=get_value("Property Plant Equipment"),
                goodwill=get_value("Good Will"),
                intangible_assets=get_value("Intangible Assets"),
                total_assets=get_value("Total Assets"),
                accounts_payable=get_value("Accounts Payable"),
                short_term_debt=get_value("Short Term Debt"),
                total_current_liabilities=get_value("Current Liabilities"),
                long_term_debt=get_value("Long Term Debt"),
                total_liabilities=get_value("Total Liab"),
                total_stockholders_equity=get_value("Total Stockholder Equity"),
                shares_outstanding=get_value("Common Stock Shares Outstanding"),
                source="yfinance",
            )
            statements.append(stmt)

        return statements

    async def get_cash_flow(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[CashFlow]:
        """
        Get cash flow statement data.

        Args:
            ticker: Stock symbol
            period: "annual" or "quarterly"
            limit: Number of periods to return

        Returns:
            List of CashFlow objects
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            if period == "annual":
                df = ticker_obj.get_cashflow(as_dict=False)
            else:
                df = ticker_obj.get_cashflow(freq="quarterly", as_dict=False)
            return df

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        statements = []
        for col in df.columns[:limit]:
            period_date = col.to_pydatetime().date()
            period_type = PeriodType.ANNUAL if period == "annual" else PeriodType.QUARTERLY

            def get_value(index_name: str) -> Optional[float]:
                try:
                    val = df.loc[index_name, col]
                    return float(val) if val is not None and not (isinstance(val, float) and val != val) else None
                except (KeyError, ValueError):
                    return None

            stmt = CashFlow(
                ticker=ticker,
                period_date=period_date,
                period_type=period_type,
                currency="USD",
                operating_cash_flow=get_value("Operating Cash Flow"),
                capital_expenditure=get_value("Capital Expenditure"),
                free_cash_flow=None,  # yfinance doesn't provide this directly, could calculate
                dividends_paid=get_value("Cash Dividends Paid"),
                share_repurchase=None,  # Often part of "Repurchase Of Stock"
                financing_cash_flow=get_value("Financing Cash Flow"),
                investing_cash_flow=get_value("Investing Cash Flow"),
                source="yfinance",
            )
            statements.append(stmt)

        return statements

    async def get_financial_ratios(self, ticker: str) -> FinancialRatios:
        """
        Get financial ratios and valuation metrics.

        Args:
            ticker: Stock symbol

        Returns:
            FinancialRatios object
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch_info():
            return ticker_obj.info

        info = await self._run_sync(_fetch_info)

        if not info:
            raise ProviderError("yfinance", f"No data available for {ticker}")

        # Map yfinance info fields to our canonical model
        return FinancialRatios(
            ticker=ticker,
            pe_ratio=info.get("trailingPE"),
            ev_to_ebitda=info.get("enterpriseToEbitda"),
            price_to_book=info.get("priceToBook"),
            price_to_sales=info.get("priceToSalesTrailing12Months"),
            return_on_equity=info.get("returnOnEquity"),
            return_on_assets=info.get("returnOnAssets"),
            return_on_invested_capital=info.get("returnOnCapital"),
            gross_margin=info.get("profitMargins", {}).get("gross") if isinstance(info.get("profitMargins"), dict) else info.get("grossMargins"),
            operating_margin=info.get("profitMargins", {}).get("operating") if isinstance(info.get("profitMargins"), dict) else info.get("operatingMargins"),
            net_margin=info.get("profitMargins", {}).get("net") if isinstance(info.get("profitMargins"), dict) else info.get("profitMargins"),
            debt_to_equity=None,  # yfinance has various debt metrics, need to calculate
            current_ratio=info.get("currentRatio"),
            fcf_yield=None,  # Need to calculate from FCF and market cap
            dividend_yield=info.get("dividendYield"),
            peg_ratio=info.get("pegRatio"),
            source="yfinance",
        )

    # ========================================================================
    # PriceProvider Implementation
    # ========================================================================

    async def get_quote(self, ticker: str) -> StockQuote:
        """
        Get real-time stock quote.

        Args:
            ticker: Stock symbol

        Returns:
            StockQuote with current price and change
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            return ticker_obj.info

        info = await self._run_sync(_fetch)

        if not info or "regularMarketPrice" not in info:
            raise ProviderError("yfinance", f"No quote data for {ticker}")

        current_price = info["regularMarketPrice"]
        previous_close = info.get("previousClose")
        current_price_float = float(current_price) if current_price is not None else 0.0

        change = None
        change_percent = None
        if previous_close is not None and previous_close > 0:
            change = current_price_float - float(previous_close)
            change_percent = (change / float(previous_close)) * 100

        return StockQuote(
            ticker=ticker,
            price=current_price_float,
            change=change,
            change_percent=change_percent,
            volume=info.get("regularMarketVolume"),
            market_cap=info.get("marketCap"),
            high=info.get("regularMarketDayHigh"),
            low=info.get("regularMarketDayLow"),
            open=info.get("regularMarketOpen"),
            previous_close=previous_close,
            timestamp=datetime.fromtimestamp(info.get("regularMarketTime", 0)) if info.get("regularMarketTime") else datetime.utcnow(),
            source="yfinance",
        )

    async def get_historical_prices(
        self, ticker: str, start: date, end: date, interval: str = "1d"
    ) -> list[PriceBar]:
        """
        Get historical OHLCV price bars.

        Args:
            ticker: Stock symbol
            start: Start date
            end: End date
            interval: Bar width (1d, 1w, 1h, etc.)

        Returns:
            List of PriceBar objects
        """
        ticker_obj = self._get_ticker(ticker)

        # yfinance interval mapping
        interval_map = {
            "1d": "1d",
            "1w": "1wk",
            "1M": "1mo",
            "1h": "1h",
            "15m": "15m",
            "5m": "5m",
            "1m": "1m",
        }
        yf_interval = interval_map.get(interval, "1d")

        def _fetch():
            return ticker_obj.history(
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval=yf_interval,
            )

        df = await self._run_sync(_fetch)

        if df is None or df.empty:
            return []

        price_bars = []
        for idx, row in df.iterrows():
            # Handle both DatetimeIndex and regular index
            if hasattr(idx, "date"):
                bar_date = idx.date()
            else:
                bar_date = idx

            price_bars.append(
                PriceBar(
                    ticker=ticker,
                    date=bar_date,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                    adjusted_close=float(row.get("Close", 0)),  # yfinance doesn't always provide adj close
                    source="yfinance",
                )
            )

        return price_bars

    # ========================================================================
    # ProfileProvider Implementation
    # ========================================================================

    async def get_company_profile(self, ticker: str) -> CompanyProfile:
        """
        Get company profile information.

        Args:
            ticker: Stock symbol

        Returns:
            CompanyProfile with company details
        """
        ticker_obj = self._get_ticker(ticker)

        def _fetch():
            return ticker_obj.info

        info = await self._run_sync(_fetch)

        if not info:
            raise ProviderError("yfinance", f"No profile data for {ticker}")

        # Parse IPO date if present
        ipo_date = None
        if info.get("ipoDate"):
            try:
                ipo_date = datetime.strptime(info["ipoDate"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        return CompanyProfile(
            ticker=ticker,
            company_name=info.get("longName") or info.get("shortName", ""),
            exchange=info.get("exchange"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            description=info.get("longBusinessSummary"),
            website=info.get("website"),
            ceo=info.get("companyOfficers", [{}])[0].get("name") if info.get("companyOfficers") else None,
            country=info.get("country"),
            employees=info.get("fullTimeEmployees"),
            ipo_date=ipo_date,
            source="yfinance",
        )

    async def search_ticker(self, query: str) -> list[TickerSearchResult]:
        """
        Search for tickers by company name or symbol.

        Note: yfinance doesn't have a direct search API. This implementation
        is a placeholder that returns a result if the query matches exactly.
        For a production system, consider using another provider for search.

        Args:
            query: Search query (company name or symbol)

        Returns:
            List of matching ticker results
        """
        # yfinance doesn't provide search functionality
        # This is a minimal implementation that tries to get info for the query
        try:
            ticker_obj = self._get_ticker(query)

            def _fetch():
                return ticker_obj.info

            info = await self._run_sync(_fetch)

            if info and (info.get("longName") or info.get("shortName")):
                return [
                    TickerSearchResult(
                        ticker=query.upper(),
                        name=info.get("longName") or info.get("shortName", ""),
                        exchange=info.get("exchange"),
                        type="stock",
                    )
                ]
        except Exception:
            pass

        return []


# Self-registration
from app.services.data.registry import (
    register_fundamentals,
    register_prices,
    register_profiles,
)

register_fundamentals("yfinance", YFinanceProvider)
register_prices("yfinance", YFinanceProvider)
register_profiles("yfinance", YFinanceProvider)
