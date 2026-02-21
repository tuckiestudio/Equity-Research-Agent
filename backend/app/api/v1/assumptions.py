"""
Assumptions API endpoints — manage financial modeling assumptions.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.assumption import AssumptionSet
from app.models.stock import Stock
from app.models.user import User
from app.schemas.assumption import (
    AssumptionCreate,
    AssumptionResponse,
    AssumptionUpdate,
    DCFResultResponse,
    ModelOutputResponse,
    ProjectedFinancialsResponse,
)
from app.services.data.registry import get_fundamentals, get_prices
from app.services.model.dcf import DCFCalculator
from app.services.model.engine import ModelEngine

logger = get_logger(__name__)

router = APIRouter(prefix="/assumptions", tags=["assumptions"])


# =============================================================================
# Helper Functions
# =============================================================================

async def get_stock_by_ticker(ticker: str, db: AsyncSession, user: User) -> Stock:
    """Get a stock by ticker, raising NotFoundError if not found."""
    result = await db.execute(
        select(Stock).where(Stock.ticker == ticker.upper())
    )
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)
    return stock


async def get_assumption_set(
    assumption_id: str,
    db: AsyncSession,
    user: User,
) -> AssumptionSet:
    """Get an assumption set by ID, ensuring it belongs to the user."""
    try:
        assumption_uuid = uuid.UUID(assumption_id)
    except ValueError:
        raise NotFoundError("AssumptionSet", assumption_id)

    result = await db.execute(
        select(AssumptionSet).where(
            AssumptionSet.id == assumption_uuid,
            AssumptionSet.user_id == user.id,
        )
    )
    assumption = result.scalar_one_or_none()
    if not assumption:
        raise NotFoundError("AssumptionSet", assumption_id)
    return assumption


def db_to_response(assumption: AssumptionSet) -> AssumptionResponse:
    """Convert database model to response schema."""
    return AssumptionResponse(
        id=str(assumption.id),
        stock_id=str(assumption.stock_id),
        user_id=str(assumption.user_id),
        name=assumption.name,
        is_active=assumption.is_active,
        revenue_growth_rates=assumption.get_revenue_growth_rates(),
        projection_years=assumption.projection_years,
        gross_margin=assumption.gross_margin,
        operating_margin=assumption.operating_margin,
        tax_rate=assumption.tax_rate,
        wacc=assumption.wacc,
        terminal_growth_rate=assumption.terminal_growth_rate,
        capex_as_pct_revenue=assumption.capex_as_pct_revenue,
        da_as_pct_revenue=assumption.da_as_pct_revenue,
        shares_outstanding=assumption.shares_outstanding,
        net_debt=assumption.net_debt,
        created_at=assumption.created_at,
        updated_at=assumption.updated_at,
    )


async def get_latest_financials(ticker: str, user_settings):
    """Fetch the latest financials for a stock.

    Returns:
        Tuple of (latest_income, latest_balance, latest_cashflow)

    Raises:
        ProviderError: If unable to fetch financials
        ValidationError: If financials are missing required data
    """
    fundamentals = get_fundamentals(user_settings)

    # Get the latest annual data
    income_statements = await fundamentals.get_income_statement(ticker, period="annual", limit=1)
    balance_sheets = await fundamentals.get_balance_sheet(ticker, period="annual", limit=1)
    cash_flows = await fundamentals.get_cash_flow(ticker, period="annual", limit=1)

    if not income_statements:
        raise ValidationError("Unable to fetch income statement for the stock", errors=[])

    if not balance_sheets:
        raise ValidationError("Unable to fetch balance sheet for the stock", errors=[])

    if not cash_flows:
        raise ValidationError("Unable to fetch cash flow statement for the stock", errors=[])

    return income_statements[0], balance_sheets[0], cash_flows[0]


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/{ticker}", response_model=AssumptionResponse)
async def create_assumption_set(
    ticker: str,
    assumption_data: AssumptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssumptionResponse:
    """Create a new assumption set for a stock.

    If this is the first assumption set for the stock, it will be marked as active.
    """
    stock = await get_stock_by_ticker(ticker, db, current_user)

    # Check if this is the first assumption set for this stock/user
    result = await db.execute(
        select(AssumptionSet).where(
            AssumptionSet.stock_id == stock.id,
            AssumptionSet.user_id == current_user.id,
        )
    )
    existing_count = len(result.all())

    # Create new assumption set
    assumption = AssumptionSet(
        stock_id=stock.id,
        user_id=current_user.id,
        name=assumption_data.name,
        is_active=(existing_count == 0),  # First set is active
        projection_years=assumption_data.projection_years,
        gross_margin=assumption_data.gross_margin,
        operating_margin=assumption_data.operating_margin,
        tax_rate=assumption_data.tax_rate,
        wacc=assumption_data.wacc,
        terminal_growth_rate=assumption_data.terminal_growth_rate,
        capex_as_pct_revenue=assumption_data.capex_as_pct_revenue,
        da_as_pct_revenue=assumption_data.da_as_pct_revenue,
        shares_outstanding=assumption_data.shares_outstanding,
        net_debt=assumption_data.net_debt,
    )
    assumption.set_revenue_growth_rates(assumption_data.revenue_growth_rates)

    db.add(assumption)
    await db.commit()
    await db.refresh(assumption)

    return db_to_response(assumption)


@router.get("/{ticker}", response_model=list[AssumptionResponse])
async def list_assumption_sets(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AssumptionResponse]:
    """List all assumption sets for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    result = await db.execute(
        select(AssumptionSet)
        .where(
            AssumptionSet.stock_id == stock.id,
            AssumptionSet.user_id == current_user.id,
        )
        .order_by(AssumptionSet.created_at.desc())
    )
    assumptions = result.scalars().all()

    return [db_to_response(a) for a in assumptions]


