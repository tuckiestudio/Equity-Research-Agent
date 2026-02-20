import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Scale,
  Sparkles,
  RefreshCw,
  Target,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { getThesis, generateThesis, getThesisHistory, type ThesisChange } from '@/services/news'
import { formatDate } from '@/utils/format'

interface ThesisTabProps {
  ticker: string
}

export default function ThesisTab({ ticker }: ThesisTabProps) {
  const queryClient = useQueryClient()
  const [showHistory, setShowHistory] = useState(false)

  const { data: thesis, isLoading } = useQuery({
    queryKey: ['thesis', ticker],
    queryFn: () => getThesis(ticker).then((res) => res.data),
  })

  const { data: history } = useQuery({
    queryKey: ['thesis-history', thesis?.id],
    queryFn: () => getThesisHistory(thesis!.id).then((res) => res.data),
    enabled: !!thesis?.id && showHistory,
  })

  const generateMutation = useMutation({
    mutationFn: () => generateThesis(ticker),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['thesis', ticker] })
    },
  })

  const getStanceIcon = (stance: string) => {
    switch (stance.toLowerCase()) {
      case 'bull':
      case 'bullish':
        return <TrendingUp className="w-5 h-5 text-success" />
      case 'bear':
      case 'bearish':
        return <TrendingDown className="w-5 h-5 text-danger" />
      default:
        return <Minus className="w-5 h-5 text-text-muted" />
    }
  }

  const getStanceColor = (stance: string) => {
    switch (stance.toLowerCase()) {
      case 'bull':
      case 'bullish':
        return 'bg-success/10 text-success border-success/20'
      case 'bear':
      case 'bearish':
        return 'bg-danger/10 text-danger border-danger/20'
      default:
        return 'bg-surface-elevated text-text-secondary border-border'
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 text-accent animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-semibold text-text-primary">Investment Thesis</h2>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white px-3 py-1.5 rounded text-sm transition-colors disabled:opacity-50"
        >
          {generateMutation.isPending ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4" />
          )}
          {thesis ? 'Regenerate' : 'Generate Thesis'}
        </button>
      </div>

      {/* Thesis Card */}
      {thesis ? (
        <div className="bg-surface-card rounded-lg border border-border overflow-hidden">
          {/* Thesis Header */}
          <div className="p-6 border-b border-border">
            <div className="flex items-start justify-between gap-4 mb-4">
              <div>
                <h3 className="text-xl font-bold text-text-primary mb-2">{thesis.title}</h3>
                <p className="text-sm text-text-secondary">{thesis.summary}</p>
              </div>
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded border ${getStanceColor(thesis.stance)}`}>
                {getStanceIcon(thesis.stance)}
                <span className="font-medium capitalize">{thesis.stance}</span>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="flex flex-wrap gap-4">
              {thesis.target_price && (
                <div className="flex items-center gap-2 bg-surface-elevated rounded-lg px-3 py-2">
                  <Target className="w-4 h-4 text-accent" />
                  <div>
                    <p className="text-xs text-text-muted">Target Price</p>
                    <p className="text-sm font-bold text-text-primary">
                      ${thesis.target_price.toFixed(2)}
                    </p>
                  </div>
                </div>
              )}
              <div className="flex items-center gap-2 bg-surface-elevated rounded-lg px-3 py-2">
                <div className="w-4 h-4 rounded-full bg-accent/20 flex items-center justify-center">
                  <span className="text-xs text-accent font-bold">%</span>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Confidence</p>
                  <p className="text-sm font-bold text-text-primary">
                    {Math.round(thesis.confidence * 100)}%
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 bg-surface-elevated rounded-lg px-3 py-2">
                <Clock className="w-4 h-4 text-text-muted" />
                <div>
                  <p className="text-xs text-text-muted">Version</p>
                  <p className="text-sm font-bold text-text-primary">v{thesis.version}</p>
                </div>
              </div>
            </div>
          </div>

          {/* Full Text */}
          <div className="p-6">
            <h4 className="text-sm font-semibold text-text-secondary mb-3">Detailed Analysis</h4>
            <div className="prose prose-invert prose-sm max-w-none">
              <pre className="whitespace-pre-wrap font-sans text-text-primary bg-surface/50 p-4 rounded-lg">
                {thesis.full_text}
              </pre>
            </div>
          </div>

          {/* History Toggle */}
          <div className="border-t border-border">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="w-full flex items-center justify-between p-4 text-sm text-text-secondary hover:text-text-primary hover:bg-surface-elevated/30 transition-colors"
            >
              <span className="font-medium">Thesis History</span>
              {showHistory ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showHistory && history && (
              <div className="px-4 pb-4 animate-fade-in">
                {history.length > 0 ? (
                  <div className="space-y-3">
                    {history.map((change, idx) => (
                      <HistoryItem key={change.id} change={change} index={history.length - idx} />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-text-secondary text-center py-4">
                    No history available yet
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-surface-card rounded-lg p-8 text-center border border-border">
          <Scale className="w-12 h-12 text-text-muted mx-auto mb-3" />
          <p className="text-text-secondary mb-1">No thesis yet</p>
          <p className="text-text-muted text-sm mb-4">
            Generate an AI-powered investment thesis for {ticker}
          </p>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="bg-accent hover:bg-accent-hover text-white px-4 py-2 rounded transition-colors disabled:opacity-50"
          >
            {generateMutation.isPending ? 'Generating...' : 'Generate Thesis'}
          </button>
        </div>
      )}
    </div>
  )
}

function HistoryItem({ change, index }: { change: ThesisChange; index: number }) {
  return (
    <div className="border-l-2 border-accent pl-4 py-1">
      <div className="flex items-center gap-2 text-xs text-text-muted mb-1">
        <span className="font-mono bg-surface-elevated px-1.5 py-0.5 rounded">#{index}</span>
        <span>{formatDate(change.created_at)}</span>
        <span className="text-accent">{change.change_type}</span>
      </div>
      <p className="text-sm text-text-secondary">{change.change_summary}</p>
      {change.previous_stance && change.new_stance && (
        <div className="flex items-center gap-2 mt-2 text-xs">
          <span className="text-text-muted">Stance:</span>
          <span className="text-text-secondary">{change.previous_stance}</span>
          <span className="text-accent">→</span>
          <span className="text-text-primary font-medium">{change.new_stance}</span>
        </div>
      )}
    </div>
  )
}
