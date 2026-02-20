# Sub-Agent Work Package: GLM-4.7 — Phase 2: Multi-LLM Service Layer

## Mission
Build the multi-LLM abstraction layer that lets the app route different analysis tasks to different AI models. This is the AI brain of the equity research agent.

## Context
The project already has:
- **Config:** `backend/app/core/config.py` — `settings.OPENAI_API_KEY`, `settings.ANTHROPIC_API_KEY`, `settings.GLM_API_KEY`, `settings.KIMI_API_KEY`
- **Error types:** `backend/app/core/errors.py` — use `ProviderError` and `RateLimitError`
- **Logging:** `backend/app/core/logging.py` — use `get_logger(__name__)`
- **Existing patterns:** See `services/data/protocols.py` and `services/data/registry.py` for how the data layer uses protocols + registry (follow this same pattern for LLMs)

## Important: Python Version
System Python is 3.9.6. Use `from __future__ import annotations` at the top of **every** file. Do NOT use `X | None` union syntax without it.

---

## Task 1: LLM Protocol + Base Types
**File:** `backend/app/services/llm/__init__.py`  
**File:** `backend/app/services/llm/protocols.py`  
**File:** `backend/app/services/llm/types.py`

### types.py — Shared types
```python
from __future__ import annotations
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

class LLMRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class LLMMessage(BaseModel):
    role: LLMRole
    content: str

class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: Optional[float] = None  # estimated cost
    finish_reason: Optional[str] = None

class TaskType(str, Enum):
    """Task types that map to specific models via the router."""
    THESIS_GENERATION = "thesis_generation"       # Complex reasoning → Claude Sonnet
    THESIS_UPDATE = "thesis_update"               # Update existing thesis
    NEWS_ANALYSIS = "news_analysis"               # Analyze news impact
    ASSUMPTION_GENERATION = "assumption_generation"  # Generate financial assumptions
    COMPANY_COMPARISON = "company_comparison"      # Compare companies
    NOTE_EXTRACTION = "note_extraction"            # Extract data from analyst notes
    WATCH_ITEMS = "watch_items"                    # Generate watch items / catalysts
    QUICK_SUMMARY = "quick_summary"               # Short summaries → Haiku/mini
    DATA_FORMATTING = "data_formatting"            # Structured output → GPT-4o-mini
```

### protocols.py — Provider interface
```python
from __future__ import annotations
from typing import List, Optional, Protocol, runtime_checkable
from app.services.llm.types import LLMMessage, LLMResponse

@runtime_checkable
class LLMProvider(Protocol):
    provider_name: str

    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse: ...

    async def complete_stream(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]: ...
```

---

## Task 2: OpenAI Provider
**File:** `backend/app/services/llm/providers/__init__.py`  
**File:** `backend/app/services/llm/providers/openai_provider.py`

### Implementation
```python
class OpenAIProvider:
    provider_name = "openai"

    # Default model
    DEFAULT_MODEL = "gpt-4o"

    # Pricing per 1M tokens (approximate)
    PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "o3-mini": {"input": 1.10, "output": 4.40},
    }

    def __init__(self, api_key: str) -> None: ...
    async def complete(self, messages, model=None, temperature=0.7, max_tokens=4096, json_mode=False) -> LLMResponse: ...
    async def complete_stream(self, messages, model=None, temperature=0.7, max_tokens=4096) -> AsyncIterator[str]: ...
```

### Key Implementation Details
- Use the `openai` Python SDK (already in requirements.txt): `from openai import AsyncOpenAI`
- Track token usage from `response.usage.prompt_tokens` / `response.usage.completion_tokens`
- Calculate cost from PRICING dict
- Measure latency with `time.perf_counter()`
- For `json_mode`, set `response_format={"type": "json_object"}`
- For streaming, yield chunks from `response.choices[0].delta.content`
- Wrap API errors in `ProviderError("openai", detail)`
- Handle rate limits (HTTP 429) with `RateLimitError("openai")`

---

## Task 3: Anthropic Provider
**File:** `backend/app/services/llm/providers/anthropic_provider.py`

### Implementation
```python
class AnthropicProvider:
    provider_name = "anthropic"

    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
        "claude-haiku-3-20250414": {"input": 0.80, "output": 4.00},
    }

    def __init__(self, api_key: str) -> None: ...
    async def complete(self, messages, model=None, temperature=0.7, max_tokens=4096, json_mode=False) -> LLMResponse: ...
    async def complete_stream(self, messages, model=None, temperature=0.7, max_tokens=4096) -> AsyncIterator[str]: ...
```

### Key Implementation Details
- Use the `anthropic` Python SDK (already in requirements.txt): `from anthropic import AsyncAnthropic`
- **Important:** Anthropic uses `system` as a separate parameter, NOT in the messages list. Extract system messages and pass as `system=` kwarg
- Track tokens from `response.usage.input_tokens` / `response.usage.output_tokens`
- For streaming, use `async with client.messages.stream(...)` and yield text deltas

---

## Task 4: Task Router
**File:** `backend/app/services/llm/router.py`

The router maps `TaskType` → specific model+provider based on config.

