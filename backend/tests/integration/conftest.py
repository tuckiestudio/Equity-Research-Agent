"""
Integration tests conftest - ensure environment variables are set before any imports.
"""
from __future__ import annotations

import os
import pytest

# Set test environment variables BEFORE any app imports
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-123456")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("FUNDAMENTALS_PROVIDER", "fmp")
os.environ.setdefault("PRICE_PROVIDER", "finnhub")


@pytest.fixture(scope="function", autouse=True)
async def setup_test_stocks() -> None:
    """Create common test stocks in the database before each test."""
    from app.db.session import get_db
    from app.models.stock import Stock
    from sqlalchemy import select

    db = await get_db().__anext__()

    # Create common test stocks if they don't exist
    test_stocks = [
        ("AAPL", "Apple Inc.", "NASDAQ", "Technology", "Consumer Electronics"),
        ("GOOGL", "Alphabet Inc.", "NASDAQ", "Technology", "Internet Content & Information"),
        ("MSFT", "Microsoft Corporation", "NASDAQ", "Technology", "Software"),
        ("TSLA", "Tesla Inc.", "NASDAQ", "Consumer Cyclical", "Auto Manufacturers"),
        ("NVDA", "NVIDIA Corporation", "NASDAQ", "Technology", "Semiconductors"),
        ("AMZN", "Amazon.com Inc.", "NASDAQ", "Consumer Cyclical", "Internet Retail"),
        ("META", "Meta Platforms Inc.", "NASDAQ", "Technology", "Internet Content & Information"),
    ]

    for ticker, company_name, exchange, sector, industry in test_stocks:
        result = await db.execute(select(Stock).where(Stock.ticker == ticker))
        if not result.scalar_one_or_none():
            stock = Stock(
                ticker=ticker,
                company_name=company_name,
                exchange=exchange,
                sector=sector,
                industry=industry,
            )
            db.add(stock)

    await db.commit()
