# Sub-Agent Work Package: GLM — Stage 1 (Model Builder + DCF)

## Objective

Build the financial model computation engine and DCF valuation method with an API for managing model assumptions.

## Environment

- Python 3.9 (`from __future__ import annotations` everywhere, no `X | None`)
- FastAPI + SQLAlchemy async + Pydantic v2
- Virtual env: `source backend/venv/bin/activate`
- Run tests: `cd backend && python -m pytest tests/ -v`
- All new files go under `backend/app/` or `backend/tests/`

## Codebase Context

### Existing schemas you MUST use (read `app/schemas/financial.py`)

- `IncomeStatement` — has `.revenue`, `.operating_income`, `.net_income`, `.ebitda`, `.eps_diluted`, etc.
- `BalanceSheet` — has `.cash_and_equivalents`, `.total_liabilities`, `.total_stockholders_equity`, `.shares_outstanding`, etc.
- `CashFlow` — has `.operating_cash_flow`, `.capital_expenditure`, `.free_cash_flow`, etc.
- `FinancialRatios` — has `.pe_ratio`, `.ev_to_ebitda`, `.gross_margin`, `.operating_margin`, etc.

### Existing models you MUST use

- `app/models/base.py` — `Base`, `UUIDMixin`, `TimestampMixin`
- `app/models/stock.py` — `Stock` with `id`, `ticker`, `company_name`
- `app/models/user.py` — `User` with `id`

### Existing API patterns (follow the style in `app/api/v1/stocks.py`)

- Router with prefix, tags, `Depends(get_current_user)`, `Depends(get_db)`
- Response schemas as Pydantic BaseModel with `model_config = {"from_attributes": True}`
- Use `NotFoundError`, `ValidationError` from `app.core.errors`

### LLM integration (for AI-generated assumptions)

- `app/services/llm/router.py` — `LLMRouter` with `.complete()` method
- `app/services/llm/types.py` — `TaskType.ASSUMPTION_GENERATION`, `LLMMessage`, `LLMRole`
- `app/services/llm/prompts/templates.py` — `TEMPLATES["assumption_generation"]` with placeholders: `company_name`, `ticker`, `financial_summary`

---

## Task 1: Assumption DB Model

**File:** `app/models/assumption.py`

```python
class AssumptionSet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "assumption_sets"

    stock_id: UUID FK -> stocks.id (CASCADE)
    user_id: UUID FK -> users.id (CASCADE)
    name: str (e.g. "Base Case", "Bull Case")
    is_active: bool = True  # The active set is used for valuation

    # Revenue assumptions (JSON-stored for flexibility)
    revenue_growth_rates: str  # JSON list of floats, e.g. [0.15, 0.12, 0.10, 0.08, 0.06]
    projection_years: int = 5

    # Margin assumptions
    gross_margin: float  # e.g. 0.45
    operating_margin: float  # e.g. 0.30
    tax_rate: float = 0.21

    # DCF-specific
    wacc: float  # Weighted avg cost of capital, e.g. 0.10
    terminal_growth_rate: float = 0.025  # Long-term GDP growth
    capex_as_pct_revenue: float = 0.05
    da_as_pct_revenue: float = 0.03

    # Optional overrides
    shares_outstanding: float | None  # Override from latest filing
    net_debt: float | None  # Override: total_debt - cash
```

Add `AssumptionSet` to `app/models/__init__.py` imports.

---

## Task 2: Model Engine

**File:** `app/services/model/engine.py`

Create a `ModelEngine` class:

```python
class ProjectedFinancials(BaseModel):
    """Single year of projected financials."""
    year: int
    revenue: float
    gross_profit: float
    operating_income: float
    ebitda: float
    net_income: float
    free_cash_flow: float
    eps: float

class ModelOutput(BaseModel):
    """Full model output."""
    ticker: str
    assumption_set_name: str
    projection_years: int
    projections: list[ProjectedFinancials]
    base_year_revenue: float  # The starting revenue

class ModelEngine:
    def compute(
        self,
        assumptions: AssumptionSet,  # the DB model
        latest_income: IncomeStatement,
        latest_balance: BalanceSheet,
        latest_cashflow: CashFlow,
    ) -> ModelOutput:
        """
        Pure computation — no async, no DB.

        Steps:
        1. Start with latest_income.revenue as base
        2. For each year in projection_years:
           - revenue = prev_revenue * (1 + growth_rate[i])
           - gross_profit = revenue * gross_margin
           - operating_income = revenue * operating_margin
           - ebitda = operating_income + (revenue * da_as_pct_revenue)
           - tax = operating_income * tax_rate
           - net_income = operating_income - tax
           - fcf = net_income + DA - capex
           - eps = net_income / shares_outstanding
        3. Return ModelOutput
        """
```

