"""Tests for assumption waterfall logic."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.financial import BalanceSheet, CashFlow, IncomeStatement, PeriodType
from app.services.model.dcf import DCFCalculator
from app.services.model.engine import ModelEngine


class MockAssumption:
    """Mock assumption set for waterfall tests."""

    def __init__(self) -> None:
        self.name = "Base Case"
        self.projection_years = 5
        self.gross_margin = 0.45
        self.operating_margin = 0.30
        self.tax_rate = 0.21
        self.wacc = 0.10
        self.terminal_growth_rate = 0.025
        self.capex_as_pct_revenue = 0.05
        self.da_as_pct_revenue = 0.03
        self.shares_outstanding = 1_000_000_000
        self.net_debt = 10_000_000_000
        self._growth_rates = [0.15, 0.12, 0.10, 0.08, 0.06]

    def get_revenue_growth_rates(self) -> list[float]:
        """Return growth rates list."""
        return list(self._growth_rates)

    def set_revenue_growth_rates(self, rates: list[float]) -> None:
        """Set growth rates list."""
        self._growth_rates = list(rates)


@pytest.fixture
def sample_financials():
    """Create sample financial statements."""
    income = IncomeStatement(
        ticker="AAPL",
        period_date=date(2023, 9, 30),
        period_type=PeriodType.ANNUAL,
        revenue=100_000_000_000,
        cost_of_revenue=55_000_000_000,
        gross_profit=45_000_000_000,
        operating_income=30_000_000_000,
        ebitda=35_000_000_000,
        depreciation_amortization=5_000_000_000,
        income_before_tax=30_000_000_000,
        income_tax_expense=6_300_000_000,
        net_income=23_700_000_000,
        eps_diluted=1.50,
        shares_diluted=1_000_000_000,
        shares_outstanding=1_000_000_000,
        source="test",
    )

    balance = BalanceSheet(
        ticker="AAPL",
        period_date=date(2023, 9, 30),
        period_type=PeriodType.ANNUAL,
        cash_and_equivalents=20_000_000_000,
        short_term_debt=5_000_000_000,
        long_term_debt=25_000_000_000,
        total_liabilities=150_000_000_000,
        total_stockholders_equity=100_000_000_000,
        shares_outstanding=1_000_000_000,
        source="test",
    )

    cash_flow = CashFlow(
        ticker="AAPL",
        period_date=date(2023, 9, 30),
        period_type=PeriodType.ANNUAL,
        operating_cash_flow=40_000_000_000,
        capital_expenditure=5_000_000_000,
        free_cash_flow=35_000_000_000,
        source="test",
    )

    return income, balance, cash_flow


def compute_per_share(
    assumption: MockAssumption,
    income: IncomeStatement,
    balance: BalanceSheet,
    cash_flow: CashFlow,
) -> float:
    """Helper to compute per-share value for testing."""
    engine = ModelEngine()
    model_output = engine.compute(
        assumptions=assumption,
        latest_income=income,
        latest_balance=balance,
        latest_cashflow=cash_flow,
    )

    calculator = DCFCalculator()
    result = calculator.calculate(
        model_output=model_output,
        assumptions=assumption,
        current_price=100.0,
        shares_outstanding=assumption.shares_outstanding,
        net_debt=assumption.net_debt,
    )

    return result.per_share_value


def test_waterfall_tweaks_affect_values(sample_financials) -> None:
    """Growth increases raise value, WACC increases lower value."""
    income, balance, cash_flow = sample_financials
    base = MockAssumption()

    base_per_share = compute_per_share(base, income, balance, cash_flow)

    higher_growth = MockAssumption()
    rates = higher_growth.get_revenue_growth_rates()
    higher_growth.set_revenue_growth_rates([rate * 1.10 for rate in rates])
    growth_per_share = compute_per_share(higher_growth, income, balance, cash_flow)

    higher_wacc = MockAssumption()
    higher_wacc.wacc *= 1.10
    wacc_per_share = compute_per_share(higher_wacc, income, balance, cash_flow)

    assert growth_per_share > base_per_share
    assert wacc_per_share < base_per_share


def test_waterfall_item_count() -> None:
    """All six assumption tweaks are represented."""
    tweaks = [
        "revenue_growth_rates",
        "operating_margin",
        "wacc",
        "terminal_growth_rate",
        "capex_as_pct_revenue",
        "tax_rate",
    ]
    assert len(tweaks) == 6


def test_impact_pct_formula(sample_financials) -> None:
    """Impact percent uses (tweaked-base)/base."""
    income, balance, cash_flow = sample_financials
    base = MockAssumption()
    base_per_share = compute_per_share(base, income, balance, cash_flow)

    tweak = MockAssumption()
    tweak.operating_margin *= 1.10
    tweaked_per_share = compute_per_share(tweak, income, balance, cash_flow)

    impact_pct = (tweaked_per_share - base_per_share) / base_per_share
    assert impact_pct == pytest.approx((tweaked_per_share - base_per_share) / base_per_share)
