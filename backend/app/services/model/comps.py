from __future__ import annotations
from typing import Optional

"""Comparable company analysis engine."""

import asyncio
import math
from collections.abc import Callable
from statistics import median

from pydantic import BaseModel

from app.schemas.financial import IncomeStatement
from app.services.data.registry import get_fundamentals, get_profiles


class CompMetric(BaseModel):
    """Comparable company metrics for a single ticker."""

    ticker: str
    company_name: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    price_to_book: Optional[float] = None
    price_to_sales: Optional[float] = None
    eps: Optional[float] = None
    ebitda: Optional[float] = None
    eps_source: Optional[str] = None
    ebitda_source: Optional[str] = None
    is_target: bool = False

    model_config = {"from_attributes": True}


class CompsResult(BaseModel):
    """Comparable company analysis result."""

    target_ticker: str
    target_company_name: Optional[str]
    metrics: list[CompMetric]
    median_pe: Optional[float] = None
    median_ev_to_ebitda: Optional[float] = None
    median_price_to_book: Optional[float] = None
    median_price_to_sales: Optional[float] = None
    implied_value_pe: Optional[float] = None
    implied_value_ev_to_ebitda: Optional[float] = None

    model_config = {"from_attributes": True}


class CompsEngine:
    """Engine for comparable company analysis."""

    async def analyze(
        self,
        target_ticker: str,
        peers: list[str],
        consensus_forecasts: dict[str, dict[str, float]] | None = None,
        llm_forecasts: dict[str, dict[str, float]] | None = None,
    ) -> CompsResult:
        """Analyze a target company against peers using valuation multiples.

        Args:
            target_ticker: Ticker for the target company.
            peers: List of peer tickers.
            consensus_forecasts: Optional consensus EPS/EBITDA forecasts by ticker.
            llm_forecasts: Optional LLM EPS/EBITDA forecasts by ticker.

        Returns:
            CompsResult with metrics and implied values.
        """
        normalized_target = target_ticker.upper()
        peer_tickers = [ticker.upper() for ticker in peers if ticker.upper() != normalized_target]
        tickers = [normalized_target] + peer_tickers

        fundamentals = get_fundamentals()
        profiles = get_profiles()

        ratio_tasks = [fundamentals.get_financial_ratios(ticker) for ticker in tickers]
        profile_tasks = [profiles.get_company_profile(ticker) for ticker in tickers]

        ratios_list, profiles_list = await asyncio.gather(
            asyncio.gather(*ratio_tasks),
            asyncio.gather(*profile_tasks),
        )

        ratios_by_ticker = {ratio.ticker.upper(): ratio for ratio in ratios_list}
        profiles_by_ticker = {profile.ticker.upper(): profile for profile in profiles_list}

        income_statements = await fundamentals.get_income_statement(
            normalized_target, period="annual", limit=1
        )
        latest_income = income_statements[0] if income_statements else None

        target_eps, eps_source = self._select_forecast_value(
            normalized_target,
            "eps",
            consensus_forecasts,
            llm_forecasts,
            latest_income,
            self._get_latest_eps,
        )
        target_ebitda, ebitda_source = self._select_forecast_value(
            normalized_target,
            "ebitda",
            consensus_forecasts,
            llm_forecasts,
            latest_income,
            self._get_latest_ebitda,
        )

        metrics: list[CompMetric] = []
        for ticker in tickers:
            ratios = ratios_by_ticker.get(ticker)
            profile = profiles_by_ticker.get(ticker)
            metric = CompMetric(
                ticker=ticker,
                company_name=profile.company_name if profile else None,
                market_cap=profile.market_cap if profile else None,
                pe_ratio=ratios.pe_ratio if ratios else None,
                ev_to_ebitda=ratios.ev_to_ebitda if ratios else None,
                price_to_book=ratios.price_to_book if ratios else None,
                price_to_sales=ratios.price_to_sales if ratios else None,
                eps=target_eps if ticker == normalized_target else None,
                ebitda=target_ebitda if ticker == normalized_target else None,
                eps_source=eps_source if ticker == normalized_target else None,
                ebitda_source=ebitda_source if ticker == normalized_target else None,
                is_target=ticker == normalized_target,
            )
            metrics.append(metric)

        peer_metrics = [m for m in metrics if not m.is_target]
        median_pe = self._median([m.pe_ratio for m in peer_metrics])
        median_ev_ebitda = self._median([m.ev_to_ebitda for m in peer_metrics])
        median_pb = self._median([m.price_to_book for m in peer_metrics])
        median_ps = self._median([m.price_to_sales for m in peer_metrics])

        implied_value_pe = (
            median_pe * target_eps
            if median_pe is not None and target_eps is not None
            else None
        )
        implied_value_ev_ebitda = (
            median_ev_ebitda * target_ebitda
            if median_ev_ebitda is not None and target_ebitda is not None
            else None
        )

        target_profile = profiles_by_ticker.get(normalized_target)

        return CompsResult(
            target_ticker=normalized_target,
            target_company_name=target_profile.company_name if target_profile else None,
            metrics=metrics,
            median_pe=median_pe,
            median_ev_to_ebitda=median_ev_ebitda,
            median_price_to_book=median_pb,
            median_price_to_sales=median_ps,
            implied_value_pe=implied_value_pe,
            implied_value_ev_to_ebitda=implied_value_ev_ebitda,
        )

    @staticmethod
    def _median(values: list[Optional[float]]) -> Optional[float]:
        """Calculate the median of finite values, ignoring missing entries."""
        filtered = [value for value in values if value is not None and math.isfinite(value)]
        if not filtered:
            return None
        return float(median(filtered))

    @staticmethod
    def _get_latest_eps(latest_income: IncomeStatement) -> Optional[float]:
        """Get EPS from the latest income statement."""
        if latest_income.eps_diluted is not None:
            return latest_income.eps_diluted
        return latest_income.eps

    @staticmethod
    def _get_latest_ebitda(latest_income: IncomeStatement) -> Optional[float]:
        """Get EBITDA from the latest income statement."""
        return latest_income.ebitda

    @staticmethod
    def _select_forecast_value(
        ticker: str,
        field: str,
        consensus_forecasts: dict[str, dict[str, float]] | None,
        llm_forecasts: dict[str, dict[str, float]] | None,
        latest_income: Optional[IncomeStatement],
        fallback: Callable[[IncomeStatement], Optional[float]],
    ) -> tuple[Optional[float], Optional[str]]:
        """Select forecast values with source attribution."""
        if consensus_forecasts:
            value = consensus_forecasts.get(ticker, {}).get(field)
            if value is not None:
                return value, "consensus"

        if llm_forecasts:
            value = llm_forecasts.get(ticker, {}).get(field)
            if value is not None:
                return value, "llm"

        if latest_income is not None:
            value = fallback(latest_income)
            if value is not None:
                return value, "latest_income"

        return None, None
