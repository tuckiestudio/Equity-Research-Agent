"""
Data provider protocols — the interfaces all providers must implement.

Using Python's Protocol (structural subtyping) so providers don't
need to inherit from anything. They just need the right methods.
"""
from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from app.schemas.financial import (
    BalanceSheet,
    CashFlow,
    CompanyProfile,
    FinancialRatios,
    IncomeStatement,
    NewsItem,
    PriceBar,
    StockQuote,
    TickerSearchResult,
)


@runtime_checkable
class FundamentalsProvider(Protocol):
    """Provider for financial statement data."""

    provider_name: str

    async def get_income_statement(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[IncomeStatement]:
        ...

    async def get_balance_sheet(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[BalanceSheet]:
        ...

    async def get_cash_flow(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[CashFlow]:
        ...

    async def get_financial_ratios(
        self, ticker: str
    ) -> FinancialRatios:
        ...


@runtime_checkable
class PriceProvider(Protocol):
    """Provider for price and quote data."""

    provider_name: str

    async def get_quote(self, ticker: str) -> StockQuote:
        ...

    async def get_historical_prices(
        self, ticker: str, start: date, end: date, interval: str = "1d"
    ) -> list[PriceBar]:
        ...


@runtime_checkable
class ProfileProvider(Protocol):
    """Provider for company profile and search."""

    provider_name: str

    async def get_company_profile(self, ticker: str) -> CompanyProfile:
        ...

    async def search_ticker(self, query: str) -> list[TickerSearchResult]:
        ...


@runtime_checkable
class NewsProvider(Protocol):
    """Provider for financial news and sentiment."""

    provider_name: str

    async def get_news(
        self, ticker: str, limit: int = 20
    ) -> list[NewsItem]:
        ...
