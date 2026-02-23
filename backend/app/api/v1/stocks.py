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
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    current_price: Optional[float] = None
    change_percent: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    ev_ebitda: Optional[float] = None
    dividend_yield: Optional[float] = None
    description: Optional[str] = None


# --- Endpoints ---

@router.get("/search")
async def search_stocks(
    q: str = Query(min_length=1, description="Search query (ticker or name)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StockResponse]:
    """Search stocks by ticker or company name. Falls back to yfinance if no local results."""
    query = select(Stock).where(
        Stock.ticker.ilike(f"%{q}%") | Stock.company_name.ilike(f"%{q}%")
    ).limit(20)
    result = await db.execute(query)
    stocks = result.scalars().all()

    # If no local results, try profile provider's search
    if not stocks:
        from app.services.data.registry import get_profiles
        try:
            profiles = get_profiles(current_user.settings)
            # Use search_ticker to find matching stocks
            search_results = await profiles.search_ticker(q)

            for result in search_results:
                # Check if stock already exists in DB
                existing = await db.execute(select(Stock).where(Stock.ticker == result.ticker))
                stock = existing.scalar_one_or_none()

                if not stock:
                    # Get full profile for new stocks
                    try:
                        profile = await profiles.get_company_profile(result.ticker)
                        stock = Stock(
                            ticker=result.ticker,
                            company_name=profile.company_name or result.name,
                            exchange=profile.exchange,
                            sector=profile.sector,
                            industry=profile.industry,
                        )
                    except Exception:
                        stock = Stock(
                            ticker=result.ticker,
                            company_name=result.name,
                            exchange=result.exchange,
                        )
                    db.add(stock)

            await db.flush()

            # Re-query to get all stocks
            result = await db.execute(
                select(Stock).where(
                    Stock.ticker.ilike(f"%{q}%") | Stock.company_name.ilike(f"%{q}%")
                ).limit(20)
            )
            stocks = result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to search for {q}: {e}")

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

    # Fetch live data from providers
    from app.services.data.registry import get_fundamentals, get_prices, get_profiles
    
    current_price = None
    change_percent = None
    market_cap = None
    pe_ratio = None
    ev_ebitda = None
    dividend_yield = None
    description = None

    try:
        prices = get_prices(current_user.settings)
        quote = await prices.get_quote(ticker.upper())
        current_price = quote.price
        change_percent = quote.change_percent
        market_cap = quote.market_cap
    except Exception as e:
        logger.error(f"Failed to fetch price for {ticker}: {e}")

    try:
        profiles = get_profiles(current_user.settings)
        profile = await profiles.get_company_profile(ticker.upper())
        description = profile.description
    except Exception as e:
        logger.error(f"Failed to fetch profile for {ticker}: {e}")

    try:
        fundamentals = get_fundamentals(current_user.settings)
        ratios = await fundamentals.get_financial_ratios(ticker.upper())
        pe_ratio = ratios.pe_ratio
        ev_ebitda = ratios.ev_to_ebitda
        dividend_yield = ratios.dividend_yield
    except Exception as e:
        logger.error(f"Failed to fetch ratios for {ticker}: {e}")

    return StockDetailResponse(
        id=str(stock.id),
        ticker=stock.ticker,
        company_name=stock.company_name,
        exchange=stock.exchange,
        sector=stock.sector,
        industry=stock.industry,
        current_price=current_price,
        change_percent=change_percent,
        market_cap=market_cap,
        pe_ratio=pe_ratio,
        ev_ebitda=ev_ebitda,
        dividend_yield=dividend_yield,
        description=description,
    )
