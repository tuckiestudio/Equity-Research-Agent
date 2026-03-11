import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Newspaper, RefreshCw, TrendingUp, TrendingDown, Minus, Calendar, AlertCircle } from 'lucide-react'
import { getNews, analyzeNews, getSentiment, type NewsAnalysis } from '@/services/news'
import { formatShortDate } from '@/utils/format'
import SentimentChart from '@/components/charts/SentimentChart'
import { Link } from 'react-router-dom'

interface NewsTabProps {
  ticker: string
}

export default function NewsTab({ ticker }: NewsTabProps) {
  const queryClient = useQueryClient()
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)

  const { data: news, isLoading: newsLoading } = useQuery({
    queryKey: ['news', ticker],
    queryFn: () => getNews(ticker).then((res) => res.data),
  })

  const { data: sentiment, error: sentimentError } = useQuery({
    queryKey: ['sentiment', ticker],
    queryFn: () => getSentiment(ticker).then((res) => res.data),
    retry: 1,
  })

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeNews(ticker, undefined, 20),
    onMutate: () => {
      console.log('Starting news analysis for:', ticker)
    },
    onSuccess: () => {
      console.log('News analysis completed successfully')
      queryClient.invalidateQueries({ queryKey: ['news', ticker] })
      queryClient.invalidateQueries({ queryKey: ['sentiment', ticker] })
      setAnalyzeError(null)
    },
    onError: (error: any) => {
      console.error('Analyze news error:', error)
      // Handle different error response formats
      let errorMsg = 'Failed to analyze news'
      if (error.response?.data?.detail) {
        const detail = error.response.data.detail
        if (Array.isArray(detail)) {
          // Validation errors array
          errorMsg = detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ')
        } else if (typeof detail === 'string') {
          errorMsg = detail
        } else if (detail.msg) {
          errorMsg = detail.msg
        } else {
          errorMsg = JSON.stringify(detail)
        }
      } else if (error.message) {
        errorMsg = error.message
      }
      setAnalyzeError(errorMsg)
    },
  })

  // Check if news items have AI analysis or are basic (no LLM)
  const hasBasicNews = news && news.length > 0 && news.some((article) =>
    article.ai_summary?.includes('AI analysis not available')
  )



  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Newspaper className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-semibold text-text-primary">News Analysis</h2>
        </div>
        <button
          type="button"
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); analyzeMutation.mutate(); }}
          disabled={analyzeMutation.isPending}
          className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white px-3 py-1.5 rounded text-sm transition-colors disabled:opacity-50"
        >
          {analyzeMutation.isPending ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Refresh Analysis
        </button>
      </div>

      {/* Error message */}
      {analyzeError && (
        <div className="bg-danger/10 border border-danger/20 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-danger flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-danger font-medium">Analysis Failed</p>
            <p className="text-danger/80 text-sm mt-1">{analyzeError}</p>
          </div>
        </div>
      )}

      {/* Info banner when news is fetched without AI analysis */}
      {hasBasicNews && (
        <div className="bg-surface-elevated border border-border rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-text-muted flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-text-primary font-medium">Basic News Fetch (AI Analysis Unavailable)</p>
            <p className="text-text-secondary text-sm mt-1">
              News articles have been fetched. To enable AI-powered analysis (sentiment, impact scores, thesis alignment),
              add an API key for Anthropic (Claude) or OpenAI (GPT-4o) in your settings.
            </p>
            <Link to="/settings" className="text-accent hover:underline text-sm mt-2 inline-block">
              Go to Settings →
            </Link>
          </div>
        </div>
      )}

      {/* Sentiment Summary Cards */}
      {sentimentError && (
        <div className="bg-surface-elevated/50 border border-border rounded-lg p-4 text-center text-text-secondary">
          <p className="text-sm">Sentiment data unavailable - refresh analysis to generate</p>
        </div>
      )}

      {sentiment && !sentimentError && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-surface-card rounded-lg p-4 border border-border">
            <h3 className="text-sm font-semibold text-text-secondary mb-4">Sentiment Distribution</h3>
            <SentimentChart data={sentiment} />
          </div>

          <div className="bg-surface-card rounded-lg p-4 border border-border">
            <h3 className="text-sm font-semibold text-text-secondary mb-4">Overview</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-text-secondary">Total Articles</span>
                <span className="text-text-primary font-semibold">{sentiment.total_articles || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-secondary">Avg Impact Score</span>
                <span className="text-accent font-semibold">{(sentiment.avg_impact_score ?? 0).toFixed(2)}</span>
              </div>
              <div className="pt-3 border-t border-border">
                <div className="flex gap-4">
                  <div className="flex-1 bg-success/10 rounded p-2 text-center">
                    <p className="text-2xl font-bold text-success">{sentiment.bullish_count || 0}</p>
                    <p className="text-xs text-text-secondary">Bullish</p>
                  </div>
                  <div className="flex-1 bg-surface-elevated rounded p-2 text-center">
                    <p className="text-2xl font-bold text-text-muted">{sentiment.neutral_count || 0}</p>
                    <p className="text-xs text-text-secondary">Neutral</p>
                  </div>
                  <div className="flex-1 bg-danger/10 rounded p-2 text-center">
                    <p className="text-2xl font-bold text-danger">{sentiment.bearish_count || 0}</p>
                    <p className="text-xs text-text-secondary">Bearish</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* News Articles List */}
      <div className="bg-surface-card rounded-lg border border-border">
        <div className="p-4 border-b border-border">
          <h3 className="text-sm font-semibold text-text-primary">Analyzed Articles</h3>
        </div>

        {newsLoading ? (
          <div className="p-8 text-center text-text-secondary">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading news...
          </div>
        ) : news && news.length > 0 ? (
          <div className="divide-y divide-border">
            {news.map((article) => (
              <NewsArticleItem key={article.id} article={article} />
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-text-secondary">
            No news articles analyzed yet.
            <button
              onClick={() => analyzeMutation.mutate()}
              className="block mx-auto mt-2 text-accent hover:underline"
            >
              Analyze now
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function NewsArticleItem({ article }: { article: NewsAnalysis }) {
  const [expanded, setExpanded] = useState(false)

  const getImpactIcon = (label: string | null | undefined) => {
    const l = label?.toLowerCase()
    switch (l) {
      case 'bullish':
        return <TrendingUp className="w-4 h-4 text-success" />
      case 'bearish':
        return <TrendingDown className="w-4 h-4 text-danger" />
      default:
        return <Minus className="w-4 h-4 text-text-muted" />
    }
  }

  const getImpactColor = (label: string | null | undefined) => {
    const l = label?.toLowerCase()
    switch (l) {
      case 'bullish':
        return 'bg-success/10 text-success border-success/20'
      case 'bearish':
        return 'bg-danger/10 text-danger border-danger/20'
      default:
        return 'bg-surface-elevated text-text-secondary border-border'
    }
  }

  const relevancePercent = article.relevance_score != null
    ? Math.round(article.relevance_score * 100)
    : 50

  return (
    <div
      className="p-4 hover:bg-surface-elevated/30 transition-colors cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h4 className="text-text-primary font-medium mb-1 truncate" title={article.headline}>
            {article.headline}
          </h4>
          <div className="flex items-center gap-3 text-xs text-text-muted">
            <span className="flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              {formatShortDate(article.published_at)}
            </span>
            <span>Relevance: {relevancePercent}%</span>
          </div>
        </div>
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded border ${getImpactColor(article.impact_label)}`}>
          {getImpactIcon(article.impact_label)}
          <span className="text-xs font-medium capitalize">{article.impact_label || 'neutral'}</span>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-border/50 animate-fade-in">
          <p className="text-sm text-text-secondary">{article.ai_summary}</p>
          <div className="flex items-center gap-4 mt-3 text-xs text-text-muted">
            <span>Impact Score: {(article.impact_score ?? 0).toFixed(2)}</span>
            <span>Thesis Alignment: {article.thesis_alignment || 'neutral'}</span>
          </div>
        </div>
      )}
    </div>
  )
}
