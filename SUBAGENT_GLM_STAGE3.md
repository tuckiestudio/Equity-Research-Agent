# Sub-Agent Work Package: GLM — Stage 3 (Thesis Generation + Evolution)

## Objective

Build the investment thesis engine: initial thesis generation from financial data + news, thesis versioning with an audit trail, and auto-update when new information arrives.

## Environment

- Python 3.9 (`from __future__ import annotations`, use `Optional[X]` not `X | None`)
- FastAPI + SQLAlchemy async + Pydantic v2
- Virtual env: `source backend/venv/bin/activate`
- Run tests: `cd backend && python -m pytest tests/ -v`
- All 159 existing tests must continue to pass

## Codebase Context

### LLM integration (already working)

```python
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType, LLMMessage, LLMRole

router = LLMRouter()

# For generating thesis:
response = await router.complete(
    task_type=TaskType.THESIS_GENERATION,
    messages=[...],
)

# For updating thesis:
response = await router.complete(
    task_type=TaskType.THESIS_UPDATE,
    messages=[...],
)
```

### Prompt templates (already exist — see `app/services/llm/prompts/templates.py`)

```python
from app.services.llm.prompts.templates import (
    get_thesis_generation_template,
    get_thesis_update_template,
)

# get_thesis_generation_template() placeholders:
#   ticker, company_name, business_description,
#   financial_summary, recent_news, industry_context

# get_thesis_update_template() placeholders:
#   ticker, existing_thesis, new_information, time_elapsed
```

### Data layer (for gathering context)

```python
from app.services.data.registry import get_fundamentals, get_profiles, get_news

profiles = get_profiles()
profile = await profiles.get_company_profile("AAPL")

fundamentals = get_fundamentals()
income = await fundamentals.get_income_statement("AAPL", limit=1)
ratios = await fundamentals.get_financial_ratios("AAPL")

news = get_news()
articles = await news.get_news("AAPL", limit=10)
```

### News analysis (from Stage 2 — GLM built this)

```python
from app.services.news.service import NewsService
from app.models.news_analysis import NewsAnalysis
# Can query recent news analyses for a stock to inform thesis
```

### DB patterns: `app/models/base.py` → `Base`, `UUIDMixin`, `TimestampMixin`
### API patterns: `app/api/v1/scenarios.py` — follow the same router/schema/endpoint style

---

## Task 1: Thesis DB Model

**File:** `app/models/thesis.py`

```python
class Thesis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "theses"

    stock_id: UUID FK -> stocks.id (CASCADE), indexed
    user_id: UUID FK -> users.id (CASCADE), indexed

    # Thesis content
    title: str (String(300))  # e.g. "AAPL: Innovation Premium Justified"
    summary: str (Text)  # 2-3 sentence executive summary
    full_text: str (Text)  # Full thesis document (markdown)
    stance: str (String(20))  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0 to 1.0

    # Valuation context
    target_price: float (nullable)
    current_price_at_generation: float (nullable)
    upside_pct: float (nullable)

    # Metadata
    version: int (default=1)
    is_active: bool (default=True)  # Only one active thesis per stock+user
    generated_by: str (String(50))  # "ai", "manual", "ai_updated"
    llm_model_used: str (String(100), nullable)
```

Add to `app/models/__init__.py`.

---

## Task 2: Thesis Change Audit Trail

**File:** `app/models/thesis_change.py`

```python
class ThesisChange(Base, UUIDMixin):
    __tablename__ = "thesis_changes"

    thesis_id: UUID FK -> theses.id (CASCADE), indexed
    user_id: UUID FK -> users.id (SET NULL, nullable)

    # What changed
    change_type: str (String(50))
        # "created", "stance_changed", "target_updated",
        # "confidence_changed", "full_rewrite", "news_driven_update"
    previous_stance: str (String(20), nullable)
    new_stance: str (String(20), nullable)
    previous_target_price: float (nullable)
    new_target_price: float (nullable)
    previous_confidence: float (nullable)
    new_confidence: float (nullable)

    # Context
    trigger: str (Text, nullable)  # What triggered the change (e.g. news headline, earnings)
    change_summary: str (Text)  # AI-generated summary of what changed and why
    version_from: int
    version_to: int

    created_at: datetime (with timezone, server_default=func.now(), indexed)
```

Add to `app/models/__init__.py`.

---

## Task 3: Thesis Service

**File:** `app/services/thesis/generator.py`

Also create `app/services/thesis/__init__.py` (empty).

