"""
Data provider aggregator — fallback chain wrapper.

Tries the primary provider first. On failure, falls back to the secondary.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from app.core.errors import ProviderError, RateLimitError
from app.core.logging import get_logger
from app.schemas.financial import (
    BalanceSheet,
    CashFlow,
    FinancialRatios,
    IncomeStatement,
    PriceBar,
    StockQuote,
)
from app.services.data.protocols import FundamentalsProvider, PriceProvider

logger = get_logger(__name__)


class FundamentalsAggregator:
    """Wraps a primary + fallback fundamentals provider."""

    def __init__(
        self,
        primary: FundamentalsProvider,
        fallback: Optional[FundamentalsProvider] = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    async def get_income_statement(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[IncomeStatement]:
        try:
            return await self.primary.get_income_statement(ticker, period, limit)
        except (ProviderError, RateLimitError, Exception) as e:
            if self.fallback:
                logger.warning(
                    "Primary (%s) failed for %s income statement, falling back to %s: %s",
                    self.primary.provider_name, ticker, self.fallback.provider_name, e,
                )
                return await self.fallback.get_income_statement(ticker, period, limit)
            raise

    async def get_balance_sheet(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[BalanceSheet]:
        try:
            return await self.primary.get_balance_sheet(ticker, period, limit)
        except (ProviderError, RateLimitError, Exception) as e:
            if self.fallback:
                logger.warning(
                    "Primary (%s) failed for %s balance sheet, falling back to %s: %s",
                    self.primary.provider_name, ticker, self.fallback.provider_name, e,
                )
                return await self.fallback.get_balance_sheet(ticker, period, limit)
            raise

    async def get_cash_flow(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[CashFlow]:
        try:
            return await self.primary.get_cash_flow(ticker, period, limit)
        except (ProviderError, RateLimitError, Exception) as e:
            if self.fallback:
                logger.warning(
                    "Primary (%s) failed for %s cash flow, falling back to %s: %s",
                    self.primary.provider_name, ticker, self.fallback.provider_name, e,
                )
                return await self.fallback.get_cash_flow(ticker, period, limit)
            raise

    async def get_financial_ratios(self, ticker: str) -> FinancialRatios:
        try:
            return await self.primary.get_financial_ratios(ticker)
        except (ProviderError, RateLimitError, Exception) as e:
            if self.fallback:
                logger.warning(
                    "Primary (%s) failed for %s ratios, falling back to %s: %s",
                    self.primary.provider_name, ticker, self.fallback.provider_name, e,
                )
                return await self.fallback.get_financial_ratios(ticker)
            raise


class PriceAggregator:
    """Wraps a primary + fallback price provider."""

    def __init__(
        self,
        primary: PriceProvider,
        fallback: Optional[PriceProvider] = None,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    async def get_quote(self, ticker: str) -> StockQuote:
        try:
            return await self.primary.get_quote(ticker)
        except (ProviderError, RateLimitError, Exception) as e:
            if self.fallback:
                logger.warning(
                    "Primary (%s) failed for %s quote, falling back to %s: %s",
                    self.primary.provider_name, ticker, self.fallback.provider_name, e,
                )
                return await self.fallback.get_quote(ticker)
            raise

    async def get_historical_prices(
        self, ticker: str, start: date, end: date, interval: str = "1d"
    ) -> list[PriceBar]:
        try:
            return await self.primary.get_historical_prices(ticker, start, end, interval)
        except (ProviderError, RateLimitError, Exception) as e:
            if self.fallback:
                logger.warning(
                    "Primary (%s) failed for %s history, falling back to %s: %s",
                    self.primary.provider_name, ticker, self.fallback.provider_name, e,
                )
                return await self.fallback.get_historical_prices(ticker, start, end, interval)
            raise
