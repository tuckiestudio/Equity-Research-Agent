"""
Pytest conftest.py - Shared fixtures, mocks, and utilities for all tests.

This module provides:
- Database session management with test database
- TestClient with authentication helpers
- Mock fixtures for external APIs (data providers, LLMs)
- User factories and test data generators
- Async fixtures for async tests
"""
from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Set test environment variables before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-32chars-long-123456")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("FUNDAMENTALS_PROVIDER", "fmp")
os.environ.setdefault("PRICE_PROVIDER", "finnhub")

from app.main import app
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.stock import Stock, Portfolio
from app.services.auth import create_access_token, hash_password
from app.core.config import settings


# ---------------------------------------------------------------------------
# Database Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database() -> None:
    """
    Create all database tables before any tests run.

    This fixture is autouse=True and session-scoped, so it runs once
    before all tests. This ensures tables exist for both sync and async
    TestClient tests.
    """
    from app.db.session import engine
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create a session-scoped test database engine with tables created.

    This is used for tests that use the sync TestClient and need tables
    to be available at module load time.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a test database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # Create all tables
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with rollback after each test."""
    async_session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# Test Client Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client without authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture(scope="function")
async def authenticated_client(db_session: AsyncSession) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """Create an authenticated test client with a test user."""
    # Create test user
    user = User(
        email=f"test-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        tier="free",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create client with auth
    ac = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )
    ac.headers["Authorization"] = f"Bearer {create_access_token({'sub': str(user.id)})}"

    yield ac, user

    await ac.aclose()


@pytest.fixture(scope="function")
async def pro_user_client(db_session: AsyncSession) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """Create an authenticated test client with a PRO tier user."""
    user = User(
        email=f"pro-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Pro User",
        tier="pro",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    ac = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )
    ac.headers["Authorization"] = f"Bearer {create_access_token({'sub': str(user.id)})}"

    yield ac, user

    await ac.aclose()


@pytest.fixture(scope="function")
async def premium_user_client(db_session: AsyncSession) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """Create an authenticated test client with a PREMIUM tier user."""
    user = User(
        email=f"premium-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Premium User",
        tier="premium",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    ac = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )
    ac.headers["Authorization"] = f"Bearer {create_access_token({'sub': str(user.id)})}"

    yield ac, user

    await ac.aclose()


@pytest.fixture(scope="function")
async def admin_user_client(db_session: AsyncSession) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """Create an authenticated test client with an admin user."""
    user = User(
        email=f"admin-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Admin User",
        tier="premium",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    ac = AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )
    ac.headers["Authorization"] = f"Bearer {create_access_token({'sub': str(user.id)})}"

    yield ac, user

    await ac.aclose()


# ---------------------------------------------------------------------------
# User Factories
# ---------------------------------------------------------------------------


@pytest.fixture
def user_factory() -> callable:
    """Factory for creating user objects (not persisted)."""
    def _factory(
        email: Optional[str] = None,
        password: str = "testpassword123",
        full_name: str = "Test User",
        tier: str = "free",
        is_admin: bool = False,
    ) -> User:
        return User(
            email=email or f"test-{uuid.uuid4()}@example.com",
            hashed_password=hash_password(password),
            full_name=full_name,
            tier=tier,
            is_admin=is_admin,
        )
    return _factory


# ---------------------------------------------------------------------------
# Mock Fixtures for External APIs
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_fmp_data() -> dict:
    """Mock data for FMP provider."""
    return {
        "profile": {
            "symbol": "AAPL",
            "price": 150.00,
            "beta": 1.2,
            "volAvg": 50000000,
            "mktCap": 2500000000000,
            "lastDiv": 0.96,
            "range": "120-180",
            "changes": 2.5,
            "companyName": "Apple Inc.",
            "currency": "USD",
            "cik": "0000320193",
            "isin": "US0378331005",
            "cusip": "037833100",
            "exchange": "NASDAQ",
            "exchangeShortName": "NASDAQ",
            "industry": "Consumer Electronics",
            "website": "https://www.apple.com",
            "description": "Apple Inc. designs...",
            "ceo": "Tim Cook",
            "sector": "Technology",
            "country": "US",
            "fullTimeEmployees": "164000",
            "phone": "1234567890",
            "address": "One Apple Park Way",
            "city": "Cupertino",
            "state": "CA",
            "zip": "95014",
            "dcfDiff": 10.5,
            "dcf": 160.0,
            "image": "https://example.com/logo.png",
            "ipoDate": "1980-12-12",
            "defaultImage": False,
            "isEtf": False,
            "isActivelyTrading": True,
            "isAdr": False,
            "isFund": False,
        },
        "income_statement": [{
            "date": "2024-09-30",
            "symbol": "AAPL",
            "reportedCurrency": "USD",
            "cik": "0000320193",
            "fillingDate": "2024-11-01",
            "acceptedDate": "2024-11-01 18:08:27",
            "calendarYear": "2024",
            "period": "FY",
            "revenue": 391000000000,
            "costOfRevenue": 210000000000,
            "grossProfit": 181000000000,
            "grossProfitRatio": 0.4628,
            "researchAndDevelopmentExpenses": 31000000000,
            "generalAndAdministrativeExpenses": 26000000000,
            "sellingAndMarketingExpenses": 0,
            "sellingGeneralAndAdministrativeExpenses": 26000000000,
            "otherExpenses": 0,
            "operatingExpenses": 57000000000,
            "costAndExpenses": 267000000000,
            "interestIncome": 3000000000,
            "interestExpense": 3900000000,
            "depreciationAndAmortization": 11500000000,
            "ebitda": 135500000000,
            "ebitdaratio": 0.3465,
            "operatingIncome": 124000000000,
            "operatingIncomeRatio": 0.3171,
            "totalOtherIncomeExpensesNet": -900000000,
            "incomeBeforeTax": 123100000000,
            "incomeBeforeTaxRatio": 0.3148,
            "incomeTaxExpense": 29000000000,
            "netIncome": 94100000000,
            "netIncomeRatio": 0.2406,
            "eps": 6.08,
            "epsdiluted": 6.08,
            "weightedAverageShsOut": 15480000000,
            "weightedAverageShsOutDil": 15480000000,
            "link": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.htm",
            "finalLink": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240930.htm",
        }],
        "ratios": {
            "pe_ratio": 24.7,
            "ev_to_ebitda": 18.5,
            "price_to_book": 39.2,
            "price_to_sales": 6.4,
        },
    }


@pytest.fixture
def mock_llm_response() -> dict:
    """Mock response for LLM providers."""
    return {
        "content": "This is a test response from the LLM.",
        "model": "claude-sonnet-4-20250514",
        "provider": "anthropic",
        "input_tokens": 100,
        "output_tokens": 50,
        "latency_ms": 500,
        "cost_usd": 0.001,
        "finish_reason": "stop",
    }


@pytest.fixture
def mock_news_data() -> list[dict]:
    """Mock news articles."""
    return [
        {
            "symbol": "AAPL",
            "publishedDate": "2024-01-15T10:30:00.000Z",
            "title": "Apple Reports Record Q4 Earnings",
            "image": "https://example.com/news1.jpg",
            "site": "Reuters",
            "text": "Apple Inc. reported record fourth-quarter earnings...",
            "url": "https://example.com/news/1",
        },
        {
            "symbol": "AAPL",
            "publishedDate": "2024-01-14T15:45:00.000Z",
            "title": "Apple Vision Pro Launch Date Announced",
            "image": "https://example.com/news2.jpg",
            "site": "Bloomberg",
            "text": "Apple announced the launch date for its Vision Pro headset...",
            "url": "https://example.com/news/2",
        },
    ]


@pytest.fixture
def mock_price_data() -> dict:
    """Mock stock price data."""
    return {
        "symbol": "AAPL",
        "open": 148.50,
        "high": 151.20,
        "low": 147.80,
        "close": 150.00,
        "volume": 45000000,
        "adjClose": 150.00,
        "timestamp": int(datetime.now().timestamp()),
    }


# ---------------------------------------------------------------------------
# Test Data Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_stock_data() -> dict:
    """Sample stock data for creating test stocks."""
    return {
        "AAPL": {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        },
        "GOOGL": {
            "ticker": "GOOGL",
            "company_name": "Alphabet Inc.",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Internet Content & Information",
        },
        "MSFT": {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "sector": "Technology",
            "industry": "Software",
        },
        "TSLA": {
            "ticker": "TSLA",
            "company_name": "Tesla, Inc.",
            "exchange": "NASDAQ",
            "sector": "Consumer Cyclical",
            "industry": "Auto Manufacturers",
        },
        "JPM": {
            "ticker": "JPM",
            "company_name": "JPMorgan Chase & Co.",
            "exchange": "NYSE",
            "sector": "Financial Services",
            "industry": "Banks - Diversified",
        },
    }


@pytest.fixture
def sample_assumption_data() -> dict:
    """Sample assumption set for DCF modeling."""
    return {
        "revenue_growth_rate": [0.10, 0.08, 0.06, 0.05, 0.04],
        "ebitda_margin": [0.35, 0.36, 0.37, 0.37, 0.38],
        "tax_rate": [0.15, 0.15, 0.15, 0.15, 0.15],
        "capex_percent_revenue": [0.03, 0.03, 0.03, 0.03, 0.03],
        "nwc_percent_revenue": [0.02, 0.02, 0.02, 0.02, 0.02],
        "wacc": 0.09,
        "terminal_growth_rate": 0.025,
        "shares_outstanding": 15480000000,
    }


@pytest.fixture
def sample_scenario_data() -> list[dict]:
    """Sample scenarios for valuation."""
    return [
        {
            "name": "Base Case",
            "probability": 0.6,
            "revenue_growth_adjustment": 0.0,
            "margin_adjustment": 0.0,
            "wacc_adjustment": 0.0,
            "terminal_growth_adjustment": 0.0,
        },
        {
            "name": "Bull Case",
            "probability": 0.25,
            "revenue_growth_adjustment": 0.03,
            "margin_adjustment": 0.02,
            "wacc_adjustment": -0.01,
            "terminal_growth_adjustment": 0.005,
        },
        {
            "name": "Bear Case",
            "probability": 0.15,
            "revenue_growth_adjustment": -0.04,
            "margin_adjustment": -0.03,
            "wacc_adjustment": 0.015,
            "terminal_growth_adjustment": -0.01,
        },
    ]


# ---------------------------------------------------------------------------
# Async Helper Functions
# ---------------------------------------------------------------------------


async def create_test_user(
    db_session: AsyncSession,
    email: Optional[str] = None,
    password: str = "testpassword123",
    full_name: str = "Test User",
    tier: str = "free",
    is_admin: bool = False,
) -> User:
    """Helper to create and persist a test user."""
    user = User(
        email=email or f"test-{uuid.uuid4()}@example.com",
        hashed_password=hash_password(password),
        full_name=full_name,
        tier=tier,
        is_admin=is_admin,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def create_test_stock(
    db_session: AsyncSession,
    ticker: str,
    company_name: str,
    exchange: str = "NASDAQ",
    sector: str = "Technology",
    industry: str = "Software",
) -> Stock:
    """Helper to create and persist a test stock."""
    stock = Stock(
        ticker=ticker,
        company_name=company_name,
        exchange=exchange,
        sector=sector,
        industry=industry,
    )
    db_session.add(stock)
    await db_session.commit()
    await db_session.refresh(stock)
    return stock


async def create_test_portfolio(
    db_session: AsyncSession,
    user: User,
    name: str,
    stocks: Optional[list[Stock]] = None,
) -> Portfolio:
    """Helper to create and persist a test portfolio."""
    portfolio = Portfolio(
        name=name,
        user_id=user.id,
    )
    db_session.add(portfolio)
    await db_session.commit()
    await db_session.refresh(portfolio)

    if stocks:
        portfolio.stocks.extend(stocks)
        await db_session.commit()
        await db_session.refresh(portfolio)

    return portfolio


# ---------------------------------------------------------------------------
# Rate Limit Test Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def rate_limit_config() -> dict:
    """Rate limit configuration for testing."""
    return {
        "register": {"calls": 3, "period": 60},
        "login": {"calls": 5, "period": 60},
        "thesis_generate": {"calls": 10, "period": 60},
        "news_analyze": {"calls": 20, "period": 60},
    }
