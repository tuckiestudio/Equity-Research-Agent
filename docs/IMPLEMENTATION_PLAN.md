# Equity Research Agent - Implementation Plan

## Current State
- FastAPI backend + React/Vite frontend scaffold
- Dependencies installed: yfinance, pandas, anthropic, sqlalchemy, recharts, zustand, tanstack-query
- No business logic, models, or UI components built yet

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  Portfolio Dashboard │ Model Builder │ Thesis Tracker    │
├─────────────────────────────────────────────────────────┤
│                    FastAPI Backend                        │
│  REST API + WebSocket (for live updates)                 │
├──────────┬──────────┬───────────┬───────────────────────┤
│ Data Svc │ Model Svc│ News Svc  │ AI/Thesis Svc         │
├──────────┴──────────┴───────────┴───────────────────────┤
│  PostgreSQL          │  Redis (cache/jobs)               │
└──────────────────────┴──────────────────────────────────┘
```

---

## Phase 1: Data Layer & Core Models

**Goal:** Database schema, data fetching, and the foundation everything else builds on.

### 1A: Database Models & Migrations

**Files to create/modify:**
- `backend/app/models/base.py` - SQLAlchemy base with common mixins (id, created_at, updated_at)
- `backend/app/models/stock.py` - Stock/ticker master
- `backend/app/models/portfolio.py` - User portfolios and coverage lists
- `backend/app/models/financial.py` - Historical financials (income stmt, balance sheet, cash flow)
- `backend/app/models/model.py` - Forecast models and assumptions
- `backend/app/models/news.py` - News items and analyst notes
- `backend/app/models/thesis.py` - Investment thesis snapshots
- `backend/app/models/user.py` - User accounts (simple auth)
- `backend/app/db/session.py` - Async database session factory
- Alembic initial migration

**Key schema design:**

```
users
  id, email, hashed_password, created_at

portfolios
  id, user_id, name, created_at

portfolio_stocks (coverage list)
  id, portfolio_id, stock_id, added_at, is_comp, comp_for_stock_id

stocks
  id, ticker, company_name, sector, industry, market_cap, exchange, last_refreshed

financials (historical - one row per line item per period)
  id, stock_id, period_type (annual/quarterly), period_date,
  statement_type (income/balance/cashflow), line_item, value, unit, source

model_scenarios
  id, stock_id, user_id, name, is_base_case, created_at, updated_at

model_assumptions
  id, scenario_id, line_item, year, value, assumption_type (growth_rate/margin/absolute),
  driver_description, source_reference, changed_at

model_outputs (computed forecasts)
  id, scenario_id, line_item, year, value, computed_at

news_items
  id, stock_id, headline, summary, source_url, source_name,
  published_at, fetched_at, relevance_score, ai_analysis

analyst_notes
  id, stock_id, user_id, note_type (meeting/call/clipping/observation),
  content, attachment_url, created_at, impact_assessment

thesis_snapshots (versioned investment thesis)
  id, stock_id, user_id, version, thesis_text, rating (buy/hold/sell),
  target_price, key_drivers (jsonb), key_risks (jsonb),
  watch_items (jsonb), created_at, trigger_event

thesis_changes (audit trail)
  id, thesis_snapshot_id, field_changed, old_value, new_value,
  change_reason, triggered_by_type (news/note/model_change),
  triggered_by_id, created_at
```

### 1B: Financial Data Service

**Files to create:**
- `backend/app/services/market_data.py` - yfinance wrapper for price/financial data
- `backend/app/services/financial_parser.py` - Normalize yfinance data into our schema
- `backend/app/schemas/stock.py` - Pydantic request/response schemas
- `backend/app/schemas/financial.py`

**Functionality:**
- Fetch 5-year historical financials (income statement, balance sheet, cash flow) via yfinance
- Normalize into consistent line items across companies
- Store in DB with source tracking
- Cache in Redis (TTL: 24h for financials, 15min for prices)
- Handle data gaps gracefully

### 1C: Stock & Portfolio API

**Files to create:**
- `backend/app/api/stocks.py` - CRUD for stocks, ticker search/validation
- `backend/app/api/portfolios.py` - Portfolio management endpoints

**Endpoints:**
```
POST   /api/stocks/search          - Search/validate ticker
POST   /api/stocks/{ticker}/fetch  - Trigger data fetch for a ticker
GET    /api/stocks/{ticker}        - Get stock details + financials

