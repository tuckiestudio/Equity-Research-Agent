import api from './api'
import type {
  Portfolio,
  CreatePortfolioRequest,
  AddStockRequest,
} from './types'

export const getPortfolios = () => api.get<Portfolio[]>('/v1/portfolios')

export const createPortfolio = (data: CreatePortfolioRequest) =>
  api.post<Portfolio>('/v1/portfolios', data)

export const getPortfolio = (id: string) =>
  api.get<Portfolio>(`/v1/portfolios/${id}`)

export const updatePortfolio = (id: string, data: Partial<CreatePortfolioRequest>) =>
  api.patch<Portfolio>(`/v1/portfolios/${id}`, data)

export const deletePortfolio = (id: string) =>
  api.delete(`/v1/portfolios/${id}`)

export const addStockToPortfolio = (portfolioId: string, data: AddStockRequest) =>
  api.post<Portfolio>(`/v1/portfolios/${portfolioId}/stocks`, data)

export const removeStockFromPortfolio = (portfolioId: string, ticker: string) =>
  api.delete(`/v1/portfolios/${portfolioId}/stocks/${ticker}`)

export const archiveStock = (portfolioId: string, ticker: string) =>
  api.post(`/v1/portfolios/${portfolioId}/stocks/${ticker}/archive`)

export const restoreStock = (portfolioId: string, ticker: string) =>
  api.delete(`/v1/portfolios/${portfolioId}/stocks/${ticker}/archive`)

export const getArchivedStocks = (portfolioId: string) =>
  api.get<{ id: string; ticker: string; company_name: string; exchange?: string; sector?: string }[]>(
    `/v1/portfolios/${portfolioId}/archived-stocks`
  )
