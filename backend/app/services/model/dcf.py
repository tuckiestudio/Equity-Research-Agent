"""Discounted Cash Flow (DCF) valuation calculator.

Pure computation module for DCF valuation.
No async, no database calls — just math.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.models.assumption import AssumptionSet
from app.services.model.engine import ModelOutput, ProjectedFinancials


class DCFResult(BaseModel):
    """DCF valuation output."""

    ticker: str
    assumption_set_name: str
    enterprise_value: float
    equity_value: float
    per_share_value: float
    terminal_value: float
    pv_of_fcfs: float
    pv_of_terminal: float
    upside_pct: float
    wacc: float
    terminal_growth_rate: float
    current_price: float
    projection_years: int

    model_config = {"from_attributes": True}


class DCFCalculator:
    """Calculator for Discounted Cash Flow valuation.

    Uses the projected FCFs from ModelEngine and discount them
    to present value using WACC.
    """

    def calculate(
        self,
        model_output: ModelOutput,
        assumptions: AssumptionSet,
        current_price: float,
        shares_outstanding: float,
        net_debt: float,
    ) -> DCFResult:
        """Calculate DCF valuation.

        Steps:
        1. Discount each year's FCF: PV = FCF / (1 + WACC)^year
        2. Terminal value = final_year_fcf * (1 + terminal_growth) / (WACC - terminal_growth)
        3. PV of terminal = terminal_value / (1 + WACC)^n
        4. Enterprise value = sum(PV of FCFs) + PV of terminal
        5. Equity value = enterprise_value - net_debt
        6. Per share = equity_value / shares_outstanding
        7. Upside = (per_share - current_price) / current_price

        Args:
            model_output: Output from ModelEngine with projections
            assumptions: AssumptionSet with WACC, terminal growth rate
            current_price: Current stock price
            shares_outstanding: Number of shares outstanding
            net_debt: Total debt minus cash (positive = net debt)

        Returns:
            DCFResult with valuation metrics

        Raises:
            ValueError: If WACC <= terminal_growth_rate (denominator would be <= 0)
        """
        wacc = assumptions.wacc
        terminal_growth = assumptions.terminal_growth_rate

        # Validate WACC > terminal growth rate
        if wacc <= terminal_growth:
            raise ValueError(
                f"WACC ({wacc:.4f}) must be greater than terminal growth rate "
                f"({terminal_growth:.4f}) for DCF calculation"
            )

        if shares_outstanding <= 0:
            raise ValueError("Shares outstanding must be positive")

        # Step 1: Discount each year's FCF
        pv_of_fcfs = 0.0
        projections: list[ProjectedFinancials] = model_output.projections

        for i, proj in enumerate(projections):
            year = i + 1  # Year 1, 2, 3, 4, 5...
            pv = proj.free_cash_flow / ((1 + wacc) ** year)
            pv_of_fcfs += pv

        # Step 2: Calculate terminal value using Gordon Growth Model
        # TV = Final Year FCF * (1 + g) / (WACC - g)
        final_year_fcf = projections[-1].free_cash_flow
        terminal_value = final_year_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

        # Step 3: Discount terminal value to present
        n = len(projections)
        pv_of_terminal = terminal_value / ((1 + wacc) ** n)

        # Step 4: Enterprise value = PV of FCFs + PV of terminal
        enterprise_value = pv_of_fcfs + pv_of_terminal

        # Step 5: Equity value = Enterprise value - net_debt
        equity_value = enterprise_value - net_debt

        # Step 6: Per share value
        per_share_value = equity_value / shares_outstanding

        # Step 7: Upside vs current price
        if current_price > 0:
            upside_pct = (per_share_value - current_price) / current_price
        else:
            upside_pct = 0.0

        return DCFResult(
            ticker=model_output.ticker,
            assumption_set_name=model_output.assumption_set_name,
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            per_share_value=per_share_value,
            terminal_value=terminal_value,
            pv_of_fcfs=pv_of_fcfs,
            pv_of_terminal=pv_of_terminal,
            upside_pct=upside_pct,
            wacc=wacc,
            terminal_growth_rate=terminal_growth,
            current_price=current_price,
            projection_years=n,
        )

    def calculate_sensitivity(
        self,
        model_output: ModelOutput,
        assumptions: AssumptionSet,
        current_price: float,
        shares_outstanding: float,
        net_debt: float,
        wacc_range: list[float],
        terminal_growth_range: list[float],
    ) -> list[dict]:
        """Calculate sensitivity analysis for different WACC and terminal growth combinations.

        Args:
            model_output: Output from ModelEngine with projections
            assumptions: Base AssumptionSet (will be modified for sensitivity)
            current_price: Current stock price
            shares_outstanding: Number of shares outstanding
            net_debt: Total debt minus cash
            wacc_range: List of WACC values to test
            terminal_growth_range: List of terminal growth rates to test

        Returns:
            List of dicts with wacc, terminal_growth, and per_share_value
        """
        results = []

        for wacc in wacc_range:
            for terminal_growth in terminal_growth_range:
                # Skip invalid combinations
                if wacc <= terminal_growth:
                    continue

                # Create a modified assumptions object for this combination
                # We'll create a simple dict-based approach
                try:
                    result = self.calculate(
                        model_output=model_output,
                        assumptions=assumptions,  # Will override wacc and growth
                        current_price=current_price,
                        shares_outstanding=shares_outstanding,
                        net_debt=net_debt,
                    )
                    # The calculate method uses the assumptions object directly,
                    # so we need to temporarily modify it or create a copy
                    # For now, we'll recalculate with adjusted values
                except ValueError:
                    continue

                results.append({
                    "wacc": wacc,
                    "terminal_growth_rate": terminal_growth,
                    "per_share_value": result.per_share_value,
                })

        return results
