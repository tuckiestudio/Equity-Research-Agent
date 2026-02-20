import api from '@/services/api'

export interface NewsAnalysis {
  id: string
  headline: string
  impact_label: string
  impact_score: number
  relevance_score: number
  thesis_alignment: string
  ai_summary: string
  published_at: string
}

export interface SentimentSummary {
  avg_impact_score: number
  bullish_count: number
  bearish_count: number
  neutral_count: number
  total_articles: number
}

export interface Note {
  id: string
  title: string
  content: string
  note_type?: string
  extracted_sentiment?: string
  is_ai_processed: boolean
  created_at: string
}

export interface Thesis {
  id: string
  title: string
  summary: string
  full_text: string
  stance: string
  confidence: number
  target_price?: number
  version: number
}

export interface ThesisChange {
  id: string
  change_type: string
  previous_stance?: string
  new_stance?: string
  change_summary: string
  created_at: string
}

export interface WatchItem {
  id: string
  title: string
  description: string
  category: string
  potential_impact: string
  status: string
  expected_date?: string
}

export const getNews = (ticker: string) =>
  api.get<NewsAnalysis[]>(`/v1/news/${ticker}`)

export const analyzeNews = (ticker: string) =>
  api.post<NewsAnalysis[]>(`/v1/news/${ticker}/analyze`)

export const getSentiment = (ticker: string) =>
  api.get<SentimentSummary>(`/v1/news/${ticker}/sentiment`)

export const getNotes = (ticker: string) =>
  api.get<Note[]>(`/v1/notes/${ticker}`)

export const createNote = (ticker: string, data: { title: string; content: string; note_type?: string }) =>
  api.post<Note>(`/v1/notes/${ticker}`, data)

export const updateNote = (noteId: string, data: { title: string; content: string }) =>
  api.put<Note>(`/v1/notes/${noteId}`, data)

export const deleteNote = (noteId: string) =>
  api.delete(`/v1/notes/${noteId}`)

export const extractNoteEntities = (noteId: string) =>
  api.post<Note>(`/v1/notes/${noteId}/extract`, {})

export const getThesis = (ticker: string) =>
  api.get<Thesis>(`/v1/thesis/${ticker}`)

export const generateThesis = (ticker: string) =>
  api.post<Thesis>(`/v1/thesis/${ticker}/generate`)

export const updateThesis = (thesisId: string, data: { new_information: string }) =>
  api.put<Thesis>(`/v1/thesis/${thesisId}/update`, data)

export const getThesisHistory = (thesisId: string) =>
  api.get<ThesisChange[]>(`/v1/thesis/${thesisId}/history`)

export const getWatchItems = (ticker: string) =>
  api.get<WatchItem[]>(`/v1/watch/${ticker}`)

export const generateWatchItems = (ticker: string) =>
  api.post<WatchItem[]>(`/v1/watch/${ticker}/generate`)
