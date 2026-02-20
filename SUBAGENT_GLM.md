# Sub-Agent Work Package: GLM-4.7 (via `ccs glm`)

## Mission
Implement Finnhub and yfinance data providers that conform to the existing protocol interfaces, plus comprehensive tests for all data providers.

## Context
The project has a hot-swappable data provider architecture. The interfaces and canonical models are already built:
- **Protocols:** `backend/app/services/data/protocols.py` — defines `FundamentalsProvider`, `PriceProvider`, `ProfileProvider`, `NewsProvider`
- **Canonical schemas:** `backend/app/schemas/financial.py` — all providers must normalize to these models
- **Registry:** `backend/app/services/data/registry.py` — providers self-register, env vars select the active one
- **Error types:** `backend/app/core/errors.py` — use `ProviderError` and `RateLimitError`

## Important: Python Version
System Python is 3.9.6. Use `from __future__ import annotations` at the top of every file. Do NOT use `X | None` syntax without it.

## Task 1: Finnhub Provider
**File:** `backend/app/services/data/providers/finnhub.py`

Implement `FinnhubProvider` class that satisfies `PriceProvider`, `ProfileProvider`, and `NewsProvider` protocols.

### API Reference
- Base URL: `https://finnhub.io/api/v1`
- Auth: query param `?token={API_KEY}`
- Rate limit: 60 calls/minute (free tier)

### Required Methods
```python
class FinnhubProvider:
    provider_name = "finnhub"

    def __init__(self, api_key: str) -> None: ...

    # PriceProvider
    async def get_quote(self, ticker: str) -> StockQuote: ...
    async def get_historical_prices(self, ticker: str, start: date, end: date, interval: str = "1d") -> List[PriceBar]: ...

    # ProfileProvider
    async def get_company_profile(self, ticker: str) -> CompanyProfile: ...
    async def search_ticker(self, query: str) -> List[TickerSearchResult]: ...

    # NewsProvider
    async def get_news(self, ticker: str, limit: int = 20) -> List[NewsItem]: ...
```

### Finnhub Endpoints to Use
- `/quote?symbol=AAPL` — real-time quote
- `/stock/candle?symbol=AAPL&resolution=D&from=UNIX&to=UNIX` — historical OHLCV
- `/stock/profile2?symbol=AAPL` — company profile
- `/search?q=apple` — ticker search
- `/company-news?symbol=AAPL&from=2024-01-01&to=2024-12-31` — news
- `/news-sentiment?symbol=AAPL` — sentiment scores

### Self-Registration
At the bottom of the file:
```python
from app.services.data.registry import register_prices, register_profiles, register_news
register_prices("finnhub", FinnhubProvider)
register_profiles("finnhub", FinnhubProvider)
register_news("finnhub", FinnhubProvider)
```

### HTTP Client
Use `httpx.AsyncClient` for all requests. Handle rate limits (HTTP 429) by raising `RateLimitError("finnhub")`.

## Task 2: yfinance Fallback Provider
**File:** `backend/app/services/data/providers/yfinance_provider.py`

Implement `YFinanceProvider` as a free fallback that satisfies `FundamentalsProvider`, `PriceProvider`, and `ProfileProvider`.

### Important Notes
- yfinance is synchronous — wrap calls in `asyncio.to_thread()`
- Use `yf.Ticker(symbol)` to get data
- Map yfinance's field names to our canonical models

### Required Methods
```python
class YFinanceProvider:
    provider_name = "yfinance"

    def __init__(self, api_key: str = "") -> None: ...

    # FundamentalsProvider
    async def get_income_statement(self, ticker: str, period: str = "annual", limit: int = 5) -> List[IncomeStatement]: ...
    async def get_balance_sheet(self, ticker: str, period: str = "annual", limit: int = 5) -> List[BalanceSheet]: ...
    async def get_cash_flow(self, ticker: str, period: str = "annual", limit: int = 5) -> List[CashFlow]: ...
    async def get_financial_ratios(self, ticker: str) -> FinancialRatios: ...

    # PriceProvider
    async def get_quote(self, ticker: str) -> StockQuote: ...
    async def get_historical_prices(self, ticker: str, start: date, end: date, interval: str = "1d") -> List[PriceBar]: ...

    # ProfileProvider
    async def get_company_profile(self, ticker: str) -> CompanyProfile: ...
    async def search_ticker(self, query: str) -> List[TickerSearchResult]: ...
```

### Self-Registration
```python
from app.services.data.registry import register_fundamentals, register_prices, register_profiles
register_fundamentals("yfinance", YFinanceProvider)
register_prices("yfinance", YFinanceProvider)
register_profiles("yfinance", YFinanceProvider)
```

## Task 3: Tests
**File:** `backend/tests/test_data_providers.py`

Write tests for Finnhub and yfinance providers:

```python
# Test that providers produce correct canonical model types
# Test field mapping (key fields are not None)
# Test error handling (invalid ticker, rate limit)
# Use unittest.mock / respx to mock HTTP responses, do NOT make real API calls
```

Also add a provider swap test:
**File:** `backend/tests/test_provider_swap.py`
- Test that registry correctly initializes the configured provider
- Test fallback from primary to secondary via the aggregator

## How to Run Tests
```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
```

## Final Checklist
- [ ] `providers/finnhub.py` — PriceProvider + ProfileProvider + NewsProvider
- [ ] `providers/yfinance_provider.py` — FundamentalsProvider + PriceProvider + ProfileProvider
- [ ] `tests/test_data_providers.py` — mocked tests for both providers
- [ ] `tests/test_provider_swap.py` — registry and aggregator tests
- [ ] All files have `from __future__ import annotations` at the top
- [ ] All tests pass: `python -m pytest tests/ -v`