Also create `app/services/model/__init__.py` (empty).

---

## Task 3: DCF Valuation

**File:** `app/services/model/dcf.py`

```python
class DCFResult(BaseModel):
    """DCF valuation output."""
    ticker: str
    enterprise_value: float
    equity_value: float
    per_share_value: float
    terminal_value: float
    pv_of_fcfs: float
    pv_of_terminal: float
    upside_pct: float  # vs current price
    wacc: float
    terminal_growth_rate: float

class DCFCalculator:
    def calculate(
        self,
        model_output: ModelOutput,
        assumptions: AssumptionSet,
        current_price: float,
        shares_outstanding: float,
        net_debt: float,  # total_debt - cash (positive = debt)
    ) -> DCFResult:
        """
        Steps:
        1. Discount each year's FCF: PV = FCF / (1 + WACC)^year
        2. Terminal value = final_year_fcf * (1 + terminal_growth) / (WACC - terminal_growth)
        3. PV of terminal = terminal_value / (1 + WACC)^n
        4. Enterprise value = sum(PV of FCFs) + PV of terminal
        5. Equity value = enterprise_value - net_debt
        6. Per share = equity_value / shares_outstanding
        7. Upside = (per_share - current_price) / current_price
        """
```

---

## Task 4: Assumptions API

**File:** `app/api/v1/assumptions.py`

Endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/assumptions/{ticker}` | Create assumption set for a stock |
| `GET` | `/assumptions/{ticker}` | List all assumption sets for a stock |
| `GET` | `/assumptions/{ticker}/active` | Get the active assumption set |
| `PUT` | `/assumptions/{assumption_id}` | Update an assumption set |
| `DELETE` | `/assumptions/{assumption_id}` | Delete an assumption set |
| `POST` | `/assumptions/{ticker}/generate` | AI-generate base case assumptions |

Request/response schemas:

```python
class AssumptionCreate(BaseModel):
    name: str
    revenue_growth_rates: list[float]  # must have len == projection_years
    projection_years: int = 5
    gross_margin: float
    operating_margin: float
    tax_rate: float = 0.21
    wacc: float
    terminal_growth_rate: float = 0.025
    capex_as_pct_revenue: float = 0.05
    da_as_pct_revenue: float = 0.03

class AssumptionResponse(BaseModel):
    id: str
    name: str
    is_active: bool
    revenue_growth_rates: list[float]
    # ... all fields
    model_config = {"from_attributes": True}
```

For the `/generate` endpoint:
1. Fetch the stock's latest financials (income + balance + cashflow) from the data layer
2. Build a financial summary string
3. Call `LLMRouter.complete()` with `TaskType.ASSUMPTION_GENERATION`, `json_mode=True`
4. Parse the JSON response into `AssumptionCreate`
5. Save and return

**Register router** in `app/api/v1/__init__.py`.

---

## Task 5: Tests

**File:** `tests/test_model_engine.py` (~12 tests)

```python
class TestModelEngine:
    def test_basic_projection(self):
        """Revenue grows by growth rates, margins applied correctly."""

    def test_fcf_calculation(self):
        """FCF = net_income + DA - capex."""

    def test_single_year_projection(self):
        """Single year projection works."""

    def test_eps_calculation(self):
        """EPS = net_income / shares_outstanding."""

    def test_zero_growth(self):
        """Zero growth rates produce flat revenue."""

    def test_negative_growth(self):
        """Negative growth rates decrease revenue."""

class TestDCFCalculator:
    def test_basic_dcf(self):
        """Terminal value + PV of FCFs = enterprise value."""

    def test_equity_value_subtracts_debt(self):
        """Equity = EV - net_debt."""

    def test_per_share_value(self):
        """Per share = equity / shares."""

    def test_upside_calculation(self):
        """Upside = (per_share - price) / price."""

    def test_terminal_value_formula(self):
        """TV = FCF * (1+g) / (WACC - g)."""

    def test_high_wacc_lowers_value(self):
        """Higher WACC → lower enterprise value."""
```

All tests should use direct instantiation of `ModelEngine` and `DCFCalculator` — no mocking needed since they're pure computation.

---

## Constraints

1. Use `from __future__ import annotations` in every file
2. Use `Optional[X]` not `X | None` for Python 3.9
3. Follow existing code style (see `stocks.py`, `financial.py`)
4. All tests must be synchronous where possible (engine + DCF are sync)
5. After finishing, run: `cd backend && source venv/bin/activate && python -m pytest tests/ -v`
6. All tests (existing + new) must pass
