"""
Finnhub data provider implementation.

https://finnhub.io/docs/api

Implements PriceProvider, ProfileProvider, and NewsProvider protocols.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

from app.core.errors import ProviderError, RateLimitError
from app.schemas.financial import (
    CompanyProfile,
    NewsItem,
    PriceBar,
    StockQuote,
    TickerSearchResult,
)


class FinnhubProvider:
    """Finnhub.io API client for stocks, forex, crypto, and news."""

    provider_name = "finnhub"

    BASE_URL = "https://finnhub.io/api/v1"
    RATE_LIMIT_CALLS = 60  # Free tier: 60 calls/minute
    RATE_LIMIT_SECONDS = 60

    def __init__(self, api_key: str = "") -> None:
        """
        Initialize Finnhub client.

        Args:
            api_key: Finnhub API key from https://finnhub.io/
        """
        if not api_key:
            raise ValueError("Finnhub API key is required")
        self._api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(10)  # Concurrent request limit

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                params={"token": self._api_key},
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        Make an authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments passed to httpx

        Returns:
            Parsed JSON response

        Raises:
            ProviderError: API request failed
            RateLimitError: Rate limit exceeded
        """
        async with self._semaphore:
            client = await self._get_client()
            url = endpoint

            try:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()

                data = response.json()

                # Finnhub returns {"s": "error", "errmsg": "...} on error
                if isinstance(data, dict) and data.get("s") == "error":
                    raise ProviderError(
                        "finnhub", data.get("errmsg", "Unknown error")
                    )

                return data

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise RateLimitError("finnhub")
                raise ProviderError(
                    "finnhub", f"HTTP {e.response.status_code}: {e.response.text}"
                )
            except httpx.RequestError as e:
                raise ProviderError("finnhub", f"Request failed: {e}")

    # ========================================================================
    # PriceProvider Implementation
    # ========================================================================

    async def get_quote(self, ticker: str) -> StockQuote:
        """
        Get real-time stock quote.

        Endpoint: /quote?symbol=TICKER

        Args:
            ticker: Stock symbol (e.g., "AAPL")

        Returns:
            StockQuote with current price and change
        """
        data = await self._request("GET", "/quote", params={"symbol": ticker})

        # Finnhub returns: c=current price, d=change, dp=percent change,
        # h=high, l=low, o=open, pc=previous close, t=timestamp
        current = data.get("c")
        if current is None:
            raise ProviderError("finnhub", f"No quote data for {ticker}")

        return StockQuote(
            ticker=ticker,
            price=float(current),
            change=float(data.get("d", 0)) if data.get("d") is not None else None,
            change_percent=float(data.get("dp", 0)) if data.get("dp") is not None else None,
            volume=int(data.get("v", 0)) if data.get("v") else None,
            high=float(data.get("h")) if data.get("h") else None,
            low=float(data.get("l")) if data.get("l") else None,
            open=float(data.get("o")) if data.get("o") else None,
            previous_close=float(data.get("pc")) if data.get("pc") else None,
            timestamp=datetime.fromtimestamp(data.get("t", 0)) if data.get("t") else datetime.utcnow(),
            source="finnhub",
        )

    async def get_historical_prices(
        self,
        ticker: str,
        start: date,
        end: date,
        interval: str = "1d",
    ) -> list[PriceBar]:
        """
        Get historical OHLCV price bars.

        Endpoint: /stock/candle?symbol=TICKER&resolution=D&from=UNIX&to=UNIX

        Args:
            ticker: Stock symbol
            start: Start date
            end: End date
            interval: Bar width (1d, 1w, 1h, etc.)

        Returns:
            List of PriceBar objects
        """
        # Finnhub uses Unix timestamps
        from_ts = int(start.strftime("%s"))
        to_ts = int(end.strftime("%s"))

        # Map interval to Finnhub resolution
        resolution_map = {
            "1d": "D",
            "1w": "W",
            "1M": "M",
            "1h": "60",
            "15m": "15",
            "5m": "5",
            "1m": "1",
        }
        resolution = resolution_map.get(interval, "D")

        data = await self._request(
            "GET",
            "/stock/candle",
            params={
                "symbol": ticker,
                "resolution": resolution,
                "from": from_ts,
                "to": to_ts,
            },
        )

        # Finnhub returns: s=status (ok/no_data), c=close, h=high, l=low, o=open, t=timestamps, v=volumes
        if data.get("s") == "no_data":
            return []

        timestamps = data.get("t", [])
        opens = data.get("o", [])
        highs = data.get("h", [])
        lows = data.get("l", [])
        closes = data.get("c", [])
        volumes = data.get("v", [])

        price_bars = []
        for i, ts in enumerate(timestamps):
            price_bars.append(
                PriceBar(
                    ticker=ticker,
                    date=datetime.fromtimestamp(ts).date(),
                    open=float(opens[i]) if i < len(opens) else 0,
                    high=float(highs[i]) if i < len(highs) else 0,
                    low=float(lows[i]) if i < len(lows) else 0,
                    close=float(closes[i]) if i < len(closes) else 0,
                    volume=int(volumes[i]) if i < len(volumes) else 0,
                    source="finnhub",
                )
            )

        return price_bars

    # ========================================================================
    # ProfileProvider Implementation
    # ========================================================================

    async def get_company_profile(self, ticker: str) -> CompanyProfile:
        """
        Get company profile information.

        Endpoint: /stock/profile2?symbol=TICKER

        Args:
            ticker: Stock symbol

        Returns:
            CompanyProfile with company details
        """
        data = await self._request("GET", "/stock/profile2", params={"symbol": ticker})

        if not data:
            raise ProviderError("finnhub", f"No profile data for {ticker}")

        # Parse IPO date if present
        ipo_date = None
        if data.get("ipo"):
            try:
                ipo_date = datetime.strptime(data["ipo"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        return CompanyProfile(
            ticker=ticker,
            company_name=data.get("name", ""),
            exchange=data.get("exchange"),
            sector=data.get("gics"),
            industry=data.get("subIndustry"),
            market_cap=float(data["marketCapitalization"]) if data.get("marketCapitalization") else None,
            description=data.get("description"),
            website=data.get("weburl"),
            ceo=data.get("ceo"),
            country=data.get("country"),
            employees=int(data["employeeCount"]) if data.get("employeeCount") else None,
            ipo_date=ipo_date,
            source="finnhub",
        )

    async def search_ticker(self, query: str) -> list[TickerSearchResult]:
        """
        Search for tickers by company name or symbol.

        Endpoint: /search?q=QUERY

        Args:
            query: Search query (company name or symbol)

        Returns:
            List of matching ticker results
        """
        data = await self._request("GET", "/search", params={"q": query})

        results = data.get("result", [])
        if not results:
            return []

        return [
            TickerSearchResult(
                ticker=r.get("symbol", ""),
                name=r.get("description", ""),
                exchange=r.get("displaySymbol"),
            )
            for r in results
            if r.get("symbol")
        ]

    # ========================================================================
    # NewsProvider Implementation
    # ========================================================================

    async def get_news(self, ticker: str, limit: int = 20) -> list[NewsItem]:
        """
        Get recent news for a ticker.

        Endpoint: /company-news?symbol=TICKER&from=DATE&to=DATE
        Also uses: /news-sentiment?symbol=TICKER for sentiment scores

        Args:
            ticker: Stock symbol
            limit: Maximum number of articles (default 20)

        Returns:
            List of NewsItem with optional sentiment
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # Last 30 days

        # Get news articles
        news_data = await self._request(
            "GET",
            "/company-news",
            params={
                "symbol": ticker,
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
        )

        # Get sentiment data
        sentiment_map = {}
        try:
            sentiment_data = await self._request(
                "GET", "/news-sentiment", params={"symbol": ticker}
            )
            # sentiment_data can be a dict with 'sentiment' key or directly a list
            sentiment_list = []
            if isinstance(sentiment_data, dict):
                sentiment_list = sentiment_data.get("sentiment", [])
            elif isinstance(sentiment_data, list):
                sentiment_list = sentiment_data

            sentiment_map = {
                item.get("ticker"): item.get("buzz", {})
                for item in sentiment_list
            }
        except ProviderError:
            pass  # Sentiment is optional

        # Sort by date (most recent first) and limit
        news_data.sort(key=lambda x: x.get("datetime", 0), reverse=True)
        news_data = news_data[:limit]

        articles = []
        for article in news_data:
            published = datetime.fromtimestamp(article.get("datetime", 0))

            # Try to get sentiment score if available
            sentiment_score = None
            sentiment_label = None
            if article.get("sentiment"):
                sentiment_score = article["sentiment"]
                if sentiment_score > 0.1:
                    sentiment_label = "positive"
                elif sentiment_score < -0.1:
                    sentiment_label = "negative"
                else:
                    sentiment_label = "neutral"

            articles.append(
                NewsItem(
                    headline=article.get("headline", ""),
                    summary=article.get("summary"),
                    source_name=article.get("source", "finnhub"),
                    source_url=article.get("url"),
                    ticker=ticker,
                    published_at=published,
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label,
                    relevance_score=None,  # Finnhub doesn't provide this directly
                    source="finnhub",
                )
            )

        return articles


# Self-registration
from app.services.data.registry import (
    register_news,
    register_prices,
    register_profiles,
)

register_prices("finnhub", FinnhubProvider)
register_profiles("finnhub", FinnhubProvider)
register_news("finnhub", FinnhubProvider)