POST   /api/portfolios             - Create portfolio
GET    /api/portfolios             - List user portfolios
POST   /api/portfolios/{id}/stocks - Add stock to coverage
DELETE /api/portfolios/{id}/stocks/{stock_id}
GET    /api/portfolios/{id}        - Get portfolio with all stocks
```

---

## Phase 2: Comparable Companies & Model Builder

### 2A: Comp Suggestion Engine

**Files to create:**
- `backend/app/services/comp_engine.py` - Comparable company identification

**Logic:**
1. When a ticker is added, fetch its sector/industry/market_cap from yfinance
2. Use Claude to analyze the business and suggest 5-8 relevant comps with reasoning
3. Cross-reference with yfinance sector data for validation
4. Return ranked comps with similarity rationale
5. User can accept/reject/add their own comps

**Endpoints:**
```
GET  /api/stocks/{ticker}/comps/suggest  - AI-suggested comps
POST /api/stocks/{ticker}/comps          - Add a comp (user choice)
```

### 2B: Financial Model Builder

**Files to create:**
- `backend/app/services/model_builder.py` - Forecast engine
- `backend/app/services/assumption_engine.py` - AI-generated default assumptions
- `backend/app/schemas/model.py`
- `backend/app/api/models.py`

**Functionality:**
1. **Auto-generate base case assumptions** using Claude:
   - Analyze 5-year historical trends (revenue growth, margins, capex ratios, etc.)
   - Generate 3-year forecasts with line-by-line driver assumptions
   - Each assumption has: value, reasoning, confidence level, source reference
2. **Model computation:**
   - Income statement: Revenue -> COGS -> Gross Profit -> OpEx -> EBIT -> Net Income
   - Balance sheet: Key items projected from revenue/asset ratios
   - Cash flow: Derived from income statement + balance sheet changes
   - Key metrics: EPS, P/E, EV/EBITDA, FCF yield, ROE, etc.
3. **Scenario management:**
   - Base case (AI-generated defaults)
   - User can create bull/bear scenarios
   - Change any assumption -> model recalculates immediately
   - Track assumption change history

**Endpoints:**
```
POST   /api/models/{ticker}/generate    - Generate base case model
GET    /api/models/{ticker}/scenarios   - List scenarios
GET    /api/models/{ticker}/scenarios/{id} - Full model with outputs
PATCH  /api/models/{ticker}/scenarios/{id}/assumptions - Update assumptions
POST   /api/models/{ticker}/scenarios   - Create new scenario (bull/bear)
GET    /api/models/{ticker}/scenarios/{id}/compare/{other_id} - Compare scenarios
```

---

## Phase 3: News Monitoring & Analyst Notes

### 3A: News Ingestion

**Files to create:**
- `backend/app/services/news_monitor.py` - News fetching and monitoring
- `backend/app/services/news_analyzer.py` - AI analysis of news impact
- `backend/app/schemas/news.py`
- `backend/app/api/news.py`

**Functionality:**
1. Fetch news for covered stocks (yfinance news, RSS feeds)
2. Claude analyzes each news item for:
   - Relevance to investment thesis
   - Potential impact on model assumptions (which line items, direction, magnitude)
   - Whether it challenges or supports current thesis
3. Flag high-impact items for user attention
4. Also monitor comp company news for read-across signals

**Endpoints:**
```
GET  /api/news/{ticker}              - News feed for a stock
GET  /api/news/{ticker}/alerts       - High-impact alerts
POST /api/news/{ticker}/analyze      - Re-analyze a news item's impact
GET  /api/news/portfolio/{id}        - All news across portfolio
```

### 3B: Analyst Notes System

**Files to create:**
- `backend/app/services/note_processor.py` - Process and analyze user notes
- `backend/app/schemas/notes.py`
- `backend/app/api/notes.py`

**Functionality:**
1. User can add notes (free text, meeting notes, clippings)
2. Optional file attachment (PDF, images)
3. Claude extracts key data points from notes
4. AI suggests which model assumptions might need updating based on note content
5. All notes are linked to the stock and timestamped for thesis history

**Endpoints:**
```
POST   /api/notes/{ticker}           - Add a note
GET    /api/notes/{ticker}           - List notes for stock
PUT    /api/notes/{id}               - Update a note
DELETE /api/notes/{id}               - Delete a note
POST   /api/notes/{id}/analyze       - AI analysis of note's model impact
```

---

## Phase 4: Investment Thesis Engine

### 4A: Living Thesis

**Files to create:**
- `backend/app/services/thesis_engine.py` - Thesis generation and evolution
- `backend/app/schemas/thesis.py`
- `backend/app/api/thesis.py`

**Functionality:**
1. **Initial thesis generation** (Claude):
   - Company overview and business model
   - Industry positioning and competitive dynamics
   - Key investment drivers (bull case arguments)
   - Key risks (bear case arguments)
   - Valuation summary from the model
   - Rating and target price
2. **Thesis evolution:**
   - When new information arrives (news, notes, model changes), Claude evaluates impact
   - If material, creates a new thesis snapshot with tracked changes
   - Change audit trail: what changed, why, what triggered it
3. **Watch items:**
   - AI-generated list of upcoming catalysts/events to watch
   - Linked to specific model assumptions they could impact
   - User can add/modify watch items

**Endpoints:**
```
GET    /api/thesis/{ticker}              - Current thesis
GET    /api/thesis/{ticker}/history      - All thesis versions
GET    /api/thesis/{ticker}/history/{version} - Specific version
GET    /api/thesis/{ticker}/changes      - Change audit trail
POST   /api/thesis/{ticker}/generate     - Generate/regenerate thesis
PATCH  /api/thesis/{ticker}              - User edits to thesis
GET    /api/thesis/{ticker}/watch-items  - Watch items list
POST   /api/thesis/{ticker}/watch-items  - Add watch item
```

### 4B: Thesis Timeline (Premium Feature)

**Files to create:**
- `backend/app/services/timeline.py`
- `backend/app/api/timeline.py`

**Functionality:**
1. Timeline slider showing thesis evolution over time
2. At each point: thesis text, model assumptions, rating
3. Each change linked to the triggering event (news/note/user edit)
4. Visual diff between any two points in time
5. Model assumption waterfall charts showing how estimates evolved

**Endpoints:**
```
GET /api/timeline/{ticker}                    - Full timeline data
GET /api/timeline/{ticker}/compare?v1=X&v2=Y  - Compare two points
GET /api/timeline/{ticker}/assumptions-flow    - Assumption evolution data
```

---

## Phase 5: Frontend Implementation

### 5A: Core Layout & Navigation

**Files to create:**
- `frontend/src/components/layout/AppShell.tsx` - Main layout (sidebar + content)
- `frontend/src/components/layout/Sidebar.tsx` - Navigation sidebar
- `frontend/src/components/layout/Header.tsx` - Top bar with search
- `frontend/src/stores/portfolioStore.ts` - Zustand portfolio state
- `frontend/src/stores/modelStore.ts` - Zustand model state
- `frontend/src/services/api.ts` - Axios API client with typed endpoints
- `frontend/src/types/` - TypeScript interfaces mirroring backend schemas

### 5B: Portfolio Dashboard

**Files to create:**
- `frontend/src/pages/Dashboard.tsx` - Main portfolio view
- `frontend/src/components/portfolio/StockCard.tsx` - Stock summary card
- `frontend/src/components/portfolio/AddTicker.tsx` - Ticker search & add
- `frontend/src/components/portfolio/CompSuggestions.tsx` - Comp suggestions panel

**Features:**
- Portfolio overview with stock cards (price, key metrics, thesis summary)
- Add ticker with autocomplete search
- Comp suggestions appear after adding a ticker
- Quick-glance model status and thesis rating per stock

### 5C: Model Builder UI

**Files to create:**
- `frontend/src/pages/ModelView.tsx` - Full model page
- `frontend/src/components/model/FinancialTable.tsx` - Spreadsheet-like financial table
- `frontend/src/components/model/AssumptionPanel.tsx` - Edit assumptions sidebar
- `frontend/src/components/model/ScenarioToggle.tsx` - Switch between scenarios
- `frontend/src/components/model/MetricsBar.tsx` - Key computed metrics
- `frontend/src/components/model/Charts.tsx` - Revenue/margin/EPS charts

**Features:**
- Spreadsheet-style financial table (historical + forecast)
- Click any forecast cell to see/edit the underlying assumption
- Assumption panel shows: current value, AI reasoning, source, history
- Scenario tabs (base/bull/bear)
- Real-time recalculation on assumption change
- Charts: revenue trend, margin evolution, EPS bridge, valuation multiples

### 5D: News & Notes Interface

**Files to create:**
- `frontend/src/pages/NewsView.tsx` - News feed page
- `frontend/src/components/news/NewsFeed.tsx` - Scrollable news list
- `frontend/src/components/news/NewsCard.tsx` - Individual news item with AI analysis
- `frontend/src/components/news/ImpactBadge.tsx` - Visual impact indicator
- `frontend/src/components/notes/NoteEditor.tsx` - Rich text note input
- `frontend/src/components/notes/NotesList.tsx` - Notes history

**Features:**
- Filtered news feed (by stock, by portfolio)
- Each news item shows AI-assessed impact with affected assumptions highlighted
- One-click to view how a news item would change model
- Note creation with type categorization
- After submitting a note, AI suggests assumption adjustments

### 5E: Thesis View

**Files to create:**
- `frontend/src/pages/ThesisView.tsx` - Investment thesis page
- `frontend/src/components/thesis/ThesisDocument.tsx` - Rendered thesis
- `frontend/src/components/thesis/WatchItems.tsx` - Watch list
- `frontend/src/components/thesis/ChangeLog.tsx` - Change history
- `frontend/src/components/thesis/TimelineSlider.tsx` - Historical slider (premium)
- `frontend/src/components/thesis/AssumptionWaterfall.tsx` - Assumption evolution chart

---

## Phase 6: AI Integration Layer

### 6A: Claude Service

**Files to create:**
- `backend/app/services/ai/claude_client.py` - Anthropic API wrapper
- `backend/app/services/ai/prompts.py` - All prompt templates
- `backend/app/services/ai/response_parser.py` - Structured output parsing

**Prompt design principles:**
- All prompts include factual context (financials, company data)
- Outputs are structured JSON for programmatic consumption
- Source references required in all AI outputs
- Prompts explicitly instruct the model to flag uncertainty
- User-provided context (notes) is always included when relevant

**Key prompt templates:**
1. `COMP_SUGGESTION` - Given company profile, suggest comparable companies
2. `ASSUMPTION_GENERATION` - Given 5yr historicals, generate 3yr forecast assumptions
3. `NEWS_ANALYSIS` - Given news item + current thesis, assess impact
4. `NOTE_EXTRACTION` - Given analyst note, extract data points and model implications
5. `THESIS_GENERATION` - Given all data, generate investment thesis
6. `THESIS_UPDATE` - Given new information + current thesis, determine changes
7. `WATCH_ITEMS` - Given thesis + calendar, suggest items to monitor

---

## Phase 7: Auth & Monetization Prep

### 7A: Authentication

**Files to create:**
- `backend/app/services/auth.py` - JWT auth service
- `backend/app/api/auth.py` - Login/register endpoints
- `backend/app/api/deps.py` - FastAPI dependency for auth
- `frontend/src/pages/Login.tsx`
- `frontend/src/stores/authStore.ts`

### 7B: Tiered Access

**Base tier:**
- Portfolio tracking (up to 10 stocks)
- Historical financials
- Basic model with AI-generated assumptions
- Manual assumption editing

**Premium tier:**
- Unlimited stocks
- News monitoring + AI analysis
- Analyst notes with AI extraction
- Living thesis with evolution tracking
- Timeline slider + assumption waterfall
- Comp suggestions

---

## Execution Order for Sub-Agents

Each phase below is designed to be a **self-contained work package** that a sub-agent can execute independently.

### Agent 1: Database & Data Foundation
```
Scope: Phase 1A + 1B + 1C
Input: This plan's schema design
Output: Working database, migrations, data fetching, stock/portfolio API
Test: Can add a ticker, fetch its financials, create a portfolio
```

### Agent 2: AI Service Layer
```
Scope: Phase 6A (Claude integration)
Input: This plan's prompt templates and response schemas
Output: Working AI service with all prompt templates
Test: Can call each prompt template and get structured responses
Dependencies: None (can run in parallel with Agent 1)
```

### Agent 3: Model Builder (Backend)
```
Scope: Phase 2B
Input: Working DB + AI service
Output: Model generation, assumption management, scenario API
Test: Can generate a 3-year forecast, edit assumptions, recalculate
Dependencies: Agent 1, Agent 2
```

### Agent 4: Comp Engine + News + Notes (Backend)
```
Scope: Phase 2A + 3A + 3B
Input: Working DB + AI service
Output: Comp suggestions, news monitoring, analyst notes API
Test: Can suggest comps, fetch/analyze news, create/analyze notes
Dependencies: Agent 1, Agent 2
```

### Agent 5: Thesis Engine (Backend)
```
Scope: Phase 4A + 4B
Input: All backend services
Output: Thesis generation, evolution tracking, timeline API
Test: Can generate thesis, update on new info, view timeline
Dependencies: Agents 1-4
```

### Agent 6: Frontend - Core + Portfolio
```
Scope: Phase 5A + 5B
Input: Working backend APIs
Output: App shell, portfolio dashboard, ticker management
Test: Can navigate app, add stocks, see portfolio
Dependencies: Agent 1 (backend APIs running)
```

### Agent 7: Frontend - Model Builder UI
```
Scope: Phase 5C
Input: Working model API + frontend shell
Output: Financial table, assumption editing, scenario management
Test: Can view model, edit assumptions, switch scenarios
Dependencies: Agent 3, Agent 6
```

### Agent 8: Frontend - News, Notes, Thesis
```
Scope: Phase 5D + 5E
Input: Working news/notes/thesis APIs + frontend shell
Output: News feed, note editor, thesis view, timeline slider
Test: Full user workflow from news to thesis update
Dependencies: Agents 4-6
```

### Agent 9: Auth & Polish
```
Scope: Phase 7A + 7B
Input: Complete application
Output: Auth system, tier gating, final polish
Dependencies: All previous agents
```

---

## Parallelization Strategy

```
Timeline:
  ├── Agent 1 (DB + Data) ──────┐
  ├── Agent 2 (AI Service) ─────┤
  │                              ├── Agent 3 (Model Builder) ──┐
  │                              ├── Agent 4 (Comps/News/Notes)┤
  │                              │                              ├── Agent 5 (Thesis) ─┐
  ├── Agent 6 (FE Core) ────────┤                              │                      │
  │                              ├── Agent 7 (FE Model) ───────┤                      │
  │                              │                              ├── Agent 8 (FE News) ─┤
  │                                                                                    ├── Agent 9 (Auth)
