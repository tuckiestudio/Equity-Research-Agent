"""
Portfolios API endpoints — CRUD, add/remove stocks.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.errors import AppError, NotFoundError
from app.db.session import get_db
from app.models.stock import Portfolio, Stock
from app.models.user import User

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


# --- Request/Response Schemas ---

class CreatePortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class PortfolioResponse(BaseModel):
    id: str
    name: str
    stock_count: int

    model_config = {"from_attributes": True}


class PortfolioDetailResponse(PortfolioResponse):
    stocks: list[dict]


class AddStockRequest(BaseModel):
    ticker: str = Field(min_length=1, max_length=20)


# --- Endpoints ---

@router.get("")
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PortfolioResponse]:
    """List all portfolios for current user."""
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.stocks))
        .where(Portfolio.user_id == current_user.id)
    )
    portfolios = result.scalars().all()
    return [
        PortfolioResponse(id=str(p.id), name=p.name, stock_count=len(p.stocks))
        for p in portfolios
    ]


@router.post("", status_code=201)
async def create_portfolio(
    body: CreatePortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """Create a new portfolio."""
    portfolio = Portfolio(name=body.name, user_id=current_user.id)
    db.add(portfolio)
    await db.flush()
    return PortfolioResponse(id=str(portfolio.id), name=portfolio.name, stock_count=0)


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioDetailResponse:
    """Get portfolio with stocks."""
    try:
        pid = uuid.UUID(portfolio_id)
    except ValueError:
        raise NotFoundError("Portfolio", portfolio_id)

    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.stocks))
        .where(Portfolio.id == pid, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise NotFoundError("Portfolio", portfolio_id)

    stocks = [
        {"id": str(s.id), "ticker": s.ticker, "company_name": s.company_name,
         "exchange": s.exchange, "sector": s.sector}
        for s in portfolio.stocks
    ]
    return PortfolioDetailResponse(
        id=str(portfolio.id), name=portfolio.name,
        stock_count=len(stocks), stocks=stocks,
    )


@router.post("/{portfolio_id}/stocks", status_code=201)
async def add_stock_to_portfolio(
    portfolio_id: str,
    body: AddStockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add a stock to a portfolio. Creates the stock record if needed."""
    try:
        pid = uuid.UUID(portfolio_id)
    except ValueError:
        raise NotFoundError("Portfolio", portfolio_id)

    # Get portfolio
    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.stocks))
        .where(Portfolio.id == pid, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise NotFoundError("Portfolio", portfolio_id)

    ticker = body.ticker.upper()

    # Check if already in portfolio
    if any(s.ticker == ticker for s in portfolio.stocks):
        raise AppError(status_code=409, code="STOCK_ALREADY_IN_PORTFOLIO",
                         detail=f"{ticker} is already in this portfolio")

    # Get or create stock
    result = await db.execute(select(Stock).where(Stock.ticker == ticker))
    stock = result.scalar_one_or_none()
    if not stock:
        # Create stock record (will be enriched by data providers later)
        stock = Stock(ticker=ticker, company_name=ticker)
        db.add(stock)
        await db.flush()

    portfolio.stocks.append(stock)
    return {"message": f"Added {ticker} to portfolio '{portfolio.name}'"}


@router.delete("/{portfolio_id}/stocks/{ticker}", status_code=200)
async def remove_stock_from_portfolio(
    portfolio_id: str,
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a stock from a portfolio."""
    try:
        pid = uuid.UUID(portfolio_id)
    except ValueError:
        raise NotFoundError("Portfolio", portfolio_id)

    result = await db.execute(
        select(Portfolio)
        .options(selectinload(Portfolio.stocks))
        .where(Portfolio.id == pid, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise NotFoundError("Portfolio", portfolio_id)

    ticker_upper = ticker.upper()
    stock = next((s for s in portfolio.stocks if s.ticker == ticker_upper), None)
    if not stock:
        raise NotFoundError("Stock in portfolio", ticker)

    portfolio.stocks.remove(stock)
    return {"message": f"Removed {ticker_upper} from portfolio '{portfolio.name}'"}