### Implementation
```python
# Default routing table — maps task types to (provider, model) pairs
DEFAULT_ROUTING = {
    TaskType.THESIS_GENERATION: ("anthropic", "claude-sonnet-4-20250514"),
    TaskType.THESIS_UPDATE: ("anthropic", "claude-sonnet-4-20250514"),
    TaskType.NEWS_ANALYSIS: ("openai", "gpt-4o"),
    TaskType.ASSUMPTION_GENERATION: ("anthropic", "claude-sonnet-4-20250514"),
    TaskType.COMPANY_COMPARISON: ("openai", "gpt-4o"),
    TaskType.NOTE_EXTRACTION: ("openai", "gpt-4o-mini"),
    TaskType.WATCH_ITEMS: ("openai", "gpt-4o"),
    TaskType.QUICK_SUMMARY: ("openai", "gpt-4o-mini"),
    TaskType.DATA_FORMATTING: ("openai", "gpt-4o-mini"),
}

class LLMRouter:
    def __init__(self) -> None:
        self._providers: Dict[str, LLMProvider] = {}
        self._routing = dict(DEFAULT_ROUTING)

    def register_provider(self, name: str, provider: LLMProvider) -> None: ...

    def route(self, task_type: TaskType) -> tuple[str, str]:
        """Returns (provider_name, model_name) for a task type."""
        ...

    async def complete(
        self,
        task_type: TaskType,
        messages: List[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Route a completion request to the appropriate provider+model."""
        provider_name, model = self.route(task_type)
        provider = self._providers[provider_name]
        return await provider.complete(messages, model=model, temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)

    def override_route(self, task_type: TaskType, provider: str, model: str) -> None:
        """Override routing for a specific task type."""
        ...
```

### Fallback Logic
If the primary provider fails, try the fallback chain:
1. Anthropic → OpenAI → (log error)
2. OpenAI → Anthropic → (log error)

---

## Task 5: Prompt Templates
**File:** `backend/app/services/llm/prompts/__init__.py`  
**File:** `backend/app/services/llm/prompts/templates.py`

Create a prompt template system with the 7 core templates. Use string `.format()` or f-strings with clear placeholder variables.

### Template Format
```python
from __future__ import annotations
from typing import Dict
from pydantic import BaseModel

class PromptTemplate(BaseModel):
    name: str
    task_type: TaskType
    system_prompt: str
    user_template: str  # Has {placeholders}
    version: str = "1.0"

    def render(self, **kwargs) -> list[LLMMessage]:
        """Render template into LLMMessage list."""
        messages = [
            LLMMessage(role=LLMRole.SYSTEM, content=self.system_prompt),
            LLMMessage(role=LLMRole.USER, content=self.user_template.format(**kwargs)),
        ]
        return messages
```

### The 7 Templates

1. **THESIS_GENERATION** — Generate an investment thesis given company data, financials, and news
2. **THESIS_UPDATE** — Update an existing thesis given new information
3. **NEWS_ANALYSIS** — Analyze a news article's impact on a stock (relevance, sentiment, thesis alignment)
4. **ASSUMPTION_GENERATION** — Generate base-case financial assumptions for a DCF model
5. **COMPANY_COMPARISON** — Compare two companies across key metrics
6. **NOTE_EXTRACTION** — Extract structured data points from free-text analyst notes
7. **WATCH_ITEMS** — Generate catalysts and watch items for a stock

Each template should have:
- A detailed system prompt explaining the AI's role as an equity research analyst
- A user template with clear `{placeholders}` for dynamic data
- Appropriate `task_type` matching `TaskType` enum

---

## Task 6: Tests
**File:** `backend/tests/test_llm_providers.py`  
**File:** `backend/tests/test_llm_router.py`

### test_llm_providers.py (~10 tests)
```python
# Mock the OpenAI/Anthropic SDK clients
class TestOpenAIProvider:
    # test_complete_success — mock response, verify LLMResponse fields
    # test_complete_json_mode — verify response_format is set
    # test_token_tracking — verify input/output tokens are captured
    # test_cost_calculation — verify cost is calculated from PRICING dict
    # test_rate_limit_error — mock 429, verify RateLimitError

class TestAnthropicProvider:
    # test_complete_success — mock response, verify LLMResponse fields
    # test_system_message_extraction — verify system prompt is extracted from messages
    # test_token_tracking — verify token counts
    # test_cost_calculation
    # test_provider_error
```

### test_llm_router.py (~8 tests)
```python
class TestLLMRouter:
    # test_default_routing — verify thesis → anthropic, summary → openai mini
    # test_route_override — verify override_route works
    # test_complete_routes_correctly — verify complete() calls the right provider
    # test_fallback_on_failure — verify primary → fallback on error
    # test_missing_provider — verify error when provider not registered

class TestPromptTemplates:
    # test_template_render — verify placeholders are filled
    # test_all_templates_exist — verify all 7 templates
    # test_template_version
```

## How to Run Tests
```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
```

## Final Checklist
- [ ] `services/llm/__init__.py`
- [ ] `services/llm/types.py` — LLMMessage, LLMResponse, TaskType
- [ ] `services/llm/protocols.py` — LLMProvider protocol
- [ ] `services/llm/providers/__init__.py`
- [ ] `services/llm/providers/openai_provider.py` — with cost tracking
- [ ] `services/llm/providers/anthropic_provider.py` — with system message extraction
- [ ] `services/llm/router.py` — task→model routing + fallback
- [ ] `services/llm/prompts/__init__.py`
- [ ] `services/llm/prompts/templates.py` — 7 prompt templates
- [ ] `tests/test_llm_providers.py` — ~10 mocked tests
- [ ] `tests/test_llm_router.py` — ~8 tests
- [ ] All files have `from __future__ import annotations`
- [ ] All tests pass: `python -m pytest tests/ -v`
