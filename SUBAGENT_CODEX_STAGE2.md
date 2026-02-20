# Sub-Agent Work Package: Codex — Stage 2 (Notes CRUD + Comp Suggestions)

## Objective

Build the analyst notes system (CRUD + AI-powered extraction) and the comp suggestion engine that recommends peer companies using sector data and LLM intelligence.

## Environment

- Python 3.9 (`from __future__ import annotations` everywhere, use `Optional[X]` not `X | None`)
- FastAPI + SQLAlchemy async + Pydantic v2
- Virtual env: `source backend/venv/bin/activate`
- Run tests: `cd backend && python -m pytest tests/ -v`
- All 135 existing tests must continue to pass

## Codebase Context

### Existing DB patterns

```python
# app/models/base.py
class Base: ...          # SQLAlchemy declarative base
class UUIDMixin: ...     # Adds `id` as UUID primary key
class TimestampMixin: ... # Adds `created_at`, `updated_at`

# ForeignKey pattern:
stock_id: Mapped[uuid.UUID] = mapped_column(
    UUID(as_uuid=True), ForeignKey("stocks.id", ondelete="CASCADE"),
    nullable=False, index=True,
)
```

### Existing API patterns (`app/api/v1/stocks.py`, `scenarios.py`)

```python
router = APIRouter(prefix="/notes", tags=["notes"])

@router.post("/{ticker}")
async def create_note(
    ticker: str,
    data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NoteResponse: ...
```

### LLM integration

```python
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType, LLMMessage, LLMRole

# For extracting structured data from notes:
response = await router.complete(
    task_type=TaskType.NOTE_EXTRACTION,
    messages=[LLMMessage(role=LLMRole.USER, content="...")],
    json_mode=True,
)

# For suggesting comp companies:
response = await router.complete(
    task_type=TaskType.COMPANY_COMPARISON,
    messages=[LLMMessage(role=LLMRole.USER, content="...")],
    json_mode=True,
)
```

### Prompt templates available:
- `TEMPLATES["note_extraction"]` — placeholders: `note_text`, `company_name`, `ticker`
- `TEMPLATES["company_comparison"]` — placeholders: `company_a`, `company_b`, `financial_data_a`, `financial_data_b`

### Data layer for comp suggestions:

```python
from app.services.data.registry import get_fundamentals, get_profiles

profiles = get_profiles()
profile = await profiles.get_company_profile("AAPL")
# profile.sector, profile.industry, profile.market_cap

fundamentals = get_fundamentals()
ratios = await fundamentals.get_financial_ratios("AAPL")
```

---

## Task 1: Note DB Model

**File:** `app/models/note.py`

```python
class Note(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notes"

    stock_id: UUID FK -> stocks.id (CASCADE), indexed
    user_id: UUID FK -> users.id (CASCADE), indexed

    # Content
    title: str (String(300), nullable=False)
    content: str (Text, nullable=False)  # Markdown-formatted
    note_type: str (String(50), nullable=True)
        # "earnings_call", "industry_note", "management_meeting",
        # "research_report", "personal", "other"

    # AI-extracted data (populated by note extraction service)
    extracted_sentiment: str (String(20), nullable=True)  # bullish / bearish / neutral
    extracted_key_points: str (Text, nullable=True)  # JSON list of strings
    extracted_price_target: float (nullable=True)
    extracted_metrics: str (Text, nullable=True)  # JSON dict of metric -> value
    is_ai_processed: bool (default=False)

    # Optional tagging
    tags: str (Text, nullable=True)  # JSON list of strings
```

Add to `app/models/__init__.py`.

---

## Task 2: Notes CRUD API

**File:** `app/api/v1/notes.py`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/notes/{ticker}` | Create a note for a stock |
| `GET` | `/notes/{ticker}` | List notes for a stock |
| `GET` | `/notes/detail/{note_id}` | Get a single note |
| `PUT` | `/notes/{note_id}` | Update a note |
| `DELETE` | `/notes/{note_id}` | Delete a note |
| `POST` | `/notes/{note_id}/extract` | Run AI extraction on a note |

Request/Response schemas:

```python
class NoteCreate(BaseModel):
    title: str
    content: str
    note_type: Optional[str] = None
    tags: Optional[list[str]] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    note_type: Optional[str] = None
    tags: Optional[list[str]] = None

