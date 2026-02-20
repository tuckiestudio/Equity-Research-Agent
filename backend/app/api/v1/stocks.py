"""
Stocks API endpoints — search, fetch, detail.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.stock import Stock
from app.models.user import User

router = APIRouter(prefix="/stocks", tags=["stocks"])


# --- Response Schemas ---

class StockResponse(BaseModel):
    id: str
    ticker: str
    company_name: str
    exchange: Optional[str]
    sector: Optional[str]
    industry: Optional[str]

    model_config = {"from_attributes": True}


class StockDetailResponse(StockResponse):
    """Stock with live data (price, ratios, etc.) — populated from data providers."""
    pass  # Extended in Phase 3 when provider data is wired up


# --- Endpoints ---

@router.get("/search")
async def search_stocks(
    q: str = Query(min_length=1, description="Search query (ticker or name)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StockResponse]:
    """Search stocks by ticker or company name."""
    query = select(Stock).where(
        Stock.ticker.ilike(f"%{q}%") | Stock.company_name.ilike(f"%{q}%")
    ).limit(20)
    result = await db.execute(query)
    stocks = result.scalars().all()
    return [
        StockResponse(
            id=str(s.id), ticker=s.ticker, company_name=s.company_name,
            exchange=s.exchange, sector=s.sector, industry=s.industry,
        )
        for s in stocks
    ]


@router.get("/{ticker}")
async def get_stock(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StockDetailResponse:
    """Get stock details by ticker."""
    result = await db.execute(select(Stock).where(Stock.ticker == ticker.upper()))
    stock = result.scalar_one_or_none()
    if not stock:
        raise NotFoundError("Stock", ticker)
    return StockDetailResponse(
        id=str(stock.id), ticker=stock.ticker, company_name=stock.company_name,
        exchange=stock.exchange, sector=stock.sector, industry=stock.industry,
    )
