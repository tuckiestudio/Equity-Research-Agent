# Sub-Agent Work Package: Codex — Stage 4 (Stock Detail + Model Builder + Charts)

## Objective

Build the Stock Detail page with tabbed navigation (Overview, Model, News, Notes, Thesis), the model builder UI (assumption editing, scenario comparison), and financial visualizations using Recharts.

## Environment

- React 18 + TypeScript + Vite + Tailwind 3
- Already installed: `react-router-dom@6`, `axios`, `zustand@5`, `@tanstack/react-query@5`, `recharts`, `lucide-react`, `date-fns`, `clsx`
- Path alias: `@/` → `src/`
- DO NOT install new packages. Everything you need is already in `package.json`.
- Working dir: `/Users/bob/Projects/Equity-Research-Agent/frontend`

## Existing Code — GLM is Building Concurrently

GLM (the other agent) is simultaneously building these files. **Do NOT create these files**:
- `src/components/layout/AppShell.tsx`, `Sidebar.tsx`, `Header.tsx`
- `src/pages/Login.tsx`, `Register.tsx`, `Dashboard.tsx`
- `src/stores/auth.ts`
- `src/services/api.ts` (extending it), `types.ts`, `auth.ts`, `portfolios.ts`
- `src/components/auth/ProtectedRoute.tsx`
- `src/components/dashboard/StockCard.tsx`, `AddTickerModal.tsx`

GLM is creating a placeholder `src/pages/StockDetail.tsx`. **You will replace this file** with the full implementation.

### What GLM Provides (assume these exist)

```typescript
// src/services/api.ts — axios instance with JWT interceptors
import api from '@/services/api'

// src/services/types.ts — shared types
export interface User { id: string; email: string; full_name: string }
export interface Stock { id: string; ticker: string; company_name: string; sector?: string }
```

---

## Backend API Reference (all under `/api/v1/`)

### Assumptions
- `GET /assumptions/{ticker}` → `[AssumptionSet]`
- `POST /assumptions/{ticker}` → create set → `AssumptionSet`
- `PUT /assumptions/{assumption_id}` → update → `AssumptionSet`
- `POST /assumptions/{ticker}/generate` → AI generate → `AssumptionSet`
- `POST /assumptions/{ticker}/compute_model` → `ModelOutput`
- `POST /assumptions/{ticker}/compute_dcf` → `DCFResult`

### Scenarios
- `GET /scenarios/{ticker}` → `[Scenario]`
- `POST /scenarios/{ticker}` → create → `Scenario`
- `PUT /scenarios/{scenario_id}` → update → `Scenario`
- `GET /scenarios/{ticker}/summary` → `{ target_price, scenarios: [...] }`

### Comps
- `GET /comps/{ticker}/suggest` → `[CompSuggestion]`
- `POST /comps/{ticker}/analyze?peers=MSFT&peers=GOOGL` → `CompsResult`

### News
- `POST /news/{ticker}/analyze` → analyze news → `[NewsAnalysis]`
- `GET /news/{ticker}` → `[NewsAnalysis]`
- `GET /news/{ticker}/sentiment` → `SentimentSummary`

### Notes
- `POST /notes/{ticker}` → create → `Note`
- `GET /notes/{ticker}` → `[Note]`
- `PUT /notes/{note_id}` → update
- `DELETE /notes/{note_id}`
- `POST /notes/{note_id}/extract` → AI extraction

### Thesis
- `POST /thesis/{ticker}/generate` → `Thesis`
- `GET /thesis/{ticker}` → active `Thesis`
- `PUT /thesis/{thesis_id}/update` → `{ new_information }` → `Thesis`
- `GET /thesis/{thesis_id}/history` → `[ThesisChange]`
- `GET /thesis/{ticker}/timeline` → `[TimelineItem]`

### Watch
- `POST /watch/{ticker}/generate` → `[WatchItem]`
- `GET /watch/{ticker}` → `[WatchItem]`

### Waterfall
- `GET /waterfall/{ticker}` → `WaterfallResponse`

### Export
- `GET /export/{ticker}/model` → Excel file download

---

## Task 1: Service Layer Types + Functions