class NoteResponse(BaseModel):
    id: str
    stock_id: str
    title: str
    content: str
    note_type: Optional[str]
    tags: Optional[list[str]]  # Parsed from JSON
    extracted_sentiment: Optional[str]
    extracted_key_points: Optional[list[str]]  # Parsed from JSON
    extracted_price_target: Optional[float]
    extracted_metrics: Optional[dict]  # Parsed from JSON
    is_ai_processed: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class ExtractionResult(BaseModel):
    sentiment: str
    key_points: list[str]
    price_target: Optional[float]
    metrics: dict  # e.g. {"revenue_growth": 0.15, "margin_expansion": true}
```

For the `/extract` endpoint:
1. Fetch the note from DB
2. Build prompt using `note_extraction` template
3. Call `LLMRouter.complete()` with `TaskType.NOTE_EXTRACTION`, `json_mode=True`
4. Parse response into `ExtractionResult`
5. Update note's extracted fields + set `is_ai_processed = True`
6. Return updated `NoteResponse`

**Register** the router in `app/api/v1/router.py`.

---

## Task 3: Comp Suggestion Service

**File:** `app/services/model/comp_suggestions.py`

```python
class CompSuggestion(BaseModel):
    ticker: str
    company_name: str
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    match_reason: str  # Why this company is a good comp
    similarity_score: float  # 0.0 to 1.0

class CompSuggestionEngine:
    def __init__(self, llm_router: LLMRouter):
        self._llm = llm_router

    async def suggest_peers(
        self,
        ticker: str,
        limit: int = 5,
    ) -> list[CompSuggestion]:
        """
        Hybrid approach:
        1. Get target's profile (sector, industry, market_cap)
        2. Ask LLM to suggest comparable companies with rationale
        3. Validate each suggestion by fetching its profile
        4. Return validated suggestions with match reasons
        """

    async def _get_llm_suggestions(
        self,
        ticker: str,
        company_name: str,
        sector: str,
        industry: str,
        market_cap: float,
    ) -> list[dict]:
        """
        Use COMPANY_COMPARISON task type.
        Prompt: "Given {company_name} ({ticker}) in {sector}/{industry}
        with market cap ${market_cap}B, suggest {limit} comparable public
        companies. Return JSON array with ticker, reason, similarity_score."
        """
```

Add an endpoint to the existing assumptions or a new comps API:

**File:** `app/api/v1/comps.py`

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/comps/{ticker}/suggest` | AI-suggest peer companies |
| `POST` | `/comps/{ticker}/analyze` | Run full comps analysis (uses existing `CompsEngine`) |

The `/suggest` endpoint calls `CompSuggestionEngine.suggest_peers()`.
The `/analyze` endpoint wraps `CompsEngine.analyze()` from `app/services/model/comps.py` (already built).

**Register** the router in `app/api/v1/router.py`.

---

## Task 4: Tests

**File:** `tests/test_notes.py` (~8 tests)

```python
class TestNoteModel:
    def test_model_fields(self):
        """All required columns exist on Note."""

    def test_tablename(self):
        """Table name is 'notes'."""

    def test_tags_json_round_trip(self):
        """Tags stored as JSON, parsed back to list."""

class TestNoteExtraction:
    @pytest.mark.asyncio
    async def test_extraction_parses_json(self):
        """Mock LLM returns valid JSON, parsed into ExtractionResult."""

    @pytest.mark.asyncio
    async def test_extraction_handles_bad_json(self):
        """Malformed LLM response → graceful fallback."""

    @pytest.mark.asyncio
    async def test_extraction_updates_note_fields(self):
        """After extraction, note.is_ai_processed is True."""
```

**File:** `tests/test_comp_suggestions.py` (~5 tests)

```python
class TestCompSuggestionEngine:
    @pytest.mark.asyncio
    async def test_suggest_peers_returns_suggestions(self):
        """Mock LLM + registry, verify CompSuggestion list."""

    @pytest.mark.asyncio
    async def test_suggest_peers_validates_tickers(self):
        """Invalid ticker from LLM is filtered out."""

    @pytest.mark.asyncio
    async def test_suggest_peers_respects_limit(self):
        """Returns at most `limit` suggestions."""

    @pytest.mark.asyncio
    async def test_handles_llm_error(self):
        """LLM failure → empty list, not crash."""

    @pytest.mark.asyncio
    async def test_similarity_score_range(self):
        """All similarity_scores are between 0.0 and 1.0."""
```

---

## Constraints

1. `from __future__ import annotations` in every file
2. `Optional[X]` not `X | None` for Python 3.9
3. Follow existing code style from `stocks.py`, `scenarios.py`
4. Mock `LLMRouter`, `get_profiles()`, `get_fundamentals()` in tests — no real API calls
5. After finishing: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
6. All tests (135 existing + your new ones) must pass
