# Sub-Agent Work Package: Codex-5.2 (via Claude `ccs chutes`)

## Mission
Write comprehensive tests for the FMP, SEC EDGAR, and Redis cache implementations that Kimi partially completed. All 3 implementations exist and import correctly, but have **zero test coverage**.

## Context
The project has a hot-swappable data provider architecture. The foundation is fully built and tested (44 tests pass). You need to add tests for the remaining untested components.

### What Already Exists & Works ✅
- `backend/app/services/data/providers/fmp.py` — 607-line FMP provider (FundamentalsProvider + PriceProvider + ProfileProvider)
- `backend/app/services/data/providers/sec_edgar.py` — 306-line SEC EDGAR provider (filing list + filing text)
- `backend/app/services/data/cache.py` — 315-line Redis caching layer with per-category TTLs
- `backend/tests/test_data_providers.py` — 506 lines, tests Finnhub + yfinance (17 tests) ← **use as reference for style**
- `backend/tests/test_provider_swap.py` — tests for registry + protocol conformance (21 tests)
- All providers import and self-register correctly

### Key Files to Reference
- `backend/app/schemas/financial.py` — canonical Pydantic models (IncomeStatement, BalanceSheet, CashFlow, StockQuote, PriceBar, CompanyProfile, FinancialRatios, NewsItem, TickerSearchResult)
- `backend/app/core/errors.py` — `ProviderError`, `RateLimitError`
- `backend/app/services/data/protocols.py` — provider protocol interfaces

## Important: Python Version
System Python is 3.9.6. Use `from __future__ import annotations` at the top of every file. Do NOT use `X | None` union syntax without it.

## Task 1: FMP Provider Tests
**File:** `backend/tests/test_fmp_provider.py`

Write mocked tests for `FMPProvider`. Follow the same pattern as `test_data_providers.py` (mock the HTTP client, verify canonical model types).

### Tests to Write
```python
class TestFMPProvider:
    # 1. test_get_income_statement_success — mock /income-statement/AAPL response, verify IncomeStatement fields
    # 2. test_get_balance_sheet_success — mock /balance-sheet-statement/AAPL, verify BalanceSheet fields
    # 3. test_get_cash_flow_success — mock /cash-flow-statement/AAPL, verify CashFlow fields
    # 4. test_get_financial_ratios_success — mock /ratios/AAPL, verify FinancialRatios fields
    # 5. test_get_quote_success — mock /quote/AAPL, verify StockQuote fields
    # 6. test_get_historical_prices_success — mock /historical-price-full/AAPL, verify List[PriceBar]
    # 7. test_get_company_profile_success — mock /profile/AAPL, verify CompanyProfile fields
    # 8. test_search_ticker_success — mock /search?query=apple, verify List[TickerSearchResult]
    # 9. test_empty_response_error — mock empty array response, verify ProviderError raised
    # 10. test_rate_limit_error — mock HTTP 429, verify RateLimitError raised
    # 11. test_api_error_handling — mock HTTP 500, verify ProviderError raised
    # 12. test_field_mapping_camelcase — verify FMP camelCase → snake_case mapping for key fields
```

### FMP Mock Response Examples
```python
# /income-statement/AAPL response
[{
    "date": "2023-09-30",
    "symbol": "AAPL",
    "fillingDate": "2023-11-03",
    "period": "FY",
    "revenue": 383285000000,
    "costOfRevenue": 214137000000,
    "grossProfit": 169148000000,
    "researchAndDevelopmentExpenses": 29915000000,
    "sellingGeneralAndAdministrativeExpenses": 24932000000,
    "operatingIncome": 114301000000,
    "ebitda": 125820000000,
    "netIncome": 96995000000,
    "eps": 6.13,
    "epsdiluted": 6.13,
}]

# /quote/AAPL response
[{
    "symbol": "AAPL",
    "price": 178.72,
    "change": 1.23,
    "changesPercentage": 0.6929,
    "dayHigh": 179.61,
    "dayLow": 177.33,
    "open": 178.55,
    "previousClose": 177.49,
    "volume": 54232112,
    "marketCap": 2800000000000,
    "timestamp": 1704067200,
}]

# /profile/AAPL response
[{
    "symbol": "AAPL",
    "companyName": "Apple Inc.",
    "exchange": "NASDAQ",
    "sector": "Technology",
    "industry": "Consumer Electronics",
    "mktCap": 2800000000000,
    "description": "Apple Inc. designs...",
    "website": "https://www.apple.com",
    "ceo": "Tim Cook",
    "country": "US",
    "fullTimeEmployees": "164000",
    "ipoDate": "1980-12-12",
}]
```

