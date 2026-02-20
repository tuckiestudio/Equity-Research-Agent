# Sub-Agent Work Package: Codex — Stage 3 (Watch Items + Assumption Waterfall)

## Objective

Build the watch items system (AI-generated catalysts and monitoring triggers) and the assumption waterfall endpoint that visualizes how assumption changes flow through to valuation.

## Environment

- Python 3.9 (`from __future__ import annotations`, use `Optional[X]` not `X | None`)
- FastAPI + SQLAlchemy async + Pydantic v2
- Virtual env: `source backend/venv/bin/activate`
- Run tests: `cd backend && python -m pytest tests/ -v`
- All 159 existing tests must continue to pass

## Codebase Context

### LLM integration

```python
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType, LLMMessage, LLMRole
from app.services.llm.prompts.templates import get_watch_items_template

# get_watch_items_template() placeholders:
#   ticker, company_name, investment_thesis, upcoming_events

response = await router.complete(
    task_type=TaskType.WATCH_ITEMS,
    messages=[...],
    json_mode=True,
)
```

### Model engine (from Stage 1 — for waterfall computation)

```python
from app.services.model.engine import ModelEngine, ModelOutput
from app.services.model.dcf import DCFCalculator, DCFResult
from app.models.assumption import AssumptionSet

engine = ModelEngine()
model_output = engine.compute(assumptions, income, balance, cashflow)

calculator = DCFCalculator()
dcf_result = calculator.calculate(model_output, assumptions, price, shares, net_debt)
```

### Data layer

```python
from app.services.data.registry import get_profiles, get_fundamentals
```

### DB patterns: `app/models/base.py` → `Base`, `UUIDMixin`, `TimestampMixin`
### API patterns: `app/api/v1/scenarios.py` — follow the same router/schema/endpoint style

---

## Task 1: Watch Item DB Model

**File:** `app/models/watch_item.py`

```python
class WatchItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "watch_items"

    stock_id: UUID FK -> stocks.id (CASCADE), indexed
    user_id: UUID FK -> users.id (CASCADE), indexed

    # Content
    title: str (String(300))  # e.g. "Q3 Earnings Report"
    description: str (Text)  # Detailed description of what to watch for
    category: str (String(50))
        # "earnings", "product_launch", "regulatory",
        # "macro", "competitive", "management", "technical", "other"
    
    # Timing
    expected_date: date (nullable)  # When this catalyst might occur
    is_recurring: bool (default=False)  # e.g. quarterly earnings

    # Impact assessment
    potential_impact: str (String(20))  # "high", "medium", "low"
    impact_direction: str (String(20))  # "bullish", "bearish", "uncertain"
    affected_assumptions: str (Text, nullable)
        # JSON list of assumption fields this could affect
        # e.g. ["revenue_growth_rates", "operating_margin"]

    # Status
    status: str (String(20), default="active")
        # "active", "triggered", "expired", "dismissed"
    triggered_at: datetime (nullable)
    trigger_outcome: str (Text, nullable)  # What actually happened

    # AI metadata
    generated_by: str (String(50))  # "ai" or "manual"
    confidence: float (nullable)  # How confident the AI is this matters (0-1)
```

Add to `app/models/__init__.py`.

---

## Task 2: Watch Service

**File:** `app/services/thesis/watch.py`

```python
class WatchItemSuggestion(BaseModel):
    """Parsed watch item from LLM output."""
    title: str
    description: str
    category: str
    expected_date: Optional[date]
    potential_impact: str  # high / medium / low
    impact_direction: str  # bullish / bearish / uncertain
    affected_assumptions: list[str]
    confidence: float

class WatchService:
    def __init__(self, llm_router: LLMRouter):
        self._llm = llm_router

    async def generate_watch_items(
        self,
        ticker: str,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        investment_thesis: Optional[str],
        db: AsyncSession,
        limit: int = 5,
    ) -> list[WatchItem]:
        """
        1. Fetch company profile for context
        2. Build upcoming_events string (check for known dates like earnings)
        3. Render watch_items template
        4. Call LLMRouter.complete() with TaskType.WATCH_ITEMS, json_mode=True
        5. Parse response into list of WatchItemSuggestion
        6. Save each as WatchItem to DB
        7. Return the list
        """

    async def get_active_items(
        self,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[WatchItem]:
        """Get all active watch items, ordered by expected_date ASC (soonest first)."""

    async def trigger_item(
        self,
        watch_item_id: uuid.UUID,
        outcome: str,
        db: AsyncSession,
    ) -> WatchItem:
        """Mark a watch item as triggered with outcome text."""

    async def dismiss_item(
        self,
        watch_item_id: uuid.UUID,
        db: AsyncSession,
    ) -> WatchItem:
        """Mark a watch item as dismissed."""
```

---

## Task 3: Watch API

