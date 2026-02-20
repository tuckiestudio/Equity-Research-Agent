"""Scenario API endpoints — manage valuation scenarios."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.scenario import Scenario
from app.models.stock import Stock
from app.models.user import User

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class ScenarioBase(BaseModel):
    """Base scenario fields."""

    name: str = Field(..., description="Scenario name")
    case_type: Optional[str] = Field(default=None, description="Case type (base/bull/bear)")
    probability: Optional[float] = Field(default=None, ge=0, le=1)
    revenue_growth_rate: Optional[float] = Field(default=None)
    operating_margin: Optional[float] = Field(default=None)
    wacc: Optional[float] = Field(default=None)
    terminal_growth_rate: Optional[float] = Field(default=None)
    dcf_per_share: Optional[float] = Field(default=None)
    comps_implied_pe: Optional[float] = Field(default=None)
    comps_implied_ev_ebitda: Optional[float] = Field(default=None)


class ScenarioCreate(ScenarioBase):
    """Schema for creating a scenario."""

    pass


class ScenarioUpdate(BaseModel):
    """Schema for updating a scenario."""

    name: Optional[str] = None
    case_type: Optional[str] = None
    probability: Optional[float] = Field(default=None, ge=0, le=1)
    revenue_growth_rate: Optional[float] = None
    operating_margin: Optional[float] = None
    wacc: Optional[float] = None
    terminal_growth_rate: Optional[float] = None
    dcf_per_share: Optional[float] = None
    comps_implied_pe: Optional[float] = None
    comps_implied_ev_ebitda: Optional[float] = None


class ScenarioResponse(ScenarioBase):
    """Scenario response schema."""

    id: str
    stock_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScenarioSummaryItem(BaseModel):
    """Scenario summary breakdown item."""

    id: str
    name: str
    probability: Optional[float]
    dcf_per_share: Optional[float]
    weighted_value: Optional[float]


class ScenarioSummaryResponse(BaseModel):
    """Scenario weighted summary response."""

    target_price: Optional[float]
    total_probability: float
    breakdown: list[ScenarioSummaryItem]


async def get_stock_by_ticker(
    ticker: str, db: AsyncSession, user: User
) -> Stock:
    """Get a stock by ticker, raising NotFoundError if missing."""
    result = await db.execute(
        select(Stock).where(Stock.ticker == ticker.upper())
    )
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)
    return stock


async def get_scenario_by_id(
    scenario_id: str, db: AsyncSession, user: User
) -> Scenario:
    """Get scenario by ID, ensuring it belongs to the user."""
    try:
        scenario_uuid = uuid.UUID(scenario_id)
    except ValueError:
        raise NotFoundError("Scenario", scenario_id)

    result = await db.execute(
        select(Scenario).where(
            Scenario.id == scenario_uuid,
            Scenario.user_id == user.id,
        )
    )
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise NotFoundError("Scenario", scenario_id)
    return scenario


def db_to_response(scenario: Scenario) -> ScenarioResponse:
    """Convert database model to response schema."""
    return ScenarioResponse(
        id=str(scenario.id),
        stock_id=str(scenario.stock_id),
        user_id=str(scenario.user_id),
        name=scenario.name,
        case_type=scenario.case_type,
        probability=scenario.probability,
        revenue_growth_rate=scenario.revenue_growth_rate,
        operating_margin=scenario.operating_margin,
        wacc=scenario.wacc,
        terminal_growth_rate=scenario.terminal_growth_rate,
        dcf_per_share=scenario.dcf_per_share,
        comps_implied_pe=scenario.comps_implied_pe,
        comps_implied_ev_ebitda=scenario.comps_implied_ev_ebitda,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


def compute_weighted_summary(
    scenarios: list[Scenario],
) -> ScenarioSummaryResponse:
    """Compute weighted target price summary for scenarios."""
    total_probability = 0.0
    weighted_sum = 0.0
    breakdown: list[ScenarioSummaryItem] = []

    for scenario in scenarios:
        probability = scenario.probability
        dcf_per_share = scenario.dcf_per_share
        weighted_value = None

        if probability is not None and probability > 0 and dcf_per_share is not None:
            weighted_value = probability * dcf_per_share
            total_probability += probability
            weighted_sum += weighted_value

        breakdown.append(
            ScenarioSummaryItem(
                id=str(scenario.id),
                name=scenario.name,
                probability=probability,
                dcf_per_share=dcf_per_share,
                weighted_value=weighted_value,
            )
        )

    target_price = (
        weighted_sum / total_probability if total_probability > 0 else None
    )

    return ScenarioSummaryResponse(
        target_price=target_price,
        total_probability=total_probability,
        breakdown=breakdown,
    )


@router.post("/{ticker}", response_model=ScenarioResponse)
async def create_scenario(
    ticker: str,
    scenario_data: ScenarioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioResponse:
    """Create a new scenario for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    scenario = Scenario(
        stock_id=stock.id,
        user_id=current_user.id,
        name=scenario_data.name,
        case_type=scenario_data.case_type,
        probability=scenario_data.probability,
        revenue_growth_rate=scenario_data.revenue_growth_rate,
        operating_margin=scenario_data.operating_margin,
        wacc=scenario_data.wacc,
        terminal_growth_rate=scenario_data.terminal_growth_rate,
        dcf_per_share=scenario_data.dcf_per_share,
        comps_implied_pe=scenario_data.comps_implied_pe,
        comps_implied_ev_ebitda=scenario_data.comps_implied_ev_ebitda,
    )

    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)

    return db_to_response(scenario)


