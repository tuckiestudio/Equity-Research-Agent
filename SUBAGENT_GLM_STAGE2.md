# Sub-Agent Work Package: GLM — Stage 2 (News Ingestion + AI Analysis)

## Objective

Build the news ingestion service that fetches company news, runs AI-powered analysis (relevance scoring, impact assessment, thesis alignment), and stores results with a searchable API.

## Environment

- Python 3.9 (`from __future__ import annotations` everywhere, use `Optional[X]` not `X | None`)
- FastAPI + SQLAlchemy async + Pydantic v2
- Virtual env: `source backend/venv/bin/activate`
- Run tests: `cd backend && python -m pytest tests/ -v`
- All 135 existing tests must continue to pass

## Codebase Context

### News data already flows through the provider layer

```python
# app/services/data/protocols.py
class NewsProvider(Protocol):
    async def get_news(self, ticker: str, limit: int = 20) -> List[NewsItem]: ...

# app/schemas/financial.py
class NewsItem(BaseModel):
    headline: str
    summary: Optional[str]
    source_name: str
    source_url: Optional[str]
    ticker: Optional[str]
    published_at: datetime
    sentiment_score: Optional[float]   # -1.0 to 1.0
    sentiment_label: Optional[str]     # positive, negative, neutral
    relevance_score: Optional[float]   # 0.0 to 1.0
    source: str
    fetched_at: datetime

# Usage:
from app.services.data.registry import get_news
news_provider = get_news()
articles = await news_provider.get_news("AAPL", limit=50)
```

### LLM integration (already working)

```python
from app.services.llm.router import LLMRouter
from app.services.llm.types import TaskType, LLMMessage, LLMRole

router = LLMRouter()
response = await router.complete(
    task_type=TaskType.NEWS_ANALYSIS,
    messages=[LLMMessage(role=LLMRole.USER, content="...")],
    json_mode=True,
)
# response.content is a JSON string
```

### Prompt template available: `TEMPLATES["news_analysis"]`
Placeholders: `headline`, `summary`, `company_name`, `ticker`, `current_thesis`

### DB patterns: `app/models/base.py` → `Base`, `UUIDMixin`, `TimestampMixin`

---

## Task 1: News Analysis DB Model

**File:** `app/models/news_analysis.py`

```python
class NewsAnalysis(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "news_analyses"

    stock_id: UUID FK -> stocks.id (CASCADE), indexed
    user_id: UUID FK -> users.id (SET NULL, nullable), indexed

    # Original article data
    headline: str (Text)
    summary: str (Text, nullable)
    source_name: str (String(200))
    source_url: str (Text, nullable)
    published_at: datetime (with timezone)

    # AI analysis results
    relevance_score: float  # 0.0 to 1.0, how relevant to the stock
    impact_score: float  # -1.0 to 1.0, negative=bearish, positive=bullish
    impact_label: str  # "bullish", "bearish", "neutral"
    thesis_alignment: str  # "supports", "challenges", "neutral"
    key_points: str  # JSON list of strings
    affected_metrics: str  # JSON list of affected line items (e.g. ["revenue", "margins"])
    ai_summary: str (Text)  # LLM-generated 2-3 sentence summary

    # Provider metadata
    provider_sentiment_score: float (nullable)  # Original provider sentiment
    data_source: str  # e.g. "finnhub", "fmp"
```

Add to `app/models/__init__.py`.

---

## Task 2: News Service

**File:** `app/services/news/service.py`

Also create `app/services/news/__init__.py` (empty).

