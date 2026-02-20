"""Financial model computation engine.

Pure computation module for projecting financials based on assumptions.
No async, no database calls — just math.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.models.assumption import AssumptionSet
from app.schemas.financial import BalanceSheet, CashFlow, IncomeStatement


class ProjectedFinancials(BaseModel):
    """Single year of projected financials."""

    year: int
    revenue: float
    gross_profit: float
    operating_income: float
    ebitda: float
    net_income: float
    free_cash_flow: float
    eps: float
    capex: float
    depreciation_amortization: float

    model_config = {"from_attributes": True}


class ModelOutput(BaseModel):
    """Full model output from the projection engine."""

    ticker: str
    assumption_set_name: str
    projection_years: int
    projections: list[ProjectedFinancials]
    base_year_revenue: float
    base_year: int

    model_config = {"from_attributes": True}


class ModelEngine:
    """Pure computation engine for financial projections.

    Takes historical financials and assumptions, produces multi-year projections.
    All computation is synchronous and deterministic.
    """

    def compute(
        self,
        assumptions: AssumptionSet,
        latest_income: IncomeStatement,
        latest_balance: BalanceSheet,
        latest_cashflow: CashFlow,
    ) -> ModelOutput:
        """Compute projected financials based on assumptions.

        Args:
            assumptions: AssumptionSet with growth rates, margins, etc.
            latest_income: Most recent income statement
            latest_balance: Most recent balance sheet
            latest_cashflow: Most recent cash flow statement

        Returns:
            ModelOutput with year-by-year projections

        Raises:
            ValueError: If required data is missing or invalid
        """
        # Validate required fields
        if latest_income.revenue is None or latest_income.revenue <= 0:
            raise ValueError("Income statement must have positive revenue")

        # Get shares outstanding - prefer override, otherwise from balance sheet
        shares_outstanding = self._get_shares_outstanding(
            assumptions, latest_income, latest_balance
        )

        # Parse growth rates
        growth_rates = assumptions.get_revenue_growth_rates()
        if len(growth_rates) != assumptions.projection_years:
            raise ValueError(
                f"Expected {assumptions.projection_years} growth rates, "
                f"got {len(growth_rates)}"
            )

        # Base year
        base_year = latest_income.period_date.year
        base_revenue = latest_income.revenue

        # Project year by year
        projections: list[ProjectedFinancials] = []
        current_revenue = base_revenue

        for i in range(assumptions.projection_years):
            year = base_year + i + 1
            growth_rate = growth_rates[i]

            # Revenue grows by growth rate
            current_revenue = current_revenue * (1 + growth_rate)

            # Gross profit
            gross_profit = current_revenue * assumptions.gross_margin

            # Operating income (EBIT)
            operating_income = current_revenue * assumptions.operating_margin

            # Depreciation & Amortization
            da = current_revenue * assumptions.da_as_pct_revenue

            # EBITDA
            ebitda = operating_income + da

            # Tax
            tax = operating_income * assumptions.tax_rate

            # Net income
            net_income = operating_income - tax

            # Capex
            capex = current_revenue * assumptions.capex_as_pct_revenue

            # Free Cash Flow = Net Income + DA - Capex
            fcf = net_income + da - capex

            # EPS
            eps = net_income / shares_outstanding if shares_outstanding > 0 else 0

            projection = ProjectedFinancials(
                year=year,
                revenue=current_revenue,
                gross_profit=gross_profit,
                operating_income=operating_income,
                ebitda=ebitda,
                net_income=net_income,
                free_cash_flow=fcf,
                eps=eps,
                capex=capex,
                depreciation_amortization=da,
            )
            projections.append(projection)

        return ModelOutput(
            ticker=latest_income.ticker,
            assumption_set_name=assumptions.name,
            projection_years=assumptions.projection_years,
            projections=projections,
            base_year_revenue=base_revenue,
            base_year=base_year,
        )

    def _get_shares_outstanding(
        self,
        assumptions: AssumptionSet,
        latest_income: IncomeStatement,
        latest_balance: BalanceSheet,
    ) -> float:
        """Get shares outstanding, preferring override from assumptions."""
        # Prefer override
        if assumptions.shares_outstanding is not None:
            return assumptions.shares_outstanding

        # Try income statement first (has diluted shares)
        if latest_income.shares_diluted is not None and latest_income.shares_diluted > 0:
            return latest_income.shares_diluted

        if latest_income.shares_outstanding is not None and latest_income.shares_outstanding > 0:
            return latest_income.shares_outstanding

        # Try balance sheet
        if (
            latest_balance.shares_outstanding is not None
            and latest_balance.shares_outstanding > 0
        ):
            return latest_balance.shares_outstanding

        raise ValueError("Shares outstanding not available in financial data")