**File:** `src/services/model.ts`
```typescript
// Types
export interface AssumptionSet {
  id: string; name: string; ticker: string
  revenue_growth_rates: number[]; gross_margin: number; operating_margin: number
  wacc: number; terminal_growth_rate: number; projection_years: number
  tax_rate: number; capex_as_pct_revenue: number; da_as_pct_revenue: number
}
export interface ProjectedFinancials {
  year: number; revenue: number; gross_profit: number; operating_income: number
  ebitda: number; net_income: number; free_cash_flow: number; eps: number
}
export interface ModelOutput { ticker: string; projections: ProjectedFinancials[]; base_year: number; base_year_revenue: number }
export interface DCFResult { enterprise_value: number; equity_value: number; per_share_value: number; upside_pct: number; wacc: number; terminal_growth_rate: number }
export interface Scenario { id: string; name: string; case_type: string; probability: number; dcf_per_share?: number; assumption_set_id: string }
export interface ScenarioSummary { target_price: number; scenarios: Scenario[] }
export interface CompSuggestion { ticker: string; reason: string; similarity_score: number; sector?: string; market_cap?: number }
export interface CompMetric { ticker: string; company_name: string; pe_ratio?: number; ev_ebitda?: number; pb_ratio?: number; ps_ratio?: number; market_cap?: number }
export interface CompsResult { target: CompMetric; peers: CompMetric[]; medians: { pe: number; ev_ebitda: number; pb: number; ps: number } }
export interface WaterfallItem { assumption_name: string; base_value: number; impact: number; impact_pct: number }

// API functions
export const getAssumptions = (ticker: string) => api.get<AssumptionSet[]>(`/v1/assumptions/${ticker}`)
export const generateAssumptions = (ticker: string) => api.post<AssumptionSet>(`/v1/assumptions/${ticker}/generate`)
export const updateAssumption = (id: string, data: Partial<AssumptionSet>) => api.put<AssumptionSet>(`/v1/assumptions/${id}`, data)
export const computeModel = (ticker: string, assumptionId: string) => api.post<ModelOutput>(`/v1/assumptions/${ticker}/compute_model`, { assumption_id: assumptionId })
export const computeDCF = (ticker: string, assumptionId: string) => api.post<DCFResult>(`/v1/assumptions/${ticker}/compute_dcf`, { assumption_id: assumptionId })
export const getScenarios = (ticker: string) => api.get<Scenario[]>(`/v1/scenarios/${ticker}`)
export const getScenarioSummary = (ticker: string) => api.get<ScenarioSummary>(`/v1/scenarios/${ticker}/summary`)
export const suggestComps = (ticker: string) => api.get<CompSuggestion[]>(`/v1/comps/${ticker}/suggest`)
export const analyzeComps = (ticker: string, peers: string[]) => api.post<CompsResult>(`/v1/comps/${ticker}/analyze`, null, { params: { peers } })
export const getWaterfall = (ticker: string) => api.get<{ items: WaterfallItem[] }>(`/v1/waterfall/${ticker}`)
export const exportModel = (ticker: string) => api.get(`/v1/export/${ticker}/model`, { responseType: 'blob' })
```

**File:** `src/services/news.ts` — news / notes / thesis / watch API functions
```typescript
export interface NewsAnalysis { id: string; headline: string; impact_label: string; impact_score: number; relevance_score: number; thesis_alignment: string; ai_summary: string; published_at: string }
export interface SentimentSummary { avg_impact_score: number; bullish_count: number; bearish_count: number; neutral_count: number; total_articles: number }
export interface Note { id: string; title: string; content: string; note_type?: string; extracted_sentiment?: string; is_ai_processed: boolean; created_at: string }
export interface Thesis { id: string; title: string; summary: string; full_text: string; stance: string; confidence: number; target_price?: number; version: number }
export interface ThesisChange { id: string; change_type: string; previous_stance?: string; new_stance?: string; change_summary: string; created_at: string }
export interface WatchItem { id: string; title: string; description: string; category: string; potential_impact: string; status: string; expected_date?: string }

export const getNews = (ticker: string) => api.get<NewsAnalysis[]>(`/v1/news/${ticker}`)
export const analyzeNews = (ticker: string) => api.post<NewsAnalysis[]>(`/v1/news/${ticker}/analyze`)
export const getSentiment = (ticker: string) => api.get<SentimentSummary>(`/v1/news/${ticker}/sentiment`)
export const getNotes = (ticker: string) => api.get<Note[]>(`/v1/notes/${ticker}`)
export const createNote = (ticker: string, data: { title: string; content: string; note_type?: string }) => api.post<Note>(`/v1/notes/${ticker}`, data)
export const getThesis = (ticker: string) => api.get<Thesis>(`/v1/thesis/${ticker}`)
export const generateThesis = (ticker: string) => api.post<Thesis>(`/v1/thesis/${ticker}/generate`)
export const getThesisHistory = (thesisId: string) => api.get<ThesisChange[]>(`/v1/thesis/${thesisId}/history`)
export const getWatchItems = (ticker: string) => api.get<WatchItem[]>(`/v1/watch/${ticker}`)
export const generateWatchItems = (ticker: string) => api.post<WatchItem[]>(`/v1/watch/${ticker}/generate`)
```

---

## Task 2: Stock Detail Page with Tabs

**File:** `src/pages/StockDetail.tsx` (REPLACE the placeholder GLM creates)

```tsx
// Tabbed layout: Overview | Model | News | Notes | Thesis
// Use useParams to get ticker from URL
// Tab state managed with useState
// Each tab loads its content lazily
```

