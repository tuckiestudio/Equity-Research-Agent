import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Building2,
  TrendingUp,
  PieChart,
  Newspaper,
  FileText,
  Scale,
  Eye,
} from 'lucide-react'
import { getStockDetail } from '@/services/stocks'
import { getSentiment, getWatchItems, getThesis } from '@/services/news'
import { formatCurrency, formatPercent } from '@/utils/format'
import ModelTab from '@/components/model/ModelTab'
import NewsTab from '@/components/news/NewsTab'
import NotesTab from '@/components/notes/NotesTab'
import ThesisTab from '@/components/thesis/ThesisTab'

type TabId = 'overview' | 'model' | 'news' | 'notes' | 'thesis'

export default function StockDetail() {
  const { ticker } = useParams<{ ticker: string }>()
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  const { data: stock } = useQuery({
    queryKey: ['stock', ticker],
    queryFn: () => getStockDetail(ticker!).then((res) => res.data),
    enabled: !!ticker,
  })

  const { data: sentiment } = useQuery({
    queryKey: ['sentiment', ticker],
    queryFn: () => getSentiment(ticker!).then((res) => res.data),
    enabled: !!ticker,
  })

  const { data: watchItems } = useQuery({
    queryKey: ['watch', ticker],
    queryFn: () => getWatchItems(ticker!).then((res) => res.data),
    enabled: !!ticker,
  })

  const { data: thesis } = useQuery({
    queryKey: ['thesis', ticker],
    queryFn: () => getThesis(ticker!).then((res) => res.data),
    enabled: !!ticker,
  })

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <PieChart className="w-4 h-4" /> },
    { id: 'model', label: 'Model', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'news', label: 'News', icon: <Newspaper className="w-4 h-4" /> },
    { id: 'notes', label: 'Notes', icon: <FileText className="w-4 h-4" /> },
    { id: 'thesis', label: 'Thesis', icon: <Scale className="w-4 h-4" /> },
  ]

  const getSentimentBadge = () => {
    if (!sentiment) return null
    const ratio = sentiment.bullish_count / Math.max(sentiment.total_articles, 1)
    if (ratio > 0.6) {
      return { label: 'Bullish', color: 'bg-success/20 text-success border-success/30' }
    } else if (ratio < 0.4) {
      return { label: 'Bearish', color: 'bg-danger/20 text-danger border-danger/30' }
    }
    return { label: 'Neutral', color: 'bg-surface-elevated text-text-secondary border-border' }
  }

  const sentimentBadge = getSentimentBadge()

  return (
    <div className="animate-fade-in">
      {/* Header Section */}
      <div className="mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-text-primary">
                {ticker?.toUpperCase()}
              </h1>
              {sentimentBadge && (
                <span className={`px-2.5 py-0.5 rounded-full text-sm font-medium border ${sentimentBadge.color}`}>
                  {sentimentBadge.label}
                </span>
              )}
            </div>
            <p className="text-text-secondary">
              {stock?.company_name || 'Loading...'}
            </p>
            {(stock?.sector || stock?.industry) && (
              <p className="text-text-muted text-sm mt-1">
                {stock.sector}{stock.industry && ` • ${stock.industry}`}
              </p>
            )}
          </div>

          {/* Price Display */}
          {stock?.current_price && (
            <div className="text-right">
              <p className="text-2xl font-bold text-text-primary">
                ${stock.current_price.toFixed(2)}
              </p>
              {stock.change_percent !== undefined && (
                <p className={`text-sm font-medium ${stock.change_percent >= 0 ? 'text-success' : 'text-danger'
                  }`}>
                  {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                </p>
              )}
            </div>
          )}
        </div>

        {/* Quick Stats */}
        {stock && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
            {stock.market_cap && (
              <div className="bg-surface-card rounded-lg p-3 border border-border" data-testid="market-cap">
                <p className="text-xs text-text-muted mb-1">Market Cap</p>
                <p className="text-text-primary font-semibold">{formatCurrency(stock.market_cap)}</p>
              </div>
            )}
            {stock.pe_ratio && (
              <div className="bg-surface-card rounded-lg p-3 border border-border" data-testid="pe-ratio">
                <p className="text-xs text-text-muted mb-1">P/E Ratio</p>
                <p className="text-text-primary font-semibold">{stock.pe_ratio.toFixed(2)}</p>
              </div>
            )}
            {stock.ev_ebitda && (
              <div className="bg-surface-card rounded-lg p-3 border border-border" data-testid="ev-ebitda">
                <p className="text-xs text-text-muted mb-1">EV/EBITDA</p>
                <p className="text-text-primary font-semibold">{stock.ev_ebitda.toFixed(2)}</p>
              </div>
            )}
            {stock.dividend_yield && (
              <div className="bg-surface-card rounded-lg p-3 border border-border" data-testid="dividend-yield">
                <p className="text-xs text-text-muted mb-1">Dividend Yield</p>
                <p className="text-text-primary font-semibold">{formatPercent(stock.dividend_yield)}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-border mb-6">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all relative ${activeTab === tab.id
                  ? 'text-accent'
                  : 'text-text-secondary hover:text-text-primary'
                }`}
            >
              {tab.icon}
              {tab.label}
              {activeTab === tab.id && (
                <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {activeTab === 'overview' && (
          <OverviewTab
            stock={stock}
            sentiment={sentiment}
            watchItems={watchItems}
            thesis={thesis}
          />
        )}
        {activeTab === 'model' && ticker && <ModelTab ticker={ticker} />}
        {activeTab === 'news' && ticker && <NewsTab ticker={ticker} />}
        {activeTab === 'notes' && ticker && <NotesTab ticker={ticker} />}
        {activeTab === 'thesis' && ticker && <ThesisTab ticker={ticker} />}
      </div>
    </div>
  )
}

// Overview Tab Component
interface OverviewTabProps {
  stock: any
  sentiment: any
  watchItems: any
  thesis: any
}

function OverviewTab({ sentiment, watchItems, thesis }: OverviewTabProps) {
  const getSentimentColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'bullish':
        return 'text-success border-success/30 bg-success/10'
      case 'bearish':
        return 'text-danger border-danger/30 bg-danger/10'
      default:
        return 'text-text-secondary border-border bg-surface-elevated'
    }
  }

  return (
    <div className="space-y-6">
      {/* Sentiment & Stats Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sentiment Card */}
        {sentiment && (
          <div className="bg-surface-card rounded-lg p-4 border border-border">
            <h3 className="text-sm font-semibold text-text-secondary mb-4">News Sentiment</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-text-secondary">Total Articles</span>
                <span className="text-text-primary font-semibold">{sentiment.total_articles}</span>
              </div>
              <div className="flex gap-2">
                <div className="flex-1 bg-success/10 rounded p-2 text-center">
                  <p className="text-lg font-bold text-success">{sentiment.bullish_count}</p>
                  <p className="text-xs text-text-muted">Bullish</p>
                </div>
                <div className="flex-1 bg-surface-elevated rounded p-2 text-center">
                  <p className="text-lg font-bold text-text-muted">{sentiment.neutral_count}</p>
                  <p className="text-xs text-text-muted">Neutral</p>
                </div>
                <div className="flex-1 bg-danger/10 rounded p-2 text-center">
                  <p className="text-lg font-bold text-danger">{sentiment.bearish_count}</p>
                  <p className="text-xs text-text-muted">Bearish</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Watch Items Preview */}
        {watchItems && watchItems.length > 0 && (
          <div className="lg:col-span-2 bg-surface-card rounded-lg p-4 border border-border">
            <div className="flex items-center gap-2 mb-4">
              <Eye className="w-4 h-4 text-accent" />
              <h3 className="text-sm font-semibold text-text-secondary">Watch Items</h3>
            </div>
            <div className="space-y-2">
              {watchItems.slice(0, 3).map((item: any) => (
                <div
                  key={item.id}
                  className="flex items-start gap-3 p-3 bg-surface/50 rounded border border-border/50"
                >
                  <div className={`px-2 py-0.5 rounded text-xs border ${getSentimentColor(item.potential_impact)}`}>
                    {item.potential_impact}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-text-primary font-medium text-sm truncate">{item.title}</p>
                    <p className="text-text-muted text-xs line-clamp-1">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Active Thesis Summary */}
      {thesis && (
        <div className="bg-surface-card rounded-lg p-6 border border-border">
          <div className="flex items-center gap-2 mb-4">
            <Scale className="w-5 h-5 text-accent" />
            <h3 className="text-lg font-semibold text-text-primary">Investment Thesis</h3>
          </div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h4 className="text-xl font-bold text-text-primary mb-2">{thesis.title}</h4>
              <p className="text-text-secondary">{thesis.summary}</p>
            </div>
            <div className={`px-3 py-1.5 rounded border ${getSentimentColor(thesis.stance)} capitalize font-medium`}>
              {thesis.stance}
            </div>
          </div>
          {thesis.target_price && (
            <div className="mt-4 flex items-center gap-2 bg-surface-elevated rounded-lg px-4 py-3 inline-flex">
              <span className="text-text-muted text-sm">Target Price:</span>
              <span className="text-text-primary font-bold text-lg">${thesis.target_price.toFixed(2)}</span>
              <span className="text-text-muted text-sm">({Math.round(thesis.confidence * 100)}% confidence)</span>
            </div>
          )}
        </div>
      )}

      {/* Empty State */}
      {!thesis && !sentiment && !watchItems && (
        <div className="text-center py-12 text-text-secondary">
          <Building2 className="w-12 h-12 mx-auto mb-3 text-text-muted" />
          <p>Explore the tabs to see detailed analysis</p>
        </div>
      )}
    </div>
  )
}
