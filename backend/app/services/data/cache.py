from __future__ import annotations
from typing import Optional, Any
"""
Redis caching layer for data providers.

Sits between the registry and providers to cache frequently accessed data
with category-specific TTL strategies.
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import redis.asyncio as redis
from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# =============================================================================
# Cache TTL Strategy by Category
# =============================================================================

CACHE_TTLS = {
    "quote": 30,  # 30 seconds — near real-time
    "profile": 86400,  # 24 hours — rarely changes
    "income_statement": 3600,  # 1 hour — changes quarterly
    "balance_sheet": 3600,
    "cash_flow": 3600,
    "ratios": 1800,  # 30 min
    "news": 300,  # 5 min
    "historical_prices": 3600,
    "search": 86400,  # 24 hours
    "filings": 3600,  # 1 hour
}


@dataclass
class CacheConfig:
    """Cache configuration for a data type."""

    ttl_seconds: int
    model_class: type[BaseModel]
    is_list: bool = False


class DataCache:
    """
    Redis-backed caching layer for financial data providers.

    Automatically serializes/deserializes Pydantic models and handles
    Redis connection failures gracefully (falls through to provider).

    Example:
        cache = DataCache("redis://localhost:6379")

        async def fetch_price(ticker: str) -> StockQuote:
            return await cache.get_or_fetch(
                key=f"fmp:quote:{ticker}",
                fetch_fn=lambda: provider.get_quote(ticker),
                ttl_seconds=CACHE_TTLS["quote"],
                model_class=StockQuote,
            )
    """

    def __init__(self, redis_url: str) -> None:
        """
        Initialize the cache.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379")
        """
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        self._connection_lock = asyncio.Lock()  # Prevent race condition

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get or create Redis connection (thread-safe)."""
        async with self._connection_lock:  # Prevent race condition
            if self._redis is None:
                try:
                    self._redis = await redis.from_url(
                        self._redis_url,
                        encoding="utf-8",
                        decode_responses=True,
                    )
                    # Test connection
                    await self._redis.ping()
                    self._connected = True
                    logger.info("Connected to Redis cache")
                except Exception as e:
                    logger.warning("Redis connection failed: %s. Caching disabled.", e)
                    self._connected = False
                    self._redis = None

        return self._redis

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._connected = False

    def _build_key(
        self,
        provider: str,
        data_type: str,
        ticker: str,
        extra: Optional[str] = None,
    ) -> str:
        """
        Build a cache key in the format:
        equity:{provider}:{data_type}:{ticker}:{extra}

        Args:
            provider: Provider name (e.g., "fmp", "finnhub")
            data_type: Data category (e.g., "quote", "income_statement")
            ticker: Stock ticker symbol
            extra: Optional extra identifier (e.g., "annual:5")

        Returns:
            Formatted cache key
        """
        key_parts = ["equity", provider, data_type, ticker]
        if extra:
            key_parts.append(extra)
        return ":".join(key_parts)

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable[..., Any],
        ttl_seconds: int,
        model_class: type[BaseModel],
    ) -> Any:
        """
        Get value from cache or fetch and cache it.

        Args:
            key: Cache key
            fetch_fn: Async function to fetch data if not in cache
            ttl_seconds: Time-to-live in seconds
            model_class: Pydantic model class for deserialization

        Returns:
            Cached or fetched value

        Note:
            On Redis failure, falls through to fetch_fn and logs warning.
        """
        redis_client = await self._get_redis()

        # Try to get from cache
        if redis_client and self._connected:
            try:
                cached_data = await redis_client.get(key)
                if cached_data:
                    try:
                        parsed = json.loads(cached_data)
                        # Check if it's a list wrapper
                        if isinstance(parsed, dict) and "items" in parsed:
                            items = [
                                model_class.model_validate(item)
                                for item in parsed["items"]
                            ]
                            logger.debug("Cache hit for key: %s", key)
                            return items
                        else:
                            result = model_class.model_validate_json(cached_data)
                            logger.debug("Cache hit for key: %s", key)
                            return result
                    except Exception as e:
                        logger.warning(
                            "Failed to deserialize cached data for %s: %s", key, e
                        )
                        # Fall through to fetch
            except Exception as e:
                logger.warning("Redis get failed for %s: %s", key, e)
                # Fall through to fetch

        # Fetch from provider
        try:
            result = await fetch_fn()
        except Exception as e:
            logger.error("Fetch failed for key %s: %s", key, e)
            raise

        # Try to cache the result
        if redis_client and self._connected:
            try:
                if isinstance(result, list):
                    # Wrap list in container for proper deserialization
                    serialized = json.dumps(
                        {"items": [item.model_dump() for item in result]}
                    )
                else:
                    serialized = result.model_dump_json()

                await redis_client.setex(key, ttl_seconds, serialized)
                logger.debug("Cached data for key: %s (TTL: %ds)", key, ttl_seconds)
            except Exception as e:
                logger.warning("Failed to cache data for %s: %s", key, e)
                # Continue even if caching fails

        return result

    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.

        Args:
            pattern: glob-style pattern (e.g., "equity:fmp:quote:*")
                    Note: Redis uses glob patterns, not regex

        Returns:
            Number of keys deleted
        """
        redis_client = await self._get_redis()

        if not redis_client or not self._connected:
            logger.warning("Redis not connected, cannot invalidate pattern: %s", pattern)
            return 0

        try:
            # Use SCAN to find keys matching pattern
            deleted_count = 0
            async for key in redis_client.scan_iter(match=pattern):
                await redis_client.delete(key)
                deleted_count += 1

            logger.info(
                "Invalidated %d keys matching pattern: %s", deleted_count, pattern
            )
            return deleted_count

        except Exception as e:
            logger.error("Failed to invalidate pattern %s: %s", pattern, e)
            return 0

    async def get_ttl(self, data_type: str) -> int:
        """
        Get the TTL for a data type from the default TTL strategy.

        Args:
            data_type: Data category (e.g., "quote", "profile")

        Returns:
            TTL in seconds
        """
        return CACHE_TTLS.get(data_type, 3600)  # Default to 1 hour

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        redis_client = await self._get_redis()

        if not redis_client or not self._connected:
            return False

        try:
            return await redis_client.exists(key) > 0
        except Exception:
            return False


# Convenience helper for building cache keys
def build_cache_key(
    provider: str,
    data_type: str,
    ticker: str,
    period: Optional[str] = None,
    limit: Optional[int] = None,
    **kwargs: Any,
) -> str:
    """
    Build a standardized cache key.

    Args:
        provider: Provider name (e.g., "fmp", "finnhub")
        data_type: Data category (e.g., "income_statement")
        ticker: Stock ticker symbol
        period: Optional period ("annual", "quarterly")
        limit: Optional limit number
        **kwargs: Additional key parameters

    Returns:
        Formatted cache key (e.g., "equity:fmp:income_statement:AAPL:annual:5")
    """
    extra_parts = []

    if period:
        extra_parts.append(period)
    if limit is not None:
        extra_parts.append(str(limit))

    # Add any additional kwargs in sorted order for consistency
    for key in sorted(kwargs.keys()):
        value = kwargs[key]
        if value is not None:
            extra_parts.append(f"{key}={value}")

    extra = ":".join(extra_parts) if extra_parts else None

    cache = DataCache.__new__(DataCache)  # Create without init to use static method
    return cache._build_key(provider, data_type, ticker, extra)
