import api from '@/services/api'

// Types
export interface AssumptionSet {
  id: string
  name: string
  ticker: string
  revenue_growth_rates: number[]
  gross_margin: number
  operating_margin: number
  wacc: number
  terminal_growth_rate: number
  projection_years: number
  tax_rate: number
  capex_as_pct_revenue: number
  da_as_pct_revenue: number
}

export interface ProjectedFinancials {
  year: number
  revenue: number
  gross_profit: number
  operating_income: number
  ebitda: number
  net_income: number
  free_cash_flow: number
  eps: number
}

export interface ModelOutput {
  ticker: string
  projections: ProjectedFinancials[]
  base_year: number
  base_year_revenue: number
}

export interface DCFResult {
  enterprise_value: number
  equity_value: number
  per_share_value: number
  upside_pct: number
  wacc: number
  terminal_growth_rate: number
}

export interface Scenario {
  id: string
  name: string
  case_type: string
  probability: number
  dcf_per_share?: number
  assumption_set_id: string
}

export interface ScenarioSummary {
  target_price: number
  scenarios: Scenario[]
}

export interface CompSuggestion {
  ticker: string
  reason: string
  similarity_score: number
  sector?: string
  market_cap?: number
}

export interface CompMetric {
  ticker: string
  company_name: string
  pe_ratio?: number
  ev_ebitda?: number
  pb_ratio?: number
  ps_ratio?: number
  market_cap?: number
}

export interface CompsResult {
  target: CompMetric
  peers: CompMetric[]
  medians: { pe: number; ev_ebitda: number; pb: number; ps: number }
}

export interface WaterfallItem {
  assumption_name: string
  base_value: number
  impact: number
  impact_pct: number
}

// API functions
export const getAssumptions = (ticker: string) =>
  api.get<AssumptionSet[]>(`/v1/assumptions/${ticker}`)

export const generateAssumptions = (ticker: string) =>
  api.post<AssumptionSet>(`/v1/assumptions/${ticker}/generate`)

export const updateAssumption = (id: string, data: Partial<AssumptionSet>) =>
  api.put<AssumptionSet>(`/v1/assumptions/${id}`, data)

export const computeModel = (ticker: string, assumptionId: string) =>
  api.post<ModelOutput>(`/v1/assumptions/${ticker}/compute_model`, {
    assumption_id: assumptionId,
  })

export const computeDCF = (ticker: string, assumptionId: string) =>
  api.post<DCFResult>(`/v1/assumptions/${ticker}/compute_dcf`, {
    assumption_id: assumptionId,
  })

export const getScenarios = (ticker: string) =>
  api.get<Scenario[]>(`/v1/scenarios/${ticker}`)

export const getScenarioSummary = (ticker: string) =>
  api.get<ScenarioSummary>(`/v1/scenarios/${ticker}/summary`)

export const suggestComps = (ticker: string) =>
  api.get<CompSuggestion[]>(`/v1/comps/${ticker}/suggest`)

export const analyzeComps = (ticker: string, peers: string[]) =>
  api.post<CompsResult>(`/v1/comps/${ticker}/analyze`, null, { params: { peers } })

export const getWaterfall = (ticker: string) =>
  api.get<{ items: WaterfallItem[] }>(`/v1/waterfall/${ticker}`)

export const exportModel = (ticker: string) =>
  api.get(`/v1/export/${ticker}/model`, { responseType: 'blob' })
