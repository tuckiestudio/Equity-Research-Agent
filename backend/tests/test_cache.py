from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.schemas.financial import StockQuote, TickerSearchResult
from app.services.data.cache import CACHE_TTLS, DataCache


class TestDataCache:
    """Test suite for Redis-backed data cache."""

    def test_build_key_format(self):
        """Test cache key format."""
        cache = DataCache("redis://localhost:6379")

        key = cache._build_key("fmp", "quote", "AAPL", "daily")

        assert key == "equity:fmp:quote:AAPL:daily"

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_miss(self):
        """Test cache miss falls back to fetch."""
        cache = DataCache("redis://localhost:6379")
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        cache._connected = True
        cache._redis = mock_redis

        fetch_fn = AsyncMock(
            return_value=StockQuote(
                ticker="AAPL",
                price=150.25,
                timestamp=datetime.utcnow(),
                source="fmp",
            )
        )

        result = await cache.get_or_fetch(
            key="equity:fmp:quote:AAPL",
            fetch_fn=fetch_fn,
            ttl_seconds=30,
            model_class=StockQuote,
        )

        assert isinstance(result, StockQuote)
        fetch_fn.assert_awaited_once()
        mock_redis.setex.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_or_fetch_cache_hit(self):
        """Test cache hit skips fetch."""
        cache = DataCache("redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._connected = True
        cache._redis = mock_redis

        quote = StockQuote(
            ticker="AAPL",
            price=150.25,
            timestamp=datetime.utcnow(),
            source="fmp",
        )
        mock_redis.get.return_value = quote.model_dump_json()

        fetch_fn = AsyncMock()

        result = await cache.get_or_fetch(
            key="equity:fmp:quote:AAPL",
            fetch_fn=fetch_fn,
            ttl_seconds=30,
            model_class=StockQuote,
        )

        assert isinstance(result, StockQuote)
        assert result.ticker == "AAPL"
        fetch_fn.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_fetch_redis_failure_fallthrough(self):
        """Test Redis error falls through to fetch."""
        cache = DataCache("redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._connected = True
        cache._redis = mock_redis
        mock_redis.get.side_effect = Exception("Redis down")

        fetch_fn = AsyncMock(
            return_value=StockQuote(
                ticker="AAPL",
                price=150.25,
                timestamp=datetime.utcnow(),
                source="fmp",
            )
        )

        result = await cache.get_or_fetch(
            key="equity:fmp:quote:AAPL",
            fetch_fn=fetch_fn,
            ttl_seconds=30,
            model_class=StockQuote,
        )

        assert isinstance(result, StockQuote)
        fetch_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self):
        """Test pattern invalidation."""
        cache = DataCache("redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._connected = True
        cache._redis = mock_redis

        async def async_iter(items):
            for item in items:
                yield item

        mock_redis.scan_iter = Mock(
            return_value=async_iter(
                ["equity:fmp:quote:AAPL", "equity:fmp:quote:MSFT"]
            )
        )

        deleted = await cache.invalidate("equity:fmp:quote:*")

        assert deleted == 2
        assert mock_redis.delete.await_count == 2

    def test_ttl_strategy(self):
        """Test TTL strategy values."""
        assert CACHE_TTLS["quote"] == 30
        assert CACHE_TTLS["profile"] == 86400
        assert CACHE_TTLS["income_statement"] == 3600
        assert CACHE_TTLS["balance_sheet"] == 3600
        assert CACHE_TTLS["cash_flow"] == 3600
        assert CACHE_TTLS["ratios"] == 1800
        assert CACHE_TTLS["news"] == 300
        assert CACHE_TTLS["historical_prices"] == 3600
        assert CACHE_TTLS["search"] == 86400
        assert CACHE_TTLS["filings"] == 3600

    @pytest.mark.asyncio
    async def test_list_serialization(self):
        """Test list serialization wrapper."""
        cache = DataCache("redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._connected = True
        cache._redis = mock_redis
        mock_redis.get.return_value = None

        results = [
            TickerSearchResult(
                ticker="AAPL",
                name="Apple Inc.",
                exchange="NASDAQ",
                type="stock",
            )
        ]

        fetch_fn = AsyncMock(return_value=results)

        result = await cache.get_or_fetch(
            key="equity:fmp:search:AAPL",
            fetch_fn=fetch_fn,
            ttl_seconds=3600,
            model_class=TickerSearchResult,
        )

        assert result == results
        assert mock_redis.setex.await_count == 1
        _, _, serialized = mock_redis.setex.await_args.args
        parsed = json.loads(serialized)
        assert "items" in parsed
        assert parsed["items"][0]["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_get_ttl_default(self):
        """Test default TTL fallback."""
        cache = DataCache("redis://localhost:6379")

        ttl = await cache.get_ttl("unknown")

        assert ttl == 3600
