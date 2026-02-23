import { useQuery } from '@tanstack/react-query'
import api from '@/services/api'
import { TrendingUp, TrendingDown, Activity, AlertCircle, Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface MarketIndex {
  name: string
  symbol: string
  price: number
  change: number
  change_percent: number
  high?: number
  low?: number
  open?: number
  previous_close?: number
}

interface MarketMover {
  ticker: string
  company_name: string
  price: number
  change: number
  change_percent: number
  volume?: number
  sector?: string
}

interface MarketSummary {
  indices: MarketIndex[]
  top_gainers: MarketMover[]
  top_losers: MarketMover[]
  most_active: MarketMover[]
}

interface NewsItem {
  headline: string
  source: string
  url?: string
  published_at?: string
  sentiment?: string
}

export default function Market() {
  const { data: marketData, isLoading, error, refetch } = useQuery({
    queryKey: ['market', 'summary'],
    queryFn: async () => {
      const response = await api.get<MarketSummary>('/v1/market/summary')
      return response.data
    },
    refetchInterval: 60000, // Refresh every minute
  })

  const { data: newsData } = useQuery({
    queryKey: ['market', 'news'],
    queryFn: async () => {
      const response = await api.get<NewsItem[]>('/v1/market/news')
      return response.data
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-12 h-12 text-accent animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-card">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 mx-auto text-danger mb-4" />
          <p className="text-danger mb-4">Failed to load market data</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-text-primary mb-1">
          Market Overview
        </h2>
        <p className="text-text-secondary">
          Real-time market indices and top movers
        </p>
      </div>

      {/* Market Indices */}
      <section>
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          Major Indices
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {marketData?.indices.map((index) => (
            <div
              key={index.symbol}
              className="glass-card p-4 hover:bg-surface-elevated transition-colors"
            >
              <div className="mb-2">
                <span className="text-sm text-text-secondary">{index.name}</span>
                <span className="block text-xs text-text-muted">{index.symbol}</span>
              </div>
              <div className="text-2xl font-bold text-text-primary mb-1">
                {index.price.toFixed(2)}
              </div>
              <div
                className={clsx(
                  'flex items-center gap-1 text-sm font-medium',
                  index.change >= 0 ? 'text-green-500' : 'text-danger'
                )}
              >
                {index.change >= 0 ? (
                  <TrendingUp className="w-4 h-4" />
                ) : (
                  <TrendingDown className="w-4 h-4" />
                )}
                <span>{index.change >= 0 ? '+' : ''}{index.change.toFixed(2)}</span>
                <span>({index.change_percent >= 0 ? '+' : ''}{index.change_percent.toFixed(2)}%)</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Top Gainers & Losers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Gainers */}
        <section>
          <h3 className="text-lg font-semibold text-green-500 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5" />
            Top Gainers
          </h3>
          <div className="glass-card divide-y divide-border">
            {marketData?.top_gainers.map((mover) => (
              <div key={mover.ticker} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-text-primary">
                        {mover.ticker}
                      </span>
                      <span className="text-text-secondary truncate">
                        {mover.company_name}
                      </span>
                    </div>
                    {mover.sector && (
                      <span className="text-xs text-text-muted">{mover.sector}</span>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-text-primary font-medium">
                      ${mover.price.toFixed(2)}
                    </div>
                    <div className="text-green-500 text-sm font-medium">
                      +{mover.change_percent.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {(!marketData?.top_gainers || marketData.top_gainers.length === 0) && (
              <div className="p-8 text-center text-text-secondary">
                No gainers data available
              </div>
            )}
          </div>
        </section>

        {/* Top Losers */}
        <section>
          <h3 className="text-lg font-semibold text-danger mb-4 flex items-center gap-2">
            <TrendingDown className="w-5 h-5" />
            Top Losers
          </h3>
          <div className="glass-card divide-y divide-border">
            {marketData?.top_losers?.map((mover) => (
              <div key={mover.ticker} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-text-primary">
                        {mover.ticker}
                      </span>
                      <span className="text-text-secondary truncate">
                        {mover.company_name}
                      </span>
                    </div>
                    {mover.sector && (
                      <span className="text-xs text-text-muted">{mover.sector}</span>
                    )}
                  </div>
                  <div className="text-right">
                    <div className="text-text-primary font-medium">
                      ${mover.price.toFixed(2)}
                    </div>
                    <div className="text-danger text-sm font-medium">
                      {mover.change_percent.toFixed(2)}%
                    </div>
                  </div>
                </div>
              </div>
            ))}
            {(!marketData?.top_losers || marketData.top_losers.length === 0) && (
              <div className="p-8 text-center text-text-secondary">
                No losers data available
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Most Active */}
      <section>
        <h3 className="text-lg font-semibold text-text-primary mb-4">
          Most Active by Volume
        </h3>
        <div className="glass-card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                  Ticker
                </th>
                <th className="text-left py-3 px-4 text-sm font-medium text-text-secondary">
                  Company
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                  Price
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                  Change %
                </th>
                <th className="text-right py-3 px-4 text-sm font-medium text-text-secondary">
                  Volume
                </th>
              </tr>
            </thead>
            <tbody>
              {marketData?.most_active.map((mover) => (
                <tr key={mover.ticker} className="border-b border-border hover:bg-surface-elevated">
                  <td className="py-3 px-4">
                    <span className="font-semibold text-text-primary">{mover.ticker}</span>
                  </td>
                  <td className="py-3 px-4 text-text-secondary">{mover.company_name}</td>
                  <td className="py-3 px-4 text-right text-text-primary">
                    ${mover.price.toFixed(2)}
                  </td>
                  <td
                    className={clsx(
                      'py-3 px-4 text-right font-medium',
                      mover.change_percent >= 0 ? 'text-green-500' : 'text-danger'
                    )}
                  >
                    {mover.change_percent >= 0 ? '+' : ''}{mover.change_percent.toFixed(2)}%
                  </td>
                  <td className="py-3 px-4 text-right text-text-muted">
                    {mover.volume?.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(!marketData?.most_active || marketData.most_active.length === 0) && (
            <div className="p-8 text-center text-text-secondary">
              No most active data available
            </div>
          )}
        </div>
      </section>

      {/* Market News */}
      {newsData && 'news' in newsData && Array.isArray(newsData.news) && newsData.news.length > 0 && (
        <section>
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            Market News
          </h3>
          <div className="grid gap-4">
            {(newsData.news as NewsItem[]).slice(0, 5).map((article: NewsItem, idx: number) => (
              <a
                key={idx}
                href={article.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="glass-card p-4 hover:bg-surface-elevated transition-colors block"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <h4 className="text-text-primary font-medium mb-1">
                      {article.headline}
                    </h4>
                    <div className="flex items-center gap-3 text-sm text-text-muted">
                      <span>{article.source}</span>
                      {article.published_at && (
                        <span>•</span>
                      )}
                      {article.published_at && (
                        <span>
                          {new Date(article.published_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  {article.sentiment && (
                    <span
                      className={clsx(
                        'px-2 py-1 rounded text-xs font-medium',
                        article.sentiment === 'positive' && 'bg-green-500/10 text-green-500',
                        article.sentiment === 'negative' && 'bg-red-500/10 text-danger',
                        article.sentiment === 'neutral' && 'bg-border text-text-muted'
                      )}
                    >
                      {article.sentiment}
                    </span>
                  )}
                </div>
              </a>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