```python
class NewsAnalysisResult(BaseModel):
    relevance_score: float
    impact_score: float
    impact_label: str  # bullish / bearish / neutral
    thesis_alignment: str  # supports / challenges / neutral
    key_points: list[str]
    affected_metrics: list[str]
    ai_summary: str

class NewsService:
    def __init__(self, llm_router: LLMRouter):
        self._llm = llm_router

    async def fetch_and_analyze(
        self,
        ticker: str,
        stock_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        current_thesis: Optional[str],  # existing thesis text for alignment check
        db: AsyncSession,
        limit: int = 20,
    ) -> list[NewsAnalysis]:
        """
        1. Fetch news via get_news() from the data registry
        2. For each article, call _analyze_article()
        3. Save to DB as NewsAnalysis records
        4. Return the list of analyses
        """

    async def _analyze_article(
        self,
        article: NewsItem,
        ticker: str,
        company_name: str,
        current_thesis: Optional[str],
    ) -> NewsAnalysisResult:
        """
        Build prompt using the news_analysis template.
        Call LLMRouter.complete() with TaskType.NEWS_ANALYSIS, json_mode=True.
        Parse response JSON into NewsAnalysisResult.
        Handle parsing errors gracefully (return neutral defaults).
        """

    async def get_recent_analyses(
        self,
        stock_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        db: AsyncSession,
        limit: int = 20,
        min_relevance: float = 0.0,
    ) -> list[NewsAnalysis]:
        """Query DB for recent analyses, ordered by published_at DESC."""

    async def get_sentiment_summary(
        self,
        stock_id: uuid.UUID,
        db: AsyncSession,
        days: int = 30,
    ) -> dict:
        """
        Aggregate sentiment over the last N days:
        - average impact_score
        - count of bullish / bearish / neutral articles
        - top key_points by frequency
        """
```

---

## Task 3: News API

**File:** `app/api/v1/news.py`

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/news/{ticker}/analyze` | Fetch + analyze news for a ticker |
| `GET` | `/news/{ticker}` | Get analyzed news (from DB) |
| `GET` | `/news/{ticker}/sentiment` | Get sentiment summary |
| `GET` | `/news/{ticker}/{analysis_id}` | Get single analysis detail |

Response schemas:
```python
class NewsAnalysisResponse(BaseModel):
    id: str
    headline: str
    summary: Optional[str]
    source_name: str
    source_url: Optional[str]
    published_at: datetime
    relevance_score: float
    impact_score: float
    impact_label: str
    thesis_alignment: str
    key_points: list[str]  # Parsed from JSON
    affected_metrics: list[str]
    ai_summary: str
    created_at: datetime
    model_config = {"from_attributes": True}

class SentimentSummaryResponse(BaseModel):
    ticker: str
    period_days: int
    avg_impact_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    total_articles: int
    top_key_points: list[str]
```

Query params for `GET /news/{ticker}`:
- `limit` (int, default 20)
- `min_relevance` (float, default 0.0)

**Register** the router in `app/api/v1/router.py`.

---

## Task 4: Tests

**File:** `tests/test_news_service.py` (~10 tests)

```python
class TestNewsService:
    @pytest.mark.asyncio
    async def test_analyze_article_returns_result(self):
        """Mock LLMRouter, verify NewsAnalysisResult fields."""

    @pytest.mark.asyncio
    async def test_analyze_article_with_thesis(self):
        """Thesis text is included in prompt when provided."""

    @pytest.mark.asyncio
    async def test_analyze_article_handles_bad_json(self):
        """Malformed LLM response → neutral defaults."""

    @pytest.mark.asyncio
    async def test_analyze_article_handles_llm_error(self):
        """LLM error → graceful fallback, not crash."""

    def test_sentiment_summary_aggregation(self):
        """Given a list of analyses, compute correct averages and counts."""

    def test_key_points_json_round_trip(self):
        """key_points stored as JSON, parsed back to list."""

    def test_affected_metrics_json_round_trip(self):
        """affected_metrics stored as JSON, parsed back to list."""

class TestNewsAnalysisModel:
    def test_model_fields(self):
        """Verify all required columns exist on NewsAnalysis."""

    def test_tablename(self):
        """Table name is 'news_analyses'."""

    def test_foreign_keys(self):
        """stock_id and user_id FKs are defined."""
```

---

## Constraints

1. `from __future__ import annotations` in every file
2. `Optional[X]` not `X | None` for Python 3.9
3. Follow existing code style from `stocks.py`, `assumptions.py`
4. Mock `get_news()` and `LLMRouter` in tests — no real API calls
5. After finishing: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
6. All tests (135 existing + your new ones) must pass
