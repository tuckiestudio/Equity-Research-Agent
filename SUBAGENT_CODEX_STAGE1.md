# Sub-Agent Work Package: Codex — Stage 1 (Comps + Scenarios)

## Objective

Build the comparable company (comps) analysis engine, scenario management system, and Excel export functionality.

## Environment

- Python 3.9 (`from __future__ import annotations` everywhere, no `X | None`)
- FastAPI + SQLAlchemy async + Pydantic v2
- Virtual env: `source backend/venv/bin/activate`
- Run tests: `cd backend && python -m pytest tests/ -v`
- All new files go under `backend/app/` or `backend/tests/`
- Install if needed: `pip install openpyxl`

## Codebase Context

### Existing schemas (read `app/schemas/financial.py`)

- `FinancialRatios` — `.pe_ratio`, `.ev_to_ebitda`, `.price_to_book`, `.price_to_sales`, `.gross_margin`, `.operating_margin`, `.net_margin`
- `CompanyProfile` — `.ticker`, `.company_name`, `.sector`, `.industry`, `.market_cap`
- `StockQuote` — `.ticker`, `.price`, `.market_cap`

### Existing data protocols (read `app/services/data/protocols.py`)

Data fetching is done via the provider registry:
```python
from app.services.data.registry import ProviderRegistry
registry = ProviderRegistry()

# Get ratios for a ticker
ratios_provider = registry.get_fundamentals_provider()
ratios = await ratios_provider.get_financial_ratios("AAPL")

# Get profile
profile_provider = registry.get_profile_provider()
profile = await profile_provider.get_company_profile("AAPL")
```

### Existing DB patterns (read `app/models/base.py`, `app/models/stock.py`)

- `Base`, `UUIDMixin`, `TimestampMixin`
- UUID primary keys, SQLAlchemy `Mapped` type hints

### Existing API patterns (read `app/api/v1/stocks.py`)

- `APIRouter(prefix=..., tags=[...])`, `Depends(get_current_user)`, `Depends(get_db)`
- Pydantic response schemas with `model_config = {"from_attributes": True}`
- Errors: `NotFoundError`, `ValidationError` from `app.core.errors`

### LLM integration (for comp suggestions)

- `app/services/llm/router.py` — `LLMRouter.complete()`
- `app/services/llm/types.py` — `TaskType.COMPANY_COMPARISON`, `LLMMessage`, `LLMRole`
- `app/services/llm/prompts/templates.py` — `TEMPLATES["company_comparison"]` with placeholders: `company_a`, `company_b`, `financial_data_a`, `financial_data_b`

---

## Task 1: Comps Analysis Engine

**File:** `app/services/model/comps.py`

```python
class CompMetric(BaseModel):
    """A single comparable metric for one company."""
    ticker: str
    company_name: str
    sector: str | None  # Use Optional[str] for 3.9
    industry: str | None
    market_cap: float | None
    pe_ratio: float | None
    ev_to_ebitda: float | None
    price_to_book: float | None
    price_to_sales: float | None
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None

class CompsResult(BaseModel):
    """Comparable analysis output."""
    target_ticker: str
    peers: list[CompMetric]
    median_pe: float | None
    median_ev_ebitda: float | None
    median_pb: float | None
    median_ps: float | None
    implied_value_pe: float | None  # median_pe * target EPS
    implied_value_ev_ebitda: float | None  # derived from median multiple

class CompsEngine:
    async def analyze(
        self,
        target_ticker: str,
        peer_tickers: list[str],
        registry: ProviderRegistry,
    ) -> CompsResult:
        """
        1. Fetch FinancialRatios + CompanyProfile for target + all peers
        2. Build CompMetric for each
        3. Calculate medians (ignore None values)
        4. Calculate implied values for target
        5. Return CompsResult
        """

    @staticmethod
    def _median(values: list[float]) -> float | None:
        """Calculate median, filtering out None/NaN."""
```

---

## Task 2: Scenario DB Model

**File:** `app/models/scenario.py`

```python
class Scenario(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scenarios"

    stock_id: UUID FK -> stocks.id (CASCADE)
    user_id: UUID FK -> users.id (CASCADE)
    name: str  # "Bull", "Base", "Bear"
    case_type: str  # Enum-like: "bull", "base", "bear", "custom"
    probability: float = 0.0  # Weight for weighted avg (0.0 to 1.0)

    # Key assumptions (denormalized for quick comparison)
    revenue_growth_rate: float  # Avg annual
    operating_margin: float
    wacc: float
    terminal_growth_rate: float

    # Valuation outputs (computed, stored for fast retrieval)
    dcf_per_share: float | None  # Use Optional for 3.9
    comps_implied_pe: float | None
    comps_implied_ev_ebitda: float | None

    # Link to full assumption set (optional)
    assumption_set_id: UUID FK -> assumption_sets.id (SET NULL, nullable)
```

