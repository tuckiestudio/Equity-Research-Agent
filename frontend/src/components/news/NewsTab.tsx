import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Newspaper, RefreshCw, TrendingUp, TrendingDown, Minus, Calendar } from 'lucide-react'
import { getNews, analyzeNews, getSentiment, type NewsAnalysis } from '@/services/news'
import { formatShortDate } from '@/utils/format'
import SentimentChart from '@/components/charts/SentimentChart'

interface NewsTabProps {
  ticker: string
}

export default function NewsTab({ ticker }: NewsTabProps) {
  const queryClient = useQueryClient()

  const { data: news, isLoading: newsLoading } = useQuery({
    queryKey: ['news', ticker],
    queryFn: () => getNews(ticker).then((res) => res.data),
  })

  const { data: sentiment } = useQuery({
    queryKey: ['sentiment', ticker],
    queryFn: () => getSentiment(ticker).then((res) => res.data),
  })

  const analyzeMutation = useMutation({
    mutationFn: () => analyzeNews(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['news', ticker] })
      queryClient.invalidateQueries({ queryKey: ['sentiment', ticker] })
    },
  })



  return (
    <div className="space-y-6">
      {/* Header with Refresh */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Newspaper className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-semibold text-text-primary">News Analysis</h2>
        </div>
        <button
          onClick={() => analyzeMutation.mutate()}
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

      {/* Sentiment Summary Cards */}
      {sentiment && (
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
                <span className="text-text-primary font-semibold">{sentiment.total_articles}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-secondary">Avg Impact Score</span>
                <span className="text-accent font-semibold">{sentiment.avg_impact_score.toFixed(2)}</span>
              </div>
              <div className="pt-3 border-t border-border">
                <div className="flex gap-4">
                  <div className="flex-1 bg-success/10 rounded p-2 text-center">
                    <p className="text-2xl font-bold text-success">{sentiment.bullish_count}</p>
                    <p className="text-xs text-text-secondary">Bullish</p>
                  </div>
                  <div className="flex-1 bg-surface-elevated rounded p-2 text-center">
                    <p className="text-2xl font-bold text-text-muted">{sentiment.neutral_count}</p>
                    <p className="text-xs text-text-secondary">Neutral</p>
                  </div>
                  <div className="flex-1 bg-danger/10 rounded p-2 text-center">
                    <p className="text-2xl font-bold text-danger">{sentiment.bearish_count}</p>
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

  const getImpactIcon = (label: string) => {
    switch (label.toLowerCase()) {
      case 'bullish':
        return <TrendingUp className="w-4 h-4 text-success" />
      case 'bearish':
        return <TrendingDown className="w-4 h-4 text-danger" />
      default:
        return <Minus className="w-4 h-4 text-text-muted" />
    }
  }

  const getImpactColor = (label: string) => {
    switch (label.toLowerCase()) {
      case 'bullish':
        return 'bg-success/10 text-success border-success/20'
      case 'bearish':
        return 'bg-danger/10 text-danger border-danger/20'
      default:
        return 'bg-surface-elevated text-text-secondary border-border'
    }
  }

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
            <span>Relevance: {(article.relevance_score * 100).toFixed(0)}%</span>
          </div>
        </div>
        <div className={`flex items-center gap-1.5 px-2 py-1 rounded border ${getImpactColor(article.impact_label)}`}>
          {getImpactIcon(article.impact_label)}
          <span className="text-xs font-medium capitalize">{article.impact_label}</span>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-border/50 animate-fade-in">
          <p className="text-sm text-text-secondary">{article.ai_summary}</p>
          <div className="flex items-center gap-4 mt-3 text-xs text-text-muted">
            <span>Impact Score: {article.impact_score.toFixed(2)}</span>
            <span>Thesis Alignment: {article.thesis_alignment}</span>
          </div>
        </div>
      )}
    </div>
  )
}