```python
class ThesisContent(BaseModel):
    """Parsed thesis from LLM output."""
    title: str
    summary: str
    full_text: str
    stance: str  # bullish / bearish / neutral
    confidence: float  # 0.0 to 1.0
    target_price: Optional[float]
    key_risks: list[str]
    key_catalysts: list[str]

class ThesisService:
    def __init__(self, llm_router: LLMRouter):
        self._llm = llm_router

    async def generate_thesis(
        self,
        ticker: str,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Thesis:
        """
        Generate an initial investment thesis:
        1. Fetch company profile, financials (income, ratios), recent news
        2. Build a financial summary string
        3. Render the thesis_generation template
        4. Call LLMRouter.complete() with TaskType.THESIS_GENERATION
        5. Parse response into ThesisContent
        6. Deactivate any existing active thesis for this stock+user
        7. Save new Thesis to DB with version=1
        8. Create ThesisChange with change_type="created"
        9. Return the thesis
        """

    async def update_thesis(
        self,
        thesis_id: uuid.UUID,
        new_information: str,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Thesis:
        """
        Update an existing thesis with new information:
        1. Fetch existing thesis
        2. Render thesis_update template with existing_thesis + new_information
        3. Call LLMRouter.complete() with TaskType.THESIS_UPDATE
        4. Parse updated thesis
        5. Detect changes (stance, target, confidence)
        6. Update the thesis record (increment version)
        7. Create ThesisChange with detected changes
        8. Return updated thesis
        """

    async def get_active_thesis(
        self,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> Optional[Thesis]:
        """Get the active thesis for a stock+user."""

    async def get_thesis_history(
        self,
        thesis_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[ThesisChange]:
        """Get the change history for a thesis, ordered by created_at."""

    async def get_thesis_timeline(
        self,
        stock_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> list[dict]:
        """
        Build a timeline of thesis evolution:
        Returns list of {date, version, stance, confidence, target_price, change_summary}
        Useful for frontend timeline visualization.
        """

    def _parse_thesis_content(self, raw_text: str) -> ThesisContent:
        """
        Parse LLM output into structured thesis.
        Try JSON first, fall back to text parsing.
        Handle gracefully — never crash.
        """

    def _detect_changes(
        self, old: Thesis, new_content: ThesisContent
    ) -> dict:
        """Compare old thesis with new content, return change details."""
```

---

## Task 4: Thesis API

**File:** `app/api/v1/thesis.py`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/thesis/{ticker}/generate` | Generate initial thesis |
| `GET` | `/thesis/{ticker}` | Get active thesis |
| `PUT` | `/thesis/{thesis_id}/update` | Update thesis with new info |
| `GET` | `/thesis/{thesis_id}/history` | Get change audit trail |
| `GET` | `/thesis/{ticker}/timeline` | Get thesis evolution timeline |
| `PUT` | `/thesis/{thesis_id}` | Manual edit (direct update without AI) |

Request schemas:
```python
class ThesisUpdateRequest(BaseModel):
    new_information: str  # What changed? (news, earnings, etc.)

class ThesisManualEdit(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    full_text: Optional[str] = None
    stance: Optional[str] = None
    confidence: Optional[float] = None
    target_price: Optional[float] = None
```

Response schemas:
```python
class ThesisResponse(BaseModel):
    id: str
    stock_id: str
    title: str
    summary: str
    full_text: str
    stance: str
    confidence: float
    target_price: Optional[float]
    current_price_at_generation: Optional[float]
    upside_pct: Optional[float]
    version: int
    is_active: bool
    generated_by: str
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ThesisChangeResponse(BaseModel):
    id: str
    change_type: str
    previous_stance: Optional[str]
    new_stance: Optional[str]
    previous_target_price: Optional[float]
    new_target_price: Optional[float]
    change_summary: str
    version_from: int
    version_to: int
    created_at: datetime

class ThesisTimelineItem(BaseModel):
    date: datetime
    version: int
    stance: str
    confidence: float
    target_price: Optional[float]
    change_summary: str
```

**Register** the router in `app/api/v1/router.py`.

---

## Task 5: Tests

**File:** `tests/test_thesis.py` (~10 tests)

```python
class TestThesisModel:
    def test_model_fields(self):
        """Verify all required columns exist."""

    def test_tablename(self):
        """Table name is 'theses'."""

class TestThesisChangeModel:
    def test_model_fields(self):
        """Verify all required columns exist."""

    def test_tablename(self):
        """Table name is 'thesis_changes'."""

class TestThesisService:
    @pytest.mark.asyncio
    async def test_generate_thesis_calls_llm(self):
        """Mock LLM + data providers, verify thesis is created."""

    @pytest.mark.asyncio
    async def test_generate_thesis_deactivates_old(self):
        """Previous active thesis is deactivated."""

    @pytest.mark.asyncio
    async def test_update_thesis_increments_version(self):
        """Version incremented on update."""

    @pytest.mark.asyncio
    async def test_update_thesis_creates_change_record(self):
        """ThesisChange created with correct change_type."""

    @pytest.mark.asyncio
    async def test_detect_stance_change(self):
        """Stance change detected and logged."""

    @pytest.mark.asyncio
    async def test_parse_thesis_handles_bad_response(self):
        """Malformed LLM output → graceful defaults."""
```

---

## Constraints

1. `from __future__ import annotations` in every file
2. `Optional[X]` not `X | None` for Python 3.9
3. Follow existing code style from `scenarios.py`, `news.py`
4. Mock `LLMRouter`, `get_fundamentals()`, `get_profiles()`, `get_news()` in tests
5. After finishing: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
6. All tests (159 existing + your new ones) must pass
