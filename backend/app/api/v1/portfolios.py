"""
Portfolios API endpoints — CRUD, add/remove stocks.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.errors import AppError, NotFoundError
from app.db.session import get_db
from app.models.stock import Portfolio, Stock, portfolio_stocks
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
    from app.services.permissions import check_limits, Tier

    # Check tier limit for number of portfolios
    max_portfolios = check_limits(current_user, "portfolios")
    if max_portfolios != -1:  # -1 means unlimited
        # Count existing portfolios
        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == current_user.id)
        )
        existing_portfolios = result.scalars().all()
        if len(existing_portfolios) >= max_portfolios:
            raise AppError(
                status_code=403,
                code="TIER_LIMIT_EXCEEDED",
                detail=f"Your tier allows a maximum of {max_portfolios} portfolios. "
                       f"Please upgrade to create more.",
            )

    portfolio = Portfolio(name=body.name, user_id=current_user.id)
    db.add(portfolio)
    await db.flush()
    return PortfolioResponse(id=str(portfolio.id), name=portfolio.name, stock_count=0)


@router.patch("/{portfolio_id}")
async def update_portfolio(
    portfolio_id: str,
    body: CreatePortfolioRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioResponse:
    """Update portfolio name."""
    try:
        pid = uuid.UUID(portfolio_id)
    except ValueError:
        raise NotFoundError("Portfolio", portfolio_id)

    result = await db.execute(
        select(Portfolio).where(Portfolio.id == pid, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise NotFoundError("Portfolio", portfolio_id)

    portfolio.name = body.name
    await db.commit()

    # Count stocks without loading them (avoiding async issue)
    stock_count_result = await db.execute(
        select(Stock)
        .join(portfolio_stocks, and_(
            Stock.id == portfolio_stocks.c.stock_id,
            portfolio_stocks.c.portfolio_id == pid,
        ))
        .where(portfolio_stocks.c.is_archived == False)
    )
    stock_count = len(stock_count_result.scalars().all())

    return PortfolioResponse(id=str(portfolio.id), name=portfolio.name, stock_count=stock_count)


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PortfolioDetailResponse:
    """Get portfolio with active (non-archived) stocks."""
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

    # Filter to only non-archived stocks by checking the association table
    result = await db.execute(
        select(Stock)
        .join(portfolio_stocks, and_(
            Stock.id == portfolio_stocks.c.stock_id,
            portfolio_stocks.c.portfolio_id == pid,
        ))
        .where(
            and_(
                portfolio_stocks.c.portfolio_id == pid,
                portfolio_stocks.c.is_archived == False,
            )
        )
    )
    active_stocks = result.scalars().all()

    stocks = [
        {"id": str(s.id), "ticker": s.ticker, "company_name": s.company_name,
         "exchange": s.exchange, "sector": s.sector}
        for s in active_stocks
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
    await db.commit()
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


@router.post("/{portfolio_id}/stocks/{ticker}/archive", status_code=200)
async def archive_stock(
    portfolio_id: str,
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Archive a stock in a portfolio. The stock is hidden from the main view but all data is preserved."""
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

    ticker_upper = ticker.upper()
    stock = next((s for s in portfolio.stocks if s.ticker == ticker_upper), None)
    if not stock:
        raise NotFoundError("Stock in portfolio", ticker)

    # Check if already archived
    result = await db.execute(
        select(portfolio_stocks.c.is_archived)
        .where(
            and_(
                portfolio_stocks.c.portfolio_id == pid,
                portfolio_stocks.c.stock_id == stock.id,
            )
        )
    )
    assoc = result.one_or_none()
    if assoc and assoc.is_archived:
        raise AppError(status_code=409, code="STOCK_ALREADY_ARCHIVED",
                       detail=f"{ticker_upper} is already archived")

    # Update the association table to mark as archived
    await db.execute(
        update(portfolio_stocks)
        .where(
            and_(
                portfolio_stocks.c.portfolio_id == pid,
                portfolio_stocks.c.stock_id == stock.id,
            )
        )
        .values(is_archived=True, archived_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return {"message": f"Archived {ticker_upper} from portfolio '{portfolio.name}'"}


@router.delete("/{portfolio_id}/stocks/{ticker}/archive", status_code=200)
async def restore_stock(
    portfolio_id: str,
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Restore an archived stock back to the active portfolio view."""
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

    ticker_upper = ticker.upper()
    stock = next((s for s in portfolio.stocks if s.ticker == ticker_upper), None)
    if not stock:
        raise NotFoundError("Stock in portfolio", ticker)

    # Check if not archived
    result = await db.execute(
        select(portfolio_stocks.c.is_archived)
        .where(
            and_(
                portfolio_stocks.c.portfolio_id == pid,
                portfolio_stocks.c.stock_id == stock.id,
            )
        )
    )
    assoc = result.one_or_none()
    if assoc and not assoc.is_archived:
        raise AppError(status_code=409, code="STOCK_NOT_ARCHIVED",
                       detail=f"{ticker_upper} is not archived")

    # Update the association table to mark as not archived
    await db.execute(
        update(portfolio_stocks)
        .where(
            and_(
                portfolio_stocks.c.portfolio_id == pid,
                portfolio_stocks.c.stock_id == stock.id,
            )
        )
        .values(is_archived=False, archived_at=None)
    )
    await db.commit()

    return {"message": f"Restored {ticker_upper} to portfolio '{portfolio.name}'"}


@router.get("/{portfolio_id}/archived-stocks")
async def get_archived_stocks(
    portfolio_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get all archived stocks for a portfolio."""
    try:
        pid = uuid.UUID(portfolio_id)
    except ValueError:
        raise NotFoundError("Portfolio", portfolio_id)

    # Get portfolio with archived stocks
    result = await db.execute(
        select(Stock)
        .join(portfolio_stocks, Stock.id == portfolio_stocks.c.stock_id)
        .where(
            and_(
                portfolio_stocks.c.portfolio_id == pid,
                portfolio_stocks.c.is_archived == True,
            )
        )
    )
    archived_stocks = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "ticker": s.ticker,
            "company_name": s.company_name,
            "exchange": s.exchange,
            "sector": s.sector,
        }
        for s in archived_stocks
    ]