Add to `app/models/__init__.py`.

---

## Task 3: Scenario API

**File:** `app/api/v1/scenarios.py`

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/scenarios/{ticker}` | Create a scenario |
| `GET` | `/scenarios/{ticker}` | List scenarios for a stock (returns all cases) |
| `GET` | `/scenarios/{ticker}/summary` | Weighted avg target price across scenarios |
| `PUT` | `/scenarios/{scenario_id}` | Update a scenario |
| `DELETE` | `/scenarios/{scenario_id}` | Delete a scenario |

Request schemas:
```python
class ScenarioCreate(BaseModel):
    name: str
    case_type: str  # "bull", "base", "bear", "custom"
    probability: float = 0.0
    revenue_growth_rate: float
    operating_margin: float
    wacc: float
    terminal_growth_rate: float = 0.025
    dcf_per_share: float | None = None  # Use Optional
    comps_implied_pe: float | None = None
    comps_implied_ev_ebitda: float | None = None
    assumption_set_id: str | None = None
```

The `/summary` endpoint should:
1. Fetch all scenarios for the ticker
2. Calculate weighted average price: `sum(probability * dcf_per_share)` for scenarios with DCF values
3. Return target price + breakdown

Register router in `app/api/v1/__init__.py`.

---

## Task 4: Excel Export

**File:** `app/services/model/export.py`

```python
class ModelExporter:
    def export_to_excel(
        self,
        ticker: str,
        model_output: ModelOutput,  # From engine.py (GLM will create this)
        dcf_result: DCFResult,  # From dcf.py (GLM will create this)
        comps_result: CompsResult,
        scenarios: list[Scenario],
        output_path: str,
    ) -> str:
        """
        Create an Excel workbook with tabs:
        1. "Projections" — ModelOutput.projections as a table
        2. "DCF" — DCF assumptions + result
        3. "Comps" — Peer comparison table
        4. "Scenarios" — All scenarios with weighted target

        Returns: path to the created .xlsx file
        """
```

Since GLM's `ModelOutput` and `DCFResult` may not exist yet when you're building, define stub imports:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.model.engine import ModelOutput
    from app.services.model.dcf import DCFResult
```

And accept them as `Any` at runtime with a comment explaining the dependency.

Also add an API endpoint:

**File:** `app/api/v1/export.py`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/export/{ticker}/model` | Download Excel model for a ticker |

This endpoint should return a `FileResponse`. For now, wire it to create a minimal Excel with just the comps + scenarios tabs (the full model will be wired when GLM's engine exists).

---

## Task 5: Tests

**File:** `tests/test_comps.py` (~6 tests)

```python
class TestCompsEngine:
    def test_median_calculation(self):
        """Median of [10, 20, 30] = 20."""

    def test_median_with_nones(self):
        """None values are filtered out."""

    def test_median_empty_list(self):
        """Empty list returns None."""

    @pytest.mark.asyncio
    async def test_analyze_with_mocked_providers(self):
        """Mock registry, verify CompMetric built correctly."""

    @pytest.mark.asyncio
    async def test_implied_value_calculation(self):
        """Implied PE value = median_pe * target_eps."""

    @pytest.mark.asyncio
    async def test_analyze_with_one_peer(self):
        """Single peer = median equals that peer's value."""
```

**File:** `tests/test_scenarios.py` (~4 tests)

```python
class TestScenarioWeighting:
    def test_weighted_average_price(self):
        """Bull 25% @ $200 + Base 50% @ $150 + Bear 25% @ $100 = $150."""

    def test_zero_probability_excluded(self):
        """Scenarios with 0 probability don't affect average."""

    def test_missing_dcf_excluded(self):
        """Scenarios without dcf_per_share are excluded from weighting."""

    def test_single_scenario(self):
        """Single scenario = that scenario's value."""
```

---

## Constraints

1. Use `from __future__ import annotations` in every file
2. Use `Optional[X]` not `X | None` for Python 3.9 compatibility
3. Follow existing code style (see `stocks.py`, `financial.py`)
4. The comps engine tests should mock the ProviderRegistry — don't call real APIs
5. After finishing, run: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
6. All tests (existing 110 + your new ones) must pass
