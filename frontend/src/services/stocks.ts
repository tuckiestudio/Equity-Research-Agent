import api from './api'
import type { StockDetail, StockSearchResult } from './types'

export const searchStocks = (query: string) =>
  api.get<StockSearchResult[]>(`/v1/stocks/search`, { params: { q: query } })

export const getStock = (ticker: string) =>
  api.get<StockDetail>(`/v1/stocks/${ticker}`)

export const getStockDetail = (ticker: string) =>
  api.get<StockDetail>(`/v1/stocks/${ticker}`)

export const getStockPriceHistory = (ticker: string, period: string = '1y') =>
  api.get(`/v1/stocks/${ticker}/history`, { params: { period } })

export const getStockNews = (ticker: string, limit: number = 10) =>
  api.get(`/v1/stocks/${ticker}/news`, { params: { limit } })
