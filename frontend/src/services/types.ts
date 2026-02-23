// User types
export interface User {
  id: string
  email: string
  full_name: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

// Stock types
export interface Stock {
  id: string
  ticker: string
  company_name: string
  sector?: string
  industry?: string
  market_cap?: number
  current_price?: number
  change_percent?: number
}

export interface StockSearchResult {
  ticker: string
  name: string
  exchange: string
}

export interface StockDetail extends Stock {
  description?: string
  country?: string
  currency?: string
  ipo_date?: string
  website?: string
  pe_ratio?: number
  ev_ebitda?: number
  dividend_yield?: number
}

// Portfolio types
export interface PortfolioSummary {
  id: string
  name: string
  stock_count: number
  stocks?: Stock[]
}

export interface PortfolioDetail {
  id: string
  name: string
  description?: string
  user_id?: string
  created_at?: string
  updated_at?: string
  stocks: Stock[]
  stock_count?: number
}

// Use PortfolioDetail as the main type, PortfolioSummary for list responses
export type Portfolio = PortfolioSummary | PortfolioDetail

export interface CreatePortfolioRequest {
  name: string
  description?: string
}

export interface AddStockRequest {
  ticker: string
}

// News types
export interface NewsArticle {
  id: string
  ticker: string
  title: string
  content: string
  source: string
  url: string
  published_date: string
  sentiment?: 'positive' | 'negative' | 'neutral'
}

// Thesis types
export interface Thesis {
  id: string
  ticker: string
  title: string
  content: string
  thesis_type: 'bull' | 'bear'
  status: 'active' | 'closed'
  created_at: string
  updated_at: string
}

// Note types
export interface Note {
  id: string
  ticker: string
  title: string
  content: string
  created_at: string
  updated_at: string
}

// API Response wrapper
export interface ApiResponse<T> {
  data: T
  message?: string
}

// Error response
export interface ApiError {
  code: string
  detail: string
  status_code: number
}

// User Settings
export interface UserSettings {
  fundamentals_provider: string
  price_provider: string
  profile_provider: string
  news_provider: string
  fmp_api_key?: string
  finnhub_api_key?: string
  eodhd_api_key?: string
  polygon_api_key?: string
  alpha_vantage_api_key?: string
  openai_api_key?: string
  anthropic_api_key?: string
}

export interface UserSettingsUpdate {
  fundamentals_provider?: string
  price_provider?: string
  profile_provider?: string
  news_provider?: string
  fmp_api_key?: string
  finnhub_api_key?: string
  eodhd_api_key?: string
  polygon_api_key?: string
  alpha_vantage_api_key?: string
  openai_api_key?: string
  anthropic_api_key?: string
}
