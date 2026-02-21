"""Watch items API endpoints — manage catalysts and monitoring items."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.stock import Stock
from app.models.user import User
from app.models.watch_item import WatchItem
from app.services.llm.router import LLMRouter
from app.services.thesis.watch import WatchService

router = APIRouter(prefix="/watch", tags=["watch"])


class WatchItemBase(BaseModel):
    """Base fields for watch items."""

    title: str = Field(..., description="Short item title")
    description: Optional[str] = Field(None, description="Details about the watch item")
    category: Optional[str] = Field(None, description="Category such as earnings or product")
    expected_date: Optional[date] = Field(None, description="Expected date")
    is_recurring: Optional[bool] = Field(False, description="Recurring indicator")
    potential_impact: Optional[str] = Field(None, description="Potential impact summary")
    impact_direction: Optional[str] = Field(None, description="positive/negative/mixed")
    affected_assumptions: list[str] = Field(default_factory=list)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class WatchItemCreate(WatchItemBase):
    """Request for creating a manual watch item."""

    status: Optional[str] = Field(None, description="active/triggered/dismissed")
    triggered_at: Optional[datetime] = Field(None, description="Trigger timestamp")
    trigger_outcome: Optional[str] = Field(None, description="Trigger outcome summary")
    generated_by: Optional[str] = Field(None, description="manual/ai")


class WatchItemTrigger(BaseModel):
    """Request to trigger a watch item."""

    trigger_outcome: Optional[str] = Field(None, description="Outcome summary")


class WatchItemResponse(WatchItemBase):
    """Watch item response schema."""

    id: str
    stock_id: str
    user_id: str
    status: str
    triggered_at: Optional[datetime]
    trigger_outcome: Optional[str]
    generated_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


async def get_stock_by_ticker(ticker: str, db: AsyncSession, user: User) -> Stock:
    """Get a stock by ticker, raising NotFoundError if missing."""
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)
    return stock


async def get_watch_item_by_id(
    watch_id: str, db: AsyncSession, user: User
) -> WatchItem:
    """Get watch item by ID, ensuring it belongs to the user."""
    try:
        watch_uuid = uuid.UUID(watch_id)
    except ValueError:
        raise NotFoundError("WatchItem", watch_id)

    result = await db.execute(
        select(WatchItem).where(
            WatchItem.id == watch_uuid,
            WatchItem.user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundError("WatchItem", watch_id)
    return item


def db_to_response(item: WatchItem) -> WatchItemResponse:
    """Convert database model to response schema."""
    return WatchItemResponse(
        id=str(item.id),
        stock_id=str(item.stock_id),
        user_id=str(item.user_id),
        title=item.title,
        description=item.description,
        category=item.category,
        expected_date=item.expected_date,
        is_recurring=item.is_recurring,
        potential_impact=item.potential_impact,
        impact_direction=item.impact_direction,
        affected_assumptions=item.get_affected_assumptions(),
        status=item.status,
        triggered_at=item.triggered_at,
        trigger_outcome=item.trigger_outcome,
        generated_by=item.generated_by,
        confidence=item.confidence,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/{ticker}/generate", response_model=list[WatchItemResponse])
async def generate_watch_items(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WatchItemResponse]:
    """Generate watch items using the LLM and persist them."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    llm_router = LLMRouter()
    service = WatchService(llm_router)

    items = await service.generate_watch_items(
        ticker=ticker.upper(),
        stock_id=stock.id,
        user_id=current_user.id,
        db=db,
        user_settings=current_user.settings,
    )

    return [db_to_response(item) for item in items]


@router.get("/{ticker}", response_model=list[WatchItemResponse])
async def list_watch_items(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WatchItemResponse]:
    """List active watch items for a stock."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    service = WatchService(LLMRouter())
    items = await service.get_active_items(
        stock_id=stock.id,
        user_id=current_user.id,
        db=db,
    )

    return [db_to_response(item) for item in items]


@router.post("/{ticker}", response_model=WatchItemResponse)
async def create_watch_item(
    ticker: str,
    item_data: WatchItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchItemResponse:
    """Create a manual watch item."""
    stock = await get_stock_by_ticker(ticker, db, current_user)

    item = WatchItem(
        stock_id=stock.id,
        user_id=current_user.id,
        title=item_data.title,
        description=item_data.description,
        category=item_data.category,
        expected_date=item_data.expected_date,
        is_recurring=bool(item_data.is_recurring),
        potential_impact=item_data.potential_impact,
        impact_direction=item_data.impact_direction,
        status=item_data.status or "active",
        triggered_at=item_data.triggered_at,
        trigger_outcome=item_data.trigger_outcome,
        generated_by=item_data.generated_by or "manual",
        confidence=item_data.confidence,
    )
    item.set_affected_assumptions(item_data.affected_assumptions)

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return db_to_response(item)


@router.put("/{watch_id}/trigger", response_model=WatchItemResponse)
async def trigger_watch_item(
    watch_id: str,
    payload: WatchItemTrigger,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchItemResponse:
    """Mark a watch item as triggered."""
    try:
        watch_uuid = uuid.UUID(watch_id)
    except ValueError:
        raise NotFoundError("WatchItem", watch_id)

    service = WatchService(LLMRouter())
    item = await service.trigger_item(
        watch_id=watch_uuid,
        user_id=current_user.id,
        outcome=payload.trigger_outcome,
        db=db,
    )

    return db_to_response(item)


@router.put("/{watch_id}/dismiss", response_model=WatchItemResponse)
async def dismiss_watch_item(
    watch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WatchItemResponse:
    """Dismiss a watch item."""
    try:
        watch_uuid = uuid.UUID(watch_id)
    except ValueError:
        raise NotFoundError("WatchItem", watch_id)

    service = WatchService(LLMRouter())
    item = await service.dismiss_item(
        watch_id=watch_uuid,
        user_id=current_user.id,
        db=db,
    )

    return db_to_response(item)


@router.delete("/{watch_id}")
async def delete_watch_item(
    watch_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a watch item."""
    item = await get_watch_item_by_id(watch_id, db, current_user)

    await db.delete(item)
    await db.commit()

    return {"message": f"Watch item '{item.title}' deleted successfully"}
