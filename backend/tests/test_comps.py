"""Tests for comparable company analysis engine."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.financial import CompanyProfile, FinancialRatios, IncomeStatement, PeriodType
from app.services.model import comps as comps_module
from app.services.model.comps import CompsEngine


class DummyFundamentals:
    """Dummy fundamentals provider for comps tests."""

    def __init__(
        self,
        ratios_by_ticker: dict[str, FinancialRatios],
        incomes_by_ticker: dict[str, list[IncomeStatement]],
    ) -> None:
        self._ratios = ratios_by_ticker
        self._incomes = incomes_by_ticker

    async def get_financial_ratios(self, ticker: str) -> FinancialRatios:
        return self._ratios[ticker]

    async def get_income_statement(
        self, ticker: str, period: str = "annual", limit: int = 5
    ) -> list[IncomeStatement]:
        return self._incomes.get(ticker, [])


class DummyProfiles:
    """Dummy profiles provider for comps tests."""

    def __init__(self, profiles_by_ticker: dict[str, CompanyProfile]) -> None:
        self._profiles = profiles_by_ticker

    async def get_company_profile(self, ticker: str) -> CompanyProfile:
        return self._profiles[ticker]


class TestCompsEngine:
    """Test suite for CompsEngine."""

    def test_median_filters_missing_and_infinite(self) -> None:
        """Median ignores None and non-finite values."""
        engine = CompsEngine()

        assert engine._median([1.0, None, 3.0]) == 2.0
        assert engine._median([None, None]) is None
        assert engine._median([1.0, float("inf"), 2.0]) == 1.5

    @pytest.mark.asyncio
    async def test_analyze_single_peer_latest_income(self, monkeypatch) -> None:
        """Single peer medians equal the peer; implied values use latest income."""
        engine = CompsEngine()

        ratios = {
            "TGT": FinancialRatios(
                ticker="TGT",
                pe_ratio=12.0,
                ev_to_ebitda=6.0,
                price_to_book=1.5,
                price_to_sales=2.0,
                source="test",
            ),
            "PEER": FinancialRatios(
                ticker="PEER",
                pe_ratio=10.0,
                ev_to_ebitda=5.0,
                price_to_book=2.0,
                price_to_sales=3.0,
                source="test",
            ),
        }
        profiles = {
            "TGT": CompanyProfile(
                ticker="TGT",
                company_name="Target Co",
                market_cap=1000.0,
                source="test",
            ),
            "PEER": CompanyProfile(
                ticker="PEER",
                company_name="Peer Co",
                market_cap=500.0,
                source="test",
            ),
        }
        income = IncomeStatement(
            ticker="TGT",
            period_date=date(2024, 12, 31),
            period_type=PeriodType.ANNUAL,
            eps=2.0,
            eps_diluted=2.5,
            ebitda=100.0,
            source="test",
        )

        monkeypatch.setattr(
            comps_module,
            "get_fundamentals",
            lambda user_settings=None: DummyFundamentals(ratios, {"TGT": [income]}),
        )
        monkeypatch.setattr(
            comps_module,
            "get_profiles",
            lambda user_settings=None: DummyProfiles(profiles),
        )

        result = await engine.analyze("TGT", ["PEER"])

        assert result.median_pe == 10.0
        assert result.median_ev_to_ebitda == 5.0
        assert result.implied_value_pe == pytest.approx(25.0)
        assert result.implied_value_ev_to_ebitda == pytest.approx(500.0)

        target_metric = next(m for m in result.metrics if m.is_target)
        assert target_metric.eps == 2.5
        assert target_metric.eps_source == "latest_income"

    @pytest.mark.asyncio
    async def test_analyze_uses_consensus_forecasts(self, monkeypatch) -> None:
        """Consensus forecasts override latest income values."""
        engine = CompsEngine()

        ratios = {
            "TGT": FinancialRatios(
                ticker="TGT",
                pe_ratio=12.0,
                ev_to_ebitda=6.0,
                price_to_book=1.5,
                price_to_sales=2.0,
                source="test",
            ),
            "PEER": FinancialRatios(
                ticker="PEER",
                pe_ratio=8.0,
                ev_to_ebitda=4.0,
                price_to_book=2.0,
                price_to_sales=3.0,
                source="test",
            ),
        }
        profiles = {
            "TGT": CompanyProfile(
                ticker="TGT",
                company_name="Target Co",
                market_cap=1000.0,
                source="test",
            ),
            "PEER": CompanyProfile(
                ticker="PEER",
                company_name="Peer Co",
                market_cap=500.0,
                source="test",
            ),
        }
        income = IncomeStatement(
            ticker="TGT",
            period_date=date(2024, 12, 31),
            period_type=PeriodType.ANNUAL,
            eps=1.0,
            eps_diluted=1.2,
            ebitda=80.0,
            source="test",
        )

        consensus = {"TGT": {"eps": 3.2, "ebitda": 200.0}}

        monkeypatch.setattr(
            comps_module,
            "get_fundamentals",
            lambda user_settings=None: DummyFundamentals(ratios, {"TGT": [income]}),
        )
        monkeypatch.setattr(
            comps_module,
            "get_profiles",
            lambda user_settings=None: DummyProfiles(profiles),
        )

        result = await engine.analyze("TGT", ["PEER"], consensus_forecasts=consensus)

        assert result.median_pe == 8.0
        assert result.implied_value_pe == pytest.approx(25.6)

        target_metric = next(m for m in result.metrics if m.is_target)
        assert target_metric.eps == 3.2
        assert target_metric.eps_source == "consensus"
        assert target_metric.ebitda == 200.0
        assert target_metric.ebitda_source == "consensus"
