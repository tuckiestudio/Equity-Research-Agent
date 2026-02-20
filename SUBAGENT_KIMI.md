# Sub-Agent Work Package: Kimi-K2.5 (via `ccs chutes`)

## Mission
Implement FMP data provider, SEC EDGAR provider, and Redis caching layer for the hot-swappable data architecture.

## Context
The project has a hot-swappable data provider architecture. The interfaces and canonical models are already built:
- **Protocols:** `backend/app/services/data/protocols.py` — defines `FundamentalsProvider`, `PriceProvider`, `ProfileProvider`, `NewsProvider`
- **Canonical schemas:** `backend/app/schemas/financial.py` — all providers must normalize to these models (IncomeStatement, BalanceSheet, CashFlow, StockQuote, PriceBar, CompanyProfile, FinancialRatios, NewsItem)
- **Registry:** `backend/app/services/data/registry.py` — providers self-register via `register_fundamentals()`, `register_prices()`, etc.
- **Error types:** `backend/app/core/errors.py` — use `ProviderError(provider_name, detail)` and `RateLimitError(provider_name)`
- **Config:** `backend/app/core/config.py` — `settings.FMP_API_KEY`, `settings.REDIS_URL`

## Important: Python Version
System Python is 3.9.6. Use `from __future__ import annotations` at the top of every file. Do NOT use `X | None` syntax without it.

## Task 1: FMP Provider (Primary)
**File:** `backend/app/services/data/providers/fmp.py`

Implement `FMPProvider` class that satisfies `FundamentalsProvider`, `PriceProvider`, and `ProfileProvider` protocols. FMP is the primary data source ($19/mo plan).

### API Reference
- Base URL: `https://financialmodelingprep.com/api/v3`
- Auth: query param `?apikey={API_KEY}`
- Rate limit: 300 calls/min on starter plan

### Required Methods
```python
class FMPProvider:
    provider_name = "fmp"

    def __init__(self, api_key: str) -> None: ...

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

### FMP Endpoints to Use
- `/income-statement/AAPL?period=annual&limit=5` — income statement
- `/balance-sheet-statement/AAPL?period=annual&limit=5` — balance sheet
- `/cash-flow-statement/AAPL?period=annual&limit=5` — cash flow
- `/ratios/AAPL?limit=1` — financial ratios
- `/quote/AAPL` — real-time quote (returns array)
- `/historical-price-full/AAPL?from=2024-01-01&to=2024-12-31` — historical OHLCV
- `/profile/AAPL` — company profile (returns array)
- `/search?query=apple&limit=10` — ticker search

### Field Mapping Guidelines
FMP uses camelCase. Map carefully:
- `revenue` → `revenue`
- `costOfRevenue` → `cost_of_revenue`
- `grossProfit` → `gross_profit`
- `researchAndDevelopmentExpenses` → `research_and_development`
- `sellingGeneralAndAdministrativeExpenses` → `selling_general_admin`
- `operatingIncome` → `operating_income`
- `ebitda` → `ebitda`
- `netIncome` → `net_income`
- `eps` → `eps`
- `epsdiluted` → `eps_diluted`

### Self-Registration
```python
from app.services.data.registry import register_fundamentals, register_prices, register_profiles
register_fundamentals("fmp", FMPProvider)
register_prices("fmp", FMPProvider)
register_profiles("fmp", FMPProvider)
```

### HTTP Client
Use `httpx.AsyncClient` for all requests. Handle:
- HTTP 429 → raise `RateLimitError("fmp")`
- HTTP 4xx/5xx → raise `ProviderError("fmp", detail_message)`
- Empty responses → raise `ProviderError("fmp", "No data returned for {ticker}")`

## Task 2: SEC EDGAR Provider
**File:** `backend/app/services/data/providers/sec_edgar.py`

Implement a provider that fetches SEC filing data. This is a specialized provider that doesn't fit the standard protocols — it has its own interface.

### Interface
```python
class SECEdgarProvider:
    provider_name = "sec_edgar"

    def __init__(self, api_key: str = "") -> None: ...

    async def get_filing_list(
        self, ticker: str, filing_type: str = "10-K", limit: int = 5
    ) -> List[SECFiling]: ...

    async def get_filing_text(self, accession_number: str) -> str: ...
```

### Data Model
Add to the file:
```python
class SECFiling(BaseModel):
    ticker: str
    filing_type: str        # 10-K, 10-Q, 8-K
    filed_date: date
    accession_number: str
    primary_document: str   # URL to the filing
    description: str
```

### SEC EDGAR API
- Base URL: `https://efts.sec.gov/LATEST`
- Full-text search: `https://efts.sec.gov/LATEST/search-index?q=AAPL&dateRange=custom&startdt=2024-01-01&enddt=2024-12-31&forms=10-K`
- Company filings: `https://data.sec.gov/submissions/CIK{cik_padded}.json`
- **IMPORTANT:** Set `User-Agent` header to `"EquityResearchAgent/1.0 (contact@example.com)"` — SEC requires this

### Ticker to CIK Mapping
Use the SEC company tickers file: `https://www.sec.gov/files/company_tickers.json`
Cache this mapping in memory (it changes rarely).

## Task 3: Redis Caching Layer
**File:** `backend/app/services/data/cache.py`

Implement a caching wrapper that sits between the registry and the providers.

### Interface
```python
class DataCache:
    def __init__(self, redis_url: str) -> None: ...

    async def get_or_fetch(
        self,
        key: str,
        fetch_fn: Callable,
        ttl_seconds: int,
        model_class: Type[BaseModel],
    ) -> Any: ...

    async def invalidate(self, pattern: str) -> int: ...
```

### TTL Strategy by Category
```python
CACHE_TTLS = {
    "quote": 30,            # 30 seconds — near real-time
    "profile": 86400,       # 24 hours — rarely changes
    "income_statement": 3600, # 1 hour — changes quarterly
    "balance_sheet": 3600,
    "cash_flow": 3600,
    "ratios": 1800,          # 30 min
    "news": 300,             # 5 min
    "historical_prices": 3600,
    "search": 86400,         # 24 hours
    "filings": 3600,         # 1 hour
}
```

### Cache Key Format
`equity:{provider}:{data_type}:{ticker}:{extra}`
Example: `equity:fmp:income_statement:AAPL:annual:5`

### Implementation Notes
- Use `redis.asyncio` (the async Redis client already in requirements)
- Serialize Pydantic models with `.model_dump_json()` and deserialize with `model_class.model_validate_json()`
- For list results, wrap in a container: `{"items": [...]}`
- Handle Redis connection failures gracefully — log warning and fall through to the actual provider

## How to Run Tests
```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
```

## Final Checklist
- [ ] `providers/fmp.py` — FundamentalsProvider + PriceProvider + ProfileProvider
- [ ] `providers/sec_edgar.py` — Filing list + filing text
- [ ] `services/data/cache.py` — Redis caching with per-category TTLs
- [ ] All files have `from __future__ import annotations` at the top
- [ ] All HTTP calls use `httpx.AsyncClient`
- [ ] All providers self-register at module level
- [ ] Error handling with `ProviderError` and `RateLimitError`