@router.get("/{ticker}", response_model=list[ScenarioResponse])
async def list_scenarios(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScenarioResponse]:
    """List scenarios for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    result = await db.execute(
        select(Scenario)
        .where(
            Scenario.stock_id == stock.id,
            Scenario.user_id == current_user.id,
        )
        .order_by(Scenario.created_at.desc())
    )
    scenarios = result.scalars().all()

    return [db_to_response(scenario) for scenario in scenarios]


@router.get("/{ticker}/summary", response_model=ScenarioSummaryResponse)
async def get_scenario_summary(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioSummaryResponse:
    """Get weighted scenario summary for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    result = await db.execute(
        select(Scenario)
        .where(
            Scenario.stock_id == stock.id,
            Scenario.user_id == current_user.id,
        )
        .order_by(Scenario.created_at.desc())
    )
    scenarios = result.scalars().all()

    return compute_weighted_summary(list(scenarios))


@router.put("/{scenario_id}", response_model=ScenarioResponse)
async def update_scenario(
    scenario_id: str,
    update_data: ScenarioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ScenarioResponse:
    """Update an existing scenario."""
    scenario = await get_scenario_by_id(scenario_id, db, current_user)

    if update_data.name is not None:
        scenario.name = update_data.name
    if update_data.case_type is not None:
        scenario.case_type = update_data.case_type
    if update_data.probability is not None:
        scenario.probability = update_data.probability
    if update_data.revenue_growth_rate is not None:
        scenario.revenue_growth_rate = update_data.revenue_growth_rate
    if update_data.operating_margin is not None:
        scenario.operating_margin = update_data.operating_margin
    if update_data.wacc is not None:
        scenario.wacc = update_data.wacc
    if update_data.terminal_growth_rate is not None:
        scenario.terminal_growth_rate = update_data.terminal_growth_rate
    if update_data.dcf_per_share is not None:
        scenario.dcf_per_share = update_data.dcf_per_share
    if update_data.comps_implied_pe is not None:
        scenario.comps_implied_pe = update_data.comps_implied_pe
    if update_data.comps_implied_ev_ebitda is not None:
        scenario.comps_implied_ev_ebitda = update_data.comps_implied_ev_ebitda

    await db.commit()
    await db.refresh(scenario)

    return db_to_response(scenario)


@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a scenario."""
    scenario = await get_scenario_by_id(scenario_id, db, current_user)

    await db.delete(scenario)
    await db.commit()

    return {"message": f"Scenario '{scenario.name}' deleted successfully"}