```

**Can run in parallel:**
- Agents 1 + 2 (no dependencies on each other)
- Agents 3 + 4 (after 1 & 2, independent of each other)
- Agent 6 can start with Agent 1 (only needs API endpoints)
- Agents 7 + 8 (after their respective backend agents)

---

## Key Technical Decisions

1. **yfinance for financial data** - Free, sufficient for MVP. Can swap to paid API (e.g., Financial Modeling Prep, Alpha Vantage) later.
2. **Claude for all AI tasks** - Single provider simplifies prompt management. Use claude-sonnet for speed-sensitive tasks (news analysis), claude-opus for quality-sensitive tasks (thesis generation).
3. **PostgreSQL JSONB** for flexible fields (key_drivers, watch_items) - Avoids schema rigidity for evolving features.
4. **Zustand over Redux** - Already in deps, simpler for this scale.
5. **No WebSocket initially** - Polling/react-query refetch intervals for MVP. Add WebSocket for real-time news alerts later.
6. **File uploads** - Store locally in MVP, move to S3/equivalent for production.

---

## Data Source Attribution

Every piece of AI-generated or data-sourced content must carry a `source` field:
- Financial data: "yfinance - {ticker} - {statement} - {date}"
- AI analysis: "claude-{model} - {prompt_template} - {timestamp}"
- News: Original source URL
- Analyst notes: "analyst_note - {user} - {note_id} - {date}"

This ensures requirement #7 (factual source referencing) is met throughout.