Tab bar design:
- Horizontal tabs below header
- Active tab: accent underline + bold text
- Inactive: muted text, hover brightens
- Bottom border separator

**Overview tab** (default):
- Company header: ticker, name, sector, industry
- Quick stats row: current price, market cap, P/E, EV/EBITDA
- Sentiment badge (bull/bear/neutral from `/news/{ticker}/sentiment`)
- Watch items preview (top 3 from `/watch/{ticker}`)
- Active thesis summary card (from `/thesis/{ticker}`)

---

## Task 3: Model Builder Tab

**File:** `src/components/model/ModelTab.tsx`
- Contains the full model building experience within the Model tab

**File:** `src/components/model/AssumptionPanel.tsx`
```
Left side panel showing editable assumptions:
- Revenue growth rates (per year, slider or input)
- Gross margin %
- Operating margin %
- WACC %
- Terminal growth rate %
- Tax rate %
- Capex as % revenue
- "Generate AI Assumptions" button
- "Compute Model" button
- Each field: label, current value, editable input
- Changes trigger recomputation
```

**File:** `src/components/model/ProjectionTable.tsx`
```
Financial projection table showing computed results:
- Columns: Year 1, Year 2, ..., Year N
- Rows: Revenue, Gross Profit, Operating Income, EBITDA, Net Income, FCF, EPS
- Format numbers: $XXX.XM or $X.XB
- Highlight growth rates between years
- Clean dark table with alternating row shading
```

**File:** `src/components/model/ValuationSummary.tsx`
```
DCF result display:
- Big number: Implied Value per share
- Upside/downside percentage (green if up, red if down)
- Enterprise value, equity value
- WACC and terminal growth rate used
- Scenario summary: weighted target price
- "Export to Excel" button → triggers blob download
```

**File:** `src/components/model/ScenarioPanel.tsx`
```
Scenario comparison:
- Three columns: Bull | Base | Bear
- Each shows: probability weight, key assumptions, DCF per share
- Weighted target price at bottom
- Color-coded: green(bull), blue(base), red(bear)
```

---

## Task 4: Charts (Recharts)

**File:** `src/components/charts/RevenueChart.tsx`
- Bar chart showing projected revenue by year
- Gradient fill bars
- Y-axis formatted in $M/$B

**File:** `src/components/charts/MarginChart.tsx`
- Line chart: gross margin % and operating margin % over projection years
- Dual lines with different colors
- Tooltip showing exact values

**File:** `src/components/charts/WaterfallChart.tsx`
- Waterfall chart showing DCF sensitivity to each assumption
- Each bar shows positive (green) or negative (red) impact
- Data from `/waterfall/{ticker}`

**File:** `src/components/charts/SentimentChart.tsx`
- Donut/pie chart: bullish vs bearish vs neutral article counts
- Color-coded: green, red, gray
- Center text: average impact score

---

## Task 5: News Tab + Notes Tab + Thesis Tab (basic versions)

**File:** `src/components/news/NewsTab.tsx`
- List of analyzed news articles from `/news/{ticker}`
- Each item: headline, published date, impact badge (bullish/bearish/neutral), AI summary
- "Refresh Analysis" button → `POST /news/{ticker}/analyze`
- Sentiment summary card at top

**File:** `src/components/notes/NotesTab.tsx`
- List of notes from `/notes/{ticker}`
- "Add Note" button → simple modal with title + content textarea
- Each note shows: title, preview, date, sentiment badge if AI-processed
- Click to expand full content

**File:** `src/components/thesis/ThesisTab.tsx`
- Active thesis display: title, stance badge, confidence bar, target price
- Full text rendered (plain text, not markdown for now)
- "Generate Thesis" button if no thesis exists
- Change history list from `/thesis/{id}/history`

---

## Design Requirements

1. **Dark mode** — match GLM's dark theme (bg-surface, text-primary, etc.)
2. Use these Tailwind semantic colors (GLM is configuring them):
   ```
   surface / surface-card / surface-elevated
   accent / accent-hover
   text-primary / text-secondary / text-muted
   border / border-hover
   success / warning / danger
   ```
3. **Financial data formatting** — always use proper number formatting: `$1.2B`, `$456.7M`, `12.3%`
4. **Loading states** — skeleton or spinner for every async operation
5. **Error states** — friendly messages when API calls fail
6. **Hover effects** — all interactive elements need clear hover states
7. **Transitions** — subtle `transition-all duration-200` on interactive elements

## Constraints

1. Use ONLY packages already in `package.json`
2. Use the `@/` path alias for all imports
3. Use `useQuery` / `useMutation` for all API calls
4. Import `api` from `@/services/api` for all requests
5. Ensure TypeScript compiles clean: `npx tsc --noEmit`
6. Do NOT modify files that GLM is building (listed above)
