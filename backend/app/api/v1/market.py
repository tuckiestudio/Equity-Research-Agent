"""
Market API endpoints — market overview, indices, top movers.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


# --- Response Schemas ---

class MarketIndex(BaseModel):
    """Market index information."""
    name: str
    symbol: str
    price: float
    change: float
    change_percent: float
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    previous_close: Optional[float] = None


class MarketMover(BaseModel):
    """Top gaining or losing stock."""
    ticker: str
    company_name: str
    price: float
    change: float
    change_percent: float
    volume: Optional[int] = None
    sector: Optional[str] = None


class MarketSummary(BaseModel):
    """Overall market summary."""
    indices: List[MarketIndex]
    top_gainers: List[MarketMover]
    top_losers: List[MarketMover]
    most_active: List[MarketMover]


class NewsItem(BaseModel):
    """News article summary."""
    headline: str
    source: str
    url: Optional[str] = None
    published_at: Optional[str] = None
    sentiment: Optional[str] = None


class MarketNewsResponse(BaseModel):
    """Market news response."""
    news: List[NewsItem]


# --- Helper Functions ---

async def _fetch_market_indices() -> List[MarketIndex]:
    """Fetch major market indices using yfinance."""
    import yfinance as yf
    import asyncio

    indices = {
        "S&P 500": "^GSPC",
        "Dow Jones": "^DJI",
        "NASDAQ": "^IXIC",
        "Russell 2000": "^RUT",
        "VIX": "^VIX",
    }

    async def fetch_index(name: str, symbol: str) -> Optional[MarketIndex]:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            current = info.get("regularMarketPrice")
            if current is None:
                return None

            prev_close = info.get("previousClose", 0)
            change = current - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            return MarketIndex(
                name=name,
                symbol=symbol,
                price=float(current),
                change=float(change),
                change_percent=float(change_pct),
                high=info.get("regularMarketDayHigh"),
                low=info.get("regularMarketDayLow"),
                open=info.get("regularMarketOpen"),
                previous_close=prev_close,
            )
        except Exception as e:
            logger.error(f"Failed to fetch index {symbol}: {e}")
            return None

    # Fetch all indices concurrently
    tasks = [fetch_index(name, symbol) for name, symbol in indices.items()]
    results = await asyncio.gather(*tasks)

    return [r for r in results if r is not None]


async def _fetch_top_movers(direction: str = "gainers", limit: int = 5) -> List[MarketMover]:
    """Fetch top gainers or losers using yfinance."""
    import yfinance as yf
    import asyncio

    # Popular ETFs/stocks to check (simplified approach)
    # In production, use a screener API
    symbols_to_check = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
        "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC",
        "NFLX", "ADBE", "CRM", "PYPL", "INTC", "AMD", "COIN", "PLTR",
    ]

    async def fetch_stock(ticker_str: str) -> Optional[MarketMover]:
        try:
            ticker = yf.Ticker(ticker_str)
            info = ticker.info

            price = info.get("regularMarketPrice")
            if price is None:
                return None

            prev_close = info.get("previousClose", 0)
            if prev_close == 0:
                return None

            change = price - prev_close
            change_pct = (change / prev_close * 100)

            # Filter by direction
            if direction == "gainers" and change_pct <= 0:
                return None
            if direction == "losers" and change_pct >= 0:
                return None

            return MarketMover(
                ticker=ticker_str,
                company_name=info.get("longName", ticker_str),
                price=float(price),
                change=float(change),
                change_percent=float(change_pct),
                volume=info.get("regularMarketVolume"),
                sector=info.get("sector"),
            )
        except Exception as e:
            logger.error(f"Failed to fetch stock {ticker_str}: {e}")
            return None

    # Fetch all stocks concurrently
    tasks = [fetch_stock(s) for s in symbols_to_check]
    results = await asyncio.gather(*tasks)

    # Filter out None and sort by change percent
    valid_results = [r for r in results if r is not None]
    valid_results.sort(key=lambda x: x.change_percent, reverse=(direction == "gainers"))

    return valid_results[:limit]


async def _fetch_most_active(limit: int = 5) -> List[MarketMover]:
    """Fetch most active stocks by volume."""
    import yfinance as yf
    import asyncio

    symbols_to_check = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
        "JPM", "V", "JNJ", "WMT", "PG", "MA", "UNH", "HD", "DIS", "BAC",
        "NFLX", "ADBE", "CRM", "PYPL", "INTC", "AMD", "COIN", "PLTR",
        "SPY", "QQQ", "IWM", "DIA",
    ]

    async def fetch_stock(ticker_str: str) -> Optional[MarketMover]:
        try:
            ticker = yf.Ticker(ticker_str)
            info = ticker.info

            price = info.get("regularMarketPrice")
            volume = info.get("regularMarketVolume")

            if price is None or volume is None:
                return None

            prev_close = info.get("previousClose", 0)
            change = price - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            return MarketMover(
                ticker=ticker_str,
                company_name=info.get("longName", ticker_str),
                price=float(price),
                change=float(change),
                change_percent=float(change_pct),
                volume=volume,
                sector=info.get("sector"),
            )
        except Exception as e:
            logger.error(f"Failed to fetch stock {ticker_str}: {e}")
            return None

    # Fetch all stocks concurrently
    tasks = [fetch_stock(s) for s in symbols_to_check]
    results = await asyncio.gather(*tasks)

    # Filter out None and sort by volume
    valid_results = [r for r in results if r is not None and r.volume]
    valid_results.sort(key=lambda x: x.volume, reverse=True)

    return valid_results[:limit]


# --- Endpoints ---

@router.get("/summary")
async def get_market_summary(
    current_user: User = Depends(get_current_user),
) -> MarketSummary:
    """Get overall market summary including indices and top movers."""
    indices_task = asyncio.create_task(_fetch_market_indices())
    gainers_task = asyncio.create_task(_fetch_top_movers("gainers"))
    losers_task = asyncio.create_task(_fetch_top_movers("losers"))
    active_task = asyncio.create_task(_fetch_most_active())

    indices, gainers, losers, most_active = await asyncio.gather(
        indices_task, gainers_task, losers_task, active_task
    )

    return MarketSummary(
        indices=indices,
        top_gainers=gainers,
        top_losers=losers,
        most_active=most_active,
    )


@router.get("/indices")
async def get_market_indices(
    current_user: User = Depends(get_current_user),
) -> List[MarketIndex]:
    """Get major market indices."""
    return await _fetch_market_indices()


@router.get("/movers")
async def get_market_movers(
    direction: str = Query("all", description="gainers, losers, or all"),
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get top gaining or losing stocks."""
    if direction == "gainers":
        gainers = await _fetch_top_movers("gainers", limit)
        return {"gainers": gainers}
    elif direction == "losers":
        losers = await _fetch_top_movers("losers", limit)
        return {"losers": losers}
    else:
        gainers, losers = await asyncio.gather(
            _fetch_top_movers("gainers", limit),
            _fetch_top_movers("losers", limit),
        )
        return {"gainers": gainers, "losers": losers}


@router.get("/news")
async def get_market_news(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
) -> MarketNewsResponse:
    """Get general market news."""
    # For now, return a simple response
    # In production, integrate with a news API for market-wide news
    from app.services.data.registry import get_news

    try:
        # Get news for a market proxy (SPY ETF)
        news_provider = get_news(current_user.settings)
        news_items = await news_provider.get_news("SPY", limit=limit)

        return MarketNewsResponse(
            news=[
                NewsItem(
                    headline=item.headline,
                    source=item.source_name,
                    url=item.source_url,
                    published_at=item.published_at.isoformat() if item.published_at else None,
                    sentiment=item.sentiment_label,
                )
                for item in news_items[:limit]
            ]
        )
    except Exception as e:
        logger.error(f"Failed to fetch market news: {e}")
        # Return empty list if news provider fails
        return MarketNewsResponse(news=[])