@router.get("/{ticker}/active", response_model=AssumptionResponse)
async def get_active_assumption_set(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssumptionResponse:
    """Get the active assumption set for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    result = await db.execute(
        select(AssumptionSet).where(
            AssumptionSet.stock_id == stock.id,
            AssumptionSet.user_id == current_user.id,
            AssumptionSet.is_active == True,
        )
    )
    assumption = result.scalar_one_or_none()

    if not assumption:
        raise NotFoundError("Active AssumptionSet", f"for ticker {ticker}")

    return db_to_response(assumption)


@router.put("/{assumption_id}", response_model=AssumptionResponse)
async def update_assumption_set(
    assumption_id: str,
    update_data: AssumptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssumptionResponse:
    """Update an existing assumption set."""
    assumption = await get_assumption_set(assumption_id, db, current_user)

    # Update fields
    if update_data.name is not None:
        assumption.name = update_data.name

    if update_data.revenue_growth_rates is not None:
        assumption.set_revenue_growth_rates(update_data.revenue_growth_rates)

    if update_data.projection_years is not None:
        assumption.projection_years = update_data.projection_years

    if update_data.gross_margin is not None:
        assumption.gross_margin = update_data.gross_margin

    if update_data.operating_margin is not None:
        assumption.operating_margin = update_data.operating_margin

    if update_data.tax_rate is not None:
        assumption.tax_rate = update_data.tax_rate

    if update_data.wacc is not None:
        assumption.wacc = update_data.wacc

    if update_data.terminal_growth_rate is not None:
        assumption.terminal_growth_rate = update_data.terminal_growth_rate

    if update_data.capex_as_pct_revenue is not None:
        assumption.capex_as_pct_revenue = update_data.capex_as_pct_revenue

    if update_data.da_as_pct_revenue is not None:
        assumption.da_as_pct_revenue = update_data.da_as_pct_revenue

    if update_data.shares_outstanding is not None:
        assumption.shares_outstanding = update_data.shares_outstanding

    if update_data.net_debt is not None:
        assumption.net_debt = update_data.net_debt

    if update_data.is_active is not None:
        # If setting to active, deactivate all other assumption sets for this stock/user
        if update_data.is_active:
            # Get all other assumption sets and deactivate them
            result = await db.execute(
                select(AssumptionSet).where(
                    AssumptionSet.stock_id == assumption.stock_id,
                    AssumptionSet.user_id == current_user.id,
                    AssumptionSet.id != assumption.id,
                )
            )
            for other in result.scalars().all():
                other.is_active = False

        assumption.is_active = update_data.is_active

    await db.commit()
    await db.refresh(assumption)

    return db_to_response(assumption)


@router.delete("/{assumption_id}")
async def delete_assumption_set(
    assumption_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete an assumption set."""
    assumption = await get_assumption_set(assumption_id, db, current_user)

    await db.delete(assumption)
    await db.commit()

    return {"message": f"Assumption set '{assumption.name}' deleted successfully"}


@router.get("/{ticker}/model", response_model=ModelOutputResponse)
async def compute_model(
    ticker: str,
    assumption_id: Optional[str] = Query(None, description="Specific assumption set ID (default: active)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModelOutputResponse:
    """Compute financial projections using the ModelEngine.

    Uses the active assumption set by default, or a specific one if provided.
    """
    stock = await get_stock_by_ticker(ticker, db, current_user)

    # Get the assumption set to use
    if assumption_id:
        assumption = await get_assumption_set(assumption_id, db, current_user)
    else:
        # Get active assumption set
        result = await db.execute(
            select(AssumptionSet).where(
                AssumptionSet.stock_id == stock.id,
                AssumptionSet.user_id == current_user.id,
                AssumptionSet.is_active == True,
            )
        )
        assumption = result.scalar_one_or_none()
        if not assumption:
            raise ValidationError(
                "No active assumption set found. Please create an assumption set first.",
                errors=[]
            )

    # Fetch latest financials
    latest_income, latest_balance, latest_cashflow = await get_latest_financials(ticker)

    # Run the model engine
    engine = ModelEngine()
    model_output = engine.compute(
        assumptions=assumption,
        latest_income=latest_income,
        latest_balance=latest_balance,
        latest_cashflow=latest_cashflow,
    )

    return ModelOutputResponse(
        ticker=model_output.ticker,
        assumption_set_name=model_output.assumption_set_name,
        projection_years=model_output.projection_years,
        projections=[
            ProjectedFinancialsResponse(
                year=p.year,
                revenue=p.revenue,
                gross_profit=p.gross_profit,
                operating_income=p.operating_income,
                ebitda=p.ebitda,
                net_income=p.net_income,
                free_cash_flow=p.free_cash_flow,
                eps=p.eps,
                capex=p.capex,
                depreciation_amortization=p.depreciation_amortization,
            )
            for p in model_output.projections
        ],
        base_year_revenue=model_output.base_year_revenue,
        base_year=model_output.base_year,
    )


@router.get("/{ticker}/dcf", response_model=DCFResultResponse)
async def compute_dcf(
    ticker: str,
    assumption_id: Optional[str] = Query(None, description="Specific assumption set ID (default: active)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DCFResultResponse:
    """Compute DCF valuation using the DCFCalculator.

    Uses the active assumption set by default, or a specific one if provided.
    """
    stock = await get_stock_by_ticker(ticker, db, current_user)

    # Get the assumption set to use
    if assumption_id:
        assumption = await get_assumption_set(assumption_id, db, current_user)
    else:
        # Get active assumption set
        result = await db.execute(
            select(AssumptionSet).where(
                AssumptionSet.stock_id == stock.id,
                AssumptionSet.user_id == current_user.id,
                AssumptionSet.is_active == True,
            )
        )
        assumption = result.scalar_one_or_none()
        if not assumption:
            raise ValidationError(
                "No active assumption set found. Please create an assumption set first.",
                errors=[]
            )

    # Fetch latest financials
    latest_income, latest_balance, latest_cashflow = await get_latest_financials(ticker, current_user.settings)

    # Get current price
    prices = get_prices(current_user.settings)
    quote = await prices.get_quote(ticker)
    current_price = quote.price

    # Get shares outstanding and net debt
    shares_outstanding = assumption.shares_outstanding
    if shares_outstanding is None:
        if latest_income.shares_diluted:
            shares_outstanding = latest_income.shares_diluted
        elif latest_balance.shares_outstanding:
            shares_outstanding = latest_balance.shares_outstanding
        else:
            raise ValidationError("Shares outstanding not available", errors=[])

    net_debt = assumption.net_debt
    if net_debt is None:
        # Calculate from balance sheet: total debt - cash
        total_debt = (latest_balance.short_term_debt or 0) + (latest_balance.long_term_debt or 0)
        cash = latest_balance.cash_and_equivalents or 0
        net_debt = total_debt - cash

    # Run the model engine first
    engine = ModelEngine()
    model_output = engine.compute(
        assumptions=assumption,
        latest_income=latest_income,
        latest_balance=latest_balance,
        latest_cashflow=latest_cashflow,
    )

    # Calculate DCF
    calculator = DCFCalculator()
    dcf_result = calculator.calculate(
        model_output=model_output,
        assumptions=assumption,
        current_price=current_price,
        shares_outstanding=shares_outstanding,
        net_debt=net_debt,
    )

    return DCFResultResponse(
        ticker=dcf_result.ticker,
        assumption_set_name=dcf_result.assumption_set_name,
        enterprise_value=dcf_result.enterprise_value,
        equity_value=dcf_result.equity_value,
        per_share_value=dcf_result.per_share_value,
        terminal_value=dcf_result.terminal_value,
        pv_of_fcfs=dcf_result.pv_of_fcfs,
        pv_of_terminal=dcf_result.pv_of_terminal,
        upside_pct=dcf_result.upside_pct,
        wacc=dcf_result.wacc,
        terminal_growth_rate=dcf_result.terminal_growth_rate,
        current_price=dcf_result.current_price,
        projection_years=dcf_result.projection_years,
    )
