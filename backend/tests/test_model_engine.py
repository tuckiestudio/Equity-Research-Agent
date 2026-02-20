"""Tests for financial model engine and DCF calculator.

Pure computation tests — no mocking needed.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.financial import BalanceSheet, CashFlow, IncomeStatement, PeriodType
from app.services.model.dcf import DCFCalculator, DCFResult
from app.services.model.engine import ModelEngine, ModelOutput

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_assumption_set():
    """Create a sample assumption set for testing."""
    # Create a mock assumption object
    class MockAssumption:
        def __init__(self):
            self.name = "Base Case"
            self.projection_years = 5
            self.gross_margin = 0.45
            self.operating_margin = 0.30
            self.tax_rate = 0.21
            self.wacc = 0.10
            self.terminal_growth_rate = 0.025
            self.capex_as_pct_revenue = 0.05
            self.da_as_pct_revenue = 0.03
            self.shares_outstanding = 1000_000_000  # 1B shares
            self.net_debt = 10_000_000_000  # $10B net debt

            # Revenue growth rates: 15%, 12%, 10%, 8%, 6%
            self.revenue_growth_rates = [0.15, 0.12, 0.10, 0.08, 0.06]

        def get_revenue_growth_rates(self):
            return self.revenue_growth_rates

    return MockAssumption()


@pytest.fixture
def sample_income_statement():
    """Create a sample income statement."""
    return IncomeStatement(
        ticker="AAPL",
        period_date=date(2023, 9, 30),
        period_type=PeriodType.ANNUAL,
        revenue=100_000_000_000,  # $100B
        cost_of_revenue=55_000_000_000,  # $55B
        gross_profit=45_000_000_000,  # $45B
        operating_income=30_000_000_000,  # $30B
        ebitda=35_000_000_000,  # $35B
        depreciation_amortization=5_000_000_000,  # $5B
        income_before_tax=30_000_000_000,
        income_tax_expense=6_300_000_000,
        net_income=23_700_000_000,  # $23.7B
        eps_diluted=1.50,
        shares_diluted=1000_000_000,
        shares_outstanding=1000_000_000,
        source="test",
    )


@pytest.fixture
def sample_balance_sheet():
    """Create a sample balance sheet."""
    return BalanceSheet(
        ticker="AAPL",
        period_date=date(2023, 9, 30),
        period_type=PeriodType.ANNUAL,
        cash_and_equivalents=20_000_000_000,  # $20B
        short_term_debt=5_000_000_000,  # $5B
        long_term_debt=25_000_000_000,  # $25B
        total_liabilities=150_000_000_000,
        total_stockholders_equity=100_000_000_000,
        shares_outstanding=1000_000_000,
        source="test",
    )


@pytest.fixture
def sample_cash_flow():
    """Create a sample cash flow statement."""
    return CashFlow(
        ticker="AAPL",
        period_date=date(2023, 9, 30),
        period_type=PeriodType.ANNUAL,
        operating_cash_flow=40_000_000_000,  # $40B
        capital_expenditure=5_000_000_000,  # $5B
        free_cash_flow=35_000_000_000,  # $35B
        source="test",
    )


# =============================================================================
# ModelEngine Tests
# =============================================================================

class TestModelEngine:
    """Test suite for ModelEngine."""

    @pytest.fixture
    def engine(self):
        """Create a ModelEngine instance."""
        return ModelEngine()

    def test_basic_projection(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Revenue grows by growth rates, margins applied correctly."""
        result = engine.compute(
            assumptions=sample_assumption_set,
            latest_income=sample_income_statement,
            latest_balance=sample_balance_sheet,
            latest_cashflow=sample_cash_flow,
        )

        assert isinstance(result, ModelOutput)
        assert result.ticker == "AAPL"
        assert result.assumption_set_name == "Base Case"
        assert result.projection_years == 5
        assert len(result.projections) == 5
        assert result.base_year_revenue == 100_000_000_000

        # Year 1: 15% growth
        year1 = result.projections[0]
        assert year1.year == 2024
        assert year1.revenue == pytest.approx(115_000_000_000, rel=0.01)  # $100B * 1.15
        assert year1.gross_profit == pytest.approx(51_750_000_000, rel=0.01)  # 45% margin
        assert year1.operating_income == pytest.approx(34_500_000_000, rel=0.01)  # 30% margin

    def test_fcf_calculation(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """FCF = net_income + DA - capex."""
        result = engine.compute(
            assumptions=sample_assumption_set,
            latest_income=sample_income_statement,
            latest_balance=sample_balance_sheet,
            latest_cashflow=sample_cash_flow,
        )

        year1 = result.projections[0]
        # Operating income = $115B * 30% = $34.5B
        # Tax = $34.5B * 21% = $7.245B
        # Net income = $34.5B - $7.245B = $27.255B
        # DA = $115B * 3% = $3.45B
        # Capex = $115B * 5% = $5.75B
        # FCF = $27.255B + $3.45B - $5.75B = $24.955B
        assert year1.free_cash_flow == pytest.approx(24_955_000_000, rel=0.01)

    def test_single_year_projection(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Single year projection works."""
        sample_assumption_set.projection_years = 1
        sample_assumption_set.revenue_growth_rates = [0.10]

        result = engine.compute(
            assumptions=sample_assumption_set,
            latest_income=sample_income_statement,
            latest_balance=sample_balance_sheet,
            latest_cashflow=sample_cash_flow,
        )

        assert result.projection_years == 1
        assert len(result.projections) == 1
        assert result.projections[0].year == 2024

    def test_eps_calculation(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """EPS = net_income / shares_outstanding."""
        result = engine.compute(
            assumptions=sample_assumption_set,
            latest_income=sample_income_statement,
            latest_balance=sample_balance_sheet,
            latest_cashflow=sample_cash_flow,
        )

        year1 = result.projections[0]
        # Net income ≈ $27.255B, Shares = 1B
        # EPS ≈ $27.26
        assert year1.eps == pytest.approx(27.26, rel=0.01)

    def test_zero_growth(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Zero growth rates produce flat revenue."""
        sample_assumption_set.projection_years = 3
        sample_assumption_set.revenue_growth_rates = [0.0, 0.0, 0.0]

        result = engine.compute(
            assumptions=sample_assumption_set,
            latest_income=sample_income_statement,
            latest_balance=sample_balance_sheet,
            latest_cashflow=sample_cash_flow,
        )

        assert result.projections[0].revenue == pytest.approx(100_000_000_000, rel=0.01)
        assert result.projections[1].revenue == pytest.approx(100_000_000_000, rel=0.01)
        assert result.projections[2].revenue == pytest.approx(100_000_000_000, rel=0.01)

    def test_negative_growth(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Negative growth rates decrease revenue."""
        sample_assumption_set.projection_years = 2
        sample_assumption_set.revenue_growth_rates = [-0.10, -0.05]

        result = engine.compute(
            assumptions=sample_assumption_set,
            latest_income=sample_income_statement,
            latest_balance=sample_balance_sheet,
            latest_cashflow=sample_cash_flow,
        )

        # Year 1: 10% decline
        assert result.projections[0].revenue == pytest.approx(90_000_000_000, rel=0.01)
        # Year 2: 5% decline from $90B
        assert result.projections[1].revenue == pytest.approx(85_500_000_000, rel=0.01)

    def test_invalid_revenue_raises_error(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Missing or zero revenue raises ValueError."""
        sample_income_statement.revenue = 0

        with pytest.raises(ValueError, match="positive revenue"):
            engine.compute(
                assumptions=sample_assumption_set,
                latest_income=sample_income_statement,
                latest_balance=sample_balance_sheet,
                latest_cashflow=sample_cash_flow,
            )

    def test_mismatched_growth_rates_raises_error(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Growth rates length must match projection_years."""
        sample_assumption_set.revenue_growth_rates = [0.10, 0.08]  # Only 2 rates for 5 years

        with pytest.raises(ValueError, match="Expected 5 growth rates, got 2"):
            engine.compute(
                assumptions=sample_assumption_set,
                latest_income=sample_income_statement,
                latest_balance=sample_balance_sheet,
                latest_cashflow=sample_cash_flow,
            )

    def test_no_shares_outstanding_raises_error(self, engine, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Missing shares outstanding raises ValueError."""
        sample_assumption_set.shares_outstanding = None
        sample_income_statement.shares_diluted = None
        sample_income_statement.shares_outstanding = None
        sample_balance_sheet.shares_outstanding = None

        with pytest.raises(ValueError, match="Shares outstanding not available"):
            engine.compute(
                assumptions=sample_assumption_set,
                latest_income=sample_income_statement,
                latest_balance=sample_balance_sheet,
                latest_cashflow=sample_cash_flow,
            )


# =============================================================================
# DCFCalculator Tests
# =============================================================================

class TestDCFCalculator:
    """Test suite for DCFCalculator."""

    @pytest.fixture
    def calculator(self):
        """Create a DCFCalculator instance."""
        return DCFCalculator()

    @pytest.fixture
    def sample_model_output(self, sample_assumption_set, sample_income_statement, sample_balance_sheet, sample_cash_flow):
        """Create a sample model output for DCF testing."""
        engine = ModelEngine()
        return engine.compute(
            assumptions=sample_assumption_set,
            latest_income=sample_income_statement,
            latest_balance=sample_balance_sheet,
            latest_cashflow=sample_cash_flow,
        )

    def test_basic_dcf(self, calculator, sample_model_output, sample_assumption_set):
        """Terminal value + PV of FCFs = enterprise value."""
        result = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=150.0,
            shares_outstanding=1000_000_000,
            net_debt=10_000_000_000,
        )

        assert isinstance(result, DCFResult)
        assert result.ticker == "AAPL"
        assert result.assumption_set_name == "Base Case"
        assert result.enterprise_value > 0
        assert result.equity_value > 0
        assert result.per_share_value > 0
        assert result.terminal_value > 0
        assert result.pv_of_fcfs > 0
        assert result.pv_of_terminal > 0

    def test_equity_value_subtracts_debt(self, calculator, sample_model_output, sample_assumption_set):
        """Equity = EV - net_debt."""
        result_no_debt = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=150.0,
            shares_outstanding=1000_000_000,
            net_debt=0,
        )

        result_with_debt = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=150.0,
            shares_outstanding=1000_000_000,
            net_debt=10_000_000_000,
        )

        # Enterprise value should be the same
        assert result_no_debt.enterprise_value == pytest.approx(result_with_debt.enterprise_value, rel=0.01)

        # Equity value with debt should be lower
        assert result_with_debt.equity_value == pytest.approx(result_no_debt.equity_value - 10_000_000_000, rel=0.01)

    def test_per_share_value(self, calculator, sample_model_output, sample_assumption_set):
        """Per share = equity / shares."""
        result = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=150.0,
            shares_outstanding=1000_000_000,
            net_debt=10_000_000_000,
        )

        # Per share should be equity value divided by shares
        expected_per_share = result.equity_value / 1000_000_000
        assert result.per_share_value == pytest.approx(expected_per_share, rel=0.01)

    def test_upside_calculation(self, calculator, sample_model_output, sample_assumption_set):
        """Upside = (per_share - price) / price."""
        current_price = 150.0

        result = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=current_price,
            shares_outstanding=1000_000_000,
            net_debt=10_000_000_000,
        )

        expected_upside = (result.per_share_value - current_price) / current_price
        assert result.upside_pct == pytest.approx(expected_upside, rel=0.01)

    def test_terminal_value_formula(self, calculator, sample_model_output, sample_assumption_set):
        """TV = FCF * (1+g) / (WACC - g)."""
        result = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=150.0,
            shares_outstanding=1000_000_000,
            net_debt=10_000_000_000,
        )

        # Get the final year FCF
        final_year_fcf = sample_model_output.projections[-1].free_cash_flow

        # Calculate expected terminal value
        wacc = sample_assumption_set.wacc
        terminal_growth = sample_assumption_set.terminal_growth_rate
        expected_tv = final_year_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

        assert result.terminal_value == pytest.approx(expected_tv, rel=0.01)

    def test_high_wacc_lowers_value(self, calculator, sample_model_output, sample_assumption_set):
        """Higher WACC → lower enterprise value."""
        # Calculate with 10% WACC
        sample_assumption_set.wacc = 0.10
        result_low_wacc = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=150.0,
            shares_outstanding=1000_000_000,
            net_debt=10_000_000_000,
        )

        # Calculate with 15% WACC
        sample_assumption_set.wacc = 0.15
        result_high_wacc = calculator.calculate(
            model_output=sample_model_output,
            assumptions=sample_assumption_set,
            current_price=150.0,
            shares_outstanding=1000_000_000,
            net_debt=10_000_000_000,
        )

        # Higher WACC should result in lower enterprise value
        assert result_high_wacc.enterprise_value < result_low_wacc.enterprise_value

    def test_wacc_must_exceed_terminal_growth(self, calculator, sample_model_output, sample_assumption_set):
        """WACC must be greater than terminal growth rate."""
        sample_assumption_set.wacc = 0.02  # Lower than terminal_growth_rate (0.025)

        with pytest.raises(ValueError, match="WACC .* must be greater than terminal growth rate"):
            calculator.calculate(
                model_output=sample_model_output,
                assumptions=sample_assumption_set,
                current_price=150.0,
                shares_outstanding=1000_000_000,
                net_debt=10_000_000_000,
            )

    def test_invalid_shares_outstanding_raises_error(self, calculator, sample_model_output, sample_assumption_set):
        """Zero or negative shares outstanding raises ValueError."""
        with pytest.raises(ValueError, match="Shares outstanding must be positive"):
            calculator.calculate(
                model_output=sample_model_output,
                assumptions=sample_assumption_set,
                current_price=150.0,
                shares_outstanding=0,
                net_debt=10_000_000_000,
            )