## Task 2: SEC EDGAR Provider Tests
**File:** `backend/tests/test_sec_edgar_provider.py`

Write mocked tests for `SECEdgarProvider`.

### Tests to Write
```python
class TestSECEdgarProvider:
    # 1. test_get_cik_success — mock company_tickers.json, verify CIK lookup
    # 2. test_get_cik_not_found — mock empty tickers, verify ProviderError
    # 3. test_get_filing_list_success — mock submissions/CIK.json, verify SECFiling list
    # 4. test_get_filing_list_filter_type — verify filing_type filter works (10-K only)
    # 5. test_get_filing_text_success — mock filing document fetch, verify text returned
    # 6. test_get_filing_text_error — mock 404, verify ProviderError
    # 7. test_cik_cache — verify CIK mapping is cached (second call doesn't re-fetch)
```

### SEC EDGAR Mock Response Examples
```python
# company_tickers.json
{"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}

# submissions/CIK0000320193.json
{
    "cik": "320193",
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "filings": {
        "recent": {
            "accessionNumber": ["0000320193-23-000077", "0000320193-23-000064"],
            "filingDate": ["2023-11-03", "2023-08-04"],
            "form": ["10-K", "10-Q"],
            "primaryDocument": ["aapl-20230930.htm", "aapl-20230701.htm"],
            "primaryDocDescription": ["10-K", "10-Q"],
        }
    }
}
```

## Task 3: Redis Cache Tests
**File:** `backend/tests/test_cache.py`

Write tests for `DataCache`. Use `unittest.mock` to mock the Redis client — do NOT require a running Redis instance.

### Tests to Write
```python
class TestDataCache:
    # 1. test_build_key_format — verify key format is "equity:{provider}:{type}:{ticker}:{extra}"
    # 2. test_get_or_fetch_cache_miss — verify fetch_fn is called on cache miss
    # 3. test_get_or_fetch_cache_hit — verify fetch_fn is NOT called on cache hit
    # 4. test_get_or_fetch_redis_failure_fallthrough — verify falls through to fetch_fn when Redis is down
    # 5. test_invalidate_pattern — verify pattern-based invalidation
    # 6. test_ttl_strategy — verify CACHE_TTLS has correct values for each category
    # 7. test_list_serialization — verify list results are wrapped in {"items": [...]} container
    # 8. test_get_ttl_default — verify default TTL for unknown data types
```

## How to Run Tests
```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
```

All existing 44 tests must continue to pass. Your new tests should add ~27 more tests (12 + 7 + 8).

## Final Checklist
- [ ] `tests/test_fmp_provider.py` — ~12 mocked tests for FMP provider
- [ ] `tests/test_sec_edgar_provider.py` — ~7 mocked tests for SEC EDGAR provider
- [ ] `tests/test_cache.py` — ~8 tests for Redis cache (mocked Redis)
- [ ] All files have `from __future__ import annotations` at the top
- [ ] All tests use `unittest.mock` / mocked responses, NO real API calls
- [ ] All ~71 tests pass: `python -m pytest tests/ -v`
- [ ] Follow existing test style in `test_data_providers.py` (pytest fixtures, async/await test methods)
