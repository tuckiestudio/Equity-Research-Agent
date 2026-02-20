"""Assumption waterfall API endpoint."""
from __future__ import annotations

import copy
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError, ValidationError
from app.db.session import get_db
from app.models.assumption import AssumptionSet
from app.models.stock import Stock
from app.models.user import User
from app.services.data.registry import get_fundamentals, get_prices
from app.services.model.dcf import DCFCalculator
from app.services.model.engine import ModelEngine

router = APIRouter(prefix="/waterfall", tags=["waterfall"])


class WaterfallItem(BaseModel):
    """Single assumption tweak result."""

    assumption: str
    base_value: Optional[float] = None
    tweaked_value: Optional[float] = None
    base_per_share: float
    tweaked_per_share: float
    impact_pct: float


class WaterfallResponse(BaseModel):
    """Response for waterfall endpoint."""

    ticker: str
    assumption_set_id: str
    base_per_share: float
    items: list[WaterfallItem]


async def get_stock_by_ticker(ticker: str, db: AsyncSession, user: User) -> Stock:
    """Get a stock by ticker, raising NotFoundError if missing."""
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
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


async def get_latest_financials(ticker: str):
    """Fetch the latest financials for a stock."""
    fundamentals = get_fundamentals()

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


async def resolve_assumption(
    stock: Stock,
    assumption_id: Optional[str],
    current_user: User,
    db: AsyncSession,
) -> AssumptionSet:
    """Resolve the assumption set to use for the waterfall."""
    if assumption_id:
        return await get_assumption_set(assumption_id, db, current_user)

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
            errors=[],
        )
    return assumption


def compute_per_share(
    assumption: AssumptionSet,
    latest_income,
    latest_balance,
    latest_cashflow,
    current_price: float,
) -> float:
    """Compute per-share value for a given assumption set."""
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
        total_debt = (latest_balance.short_term_debt or 0) + (latest_balance.long_term_debt or 0)
        cash = latest_balance.cash_and_equivalents or 0
        net_debt = total_debt - cash

    engine = ModelEngine()
    model_output = engine.compute(
        assumptions=assumption,
        latest_income=latest_income,
        latest_balance=latest_balance,
        latest_cashflow=latest_cashflow,
    )

    calculator = DCFCalculator()
    result = calculator.calculate(
        model_output=model_output,
        assumptions=assumption,
        current_price=current_price,
        shares_outstanding=shares_outstanding,
        net_debt=net_debt,
    )

    return result.per_share_value


@router.get("/{ticker}", response_model=WaterfallResponse)
async def get_waterfall(
    ticker: str,
    assumption_id: Optional[str] = Query(None, description="Specific assumption set ID (default: active)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaterfallResponse:
    """Compute a DCF assumption waterfall for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)
    assumption = await resolve_assumption(stock, assumption_id, current_user, db)

    latest_income, latest_balance, latest_cashflow = await get_latest_financials(ticker)

    prices = get_prices()
    quote = await prices.get_quote(ticker)
    current_price = quote.price

    base_per_share = compute_per_share(
        assumption,
        latest_income,
        latest_balance,
        latest_cashflow,
        current_price,
    )

    items: list[WaterfallItem] = []

    tweaks = [
        "revenue_growth_rates",
        "operating_margin",
        "wacc",
        "terminal_growth_rate",
        "capex_as_pct_revenue",
        "tax_rate",
    ]

    for field in tweaks:
        tweaked = copy.deepcopy(assumption)
        base_value = None
        tweaked_value = None

        if field == "revenue_growth_rates":
            growth_rates = tweaked.get_revenue_growth_rates()
            base_value = sum(growth_rates) / len(growth_rates) if growth_rates else None
            tweaked_rates = [rate * 1.10 for rate in growth_rates]
            tweaked_value = sum(tweaked_rates) / len(tweaked_rates) if tweaked_rates else None
            tweaked.set_revenue_growth_rates(tweaked_rates)
        else:
            base_value = getattr(tweaked, field)
            if base_value is None:
                continue
            tweaked_value = base_value * 1.10
            setattr(tweaked, field, tweaked_value)

        try:
            tweaked_per_share = compute_per_share(
                tweaked,
                latest_income,
                latest_balance,
                latest_cashflow,
                current_price,
            )
        except (ValueError, ValidationError):
            continue

        impact_pct = (tweaked_per_share - base_per_share) / base_per_share if base_per_share != 0 else 0.0

        items.append(
            WaterfallItem(
                assumption=field,
                base_value=base_value,
                tweaked_value=tweaked_value,
                base_per_share=base_per_share,
                tweaked_per_share=tweaked_per_share,
                impact_pct=impact_pct,
            )
        )

    return WaterfallResponse(
        ticker=stock.ticker,
        assumption_set_id=str(assumption.id),
        base_per_share=base_per_share,
        items=items,
    )