**File:** `app/api/v1/watch.py`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/watch/{ticker}/generate` | AI-generate watch items |
| `GET` | `/watch/{ticker}` | List active watch items |
| `POST` | `/watch/{ticker}` | Create manual watch item |
| `PUT` | `/watch/{watch_id}/trigger` | Mark item as triggered |
| `PUT` | `/watch/{watch_id}/dismiss` | Dismiss item |
| `DELETE` | `/watch/{watch_id}` | Delete item |

Request schemas:
```python
class WatchItemCreate(BaseModel):
    title: str
    description: str
    category: str = "other"
    expected_date: Optional[date] = None
    is_recurring: bool = False
    potential_impact: str = "medium"
    impact_direction: str = "uncertain"
    affected_assumptions: Optional[list[str]] = None

class WatchItemTrigger(BaseModel):
    outcome: str  # What actually happened
```

Response schema:
```python
class WatchItemResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    expected_date: Optional[date]
    is_recurring: bool
    potential_impact: str
    impact_direction: str
    affected_assumptions: Optional[list[str]]  # Parsed from JSON
    status: str
    triggered_at: Optional[datetime]
    trigger_outcome: Optional[str]
    generated_by: str
    confidence: Optional[float]
    created_at: datetime
    model_config = {"from_attributes": True}
```

**Register** the router in `app/api/v1/router.py`.

---

## Task 4: Assumption Waterfall Endpoint

**File:** `app/api/v1/waterfall.py`

This endpoint shows how changing each assumption individually impacts the DCF per-share value. It's used by the frontend to render a waterfall chart.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/waterfall/{ticker}` | Get assumption impact waterfall data |

Logic:
```python
@router.get("/{ticker}")
async def get_assumption_waterfall(
    ticker: str,
    assumption_id: Optional[str] = None,  # Use active if not provided
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WaterfallResponse:
    """
    1. Get the assumption set (active or by ID)
    2. Fetch latest financials (income, balance, cashflow)
    3. Get current stock price
    4. Compute base case DCF (using ModelEngine + DCFCalculator)
    5. For each key assumption, tweak it ±10% and recompute DCF:
       - revenue_growth_rates (avg)
       - operating_margin
       - wacc
       - terminal_growth_rate
       - capex_as_pct_revenue
       - tax_rate
    6. Return the impact of each tweak vs base case
    """
```

Response schema:
```python
class WaterfallItem(BaseModel):
    assumption_name: str  # e.g. "Revenue Growth"
    base_value: float  # Current assumption value
    tweaked_value: float  # +10% value
    base_dcf_per_share: float
    tweaked_dcf_per_share: float
    impact: float  # absolute $ change
    impact_pct: float  # % change from base

class WaterfallResponse(BaseModel):
    ticker: str
    base_dcf_per_share: float
    items: list[WaterfallItem]
```

**Register** the router in `app/api/v1/router.py`.

---

## Task 5: Tests

**File:** `tests/test_watch.py` (~8 tests)

```python
class TestWatchItemModel:
    def test_model_fields(self):
        """All required columns exist."""

    def test_tablename(self):
        """Table name is 'watch_items'."""

    def test_affected_assumptions_json(self):
        """JSON round-trip for affected_assumptions."""

class TestWatchService:
    @pytest.mark.asyncio
    async def test_generate_returns_items(self):
        """Mock LLM, verify WatchItem list."""

    @pytest.mark.asyncio
    async def test_generate_handles_llm_error(self):
        """LLM failure → empty list."""

    @pytest.mark.asyncio
    async def test_trigger_item_updates_status(self):
        """Status set to 'triggered', outcome stored."""

    @pytest.mark.asyncio
    async def test_dismiss_item_updates_status(self):
        """Status set to 'dismissed'."""
```

**File:** `tests/test_waterfall.py` (~4 tests)

```python
class TestAssumptionWaterfall:
    def test_wacc_increase_lowers_dcf(self):
        """Higher WACC → lower DCF per share."""

    def test_growth_increase_raises_dcf(self):
        """Higher growth → higher DCF per share."""

    def test_impact_pct_calculation(self):
        """impact_pct = (tweaked - base) / base."""

    def test_all_assumptions_covered(self):
        """Waterfall includes all 6 key assumptions."""
```

For waterfall tests, directly instantiate `ModelEngine` and `DCFCalculator` (they're pure computation) — build synthetic `AssumptionSet`-like objects to test the math.

---

## Constraints

1. `from __future__ import annotations` in every file
2. `Optional[X]` not `X | None` for Python 3.9
3. Follow existing code style from `scenarios.py`, `notes.py`
4. Mock `LLMRouter` and `get_profiles()` in watch tests
5. Waterfall tests can use real `ModelEngine`/`DCFCalculator` (sync, pure math)
6. After finishing: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
7. All tests (159 existing + your new ones) must pass
