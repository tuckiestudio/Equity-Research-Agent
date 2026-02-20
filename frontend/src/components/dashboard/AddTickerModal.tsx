import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { searchStocks } from '@/services/stocks'
import { addStockToPortfolio } from '@/services/portfolios'
import type { StockSearchResult } from '@/services/types'
import { X, Search, Loader2 } from 'lucide-react'
import clsx from 'clsx'

interface AddTickerModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddTickerModal({
  isOpen,
  onClose,
  onSuccess,
}: AddTickerModalProps) {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Search stocks
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['stocks', 'search', debouncedQuery],
    queryFn: async () => {
      const response = await searchStocks(debouncedQuery)
      return response.data
    },
    enabled: debouncedQuery.length >= 2,
  })

  // Get first portfolio ID (simplified for MVP)
  const { data: portfolios } = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const { getPortfolios } = await import('@/services/portfolios')
      const response = await getPortfolios()
      return response.data
    },
    enabled: isOpen,
  })

  const portfolioId = portfolios?.[0]?.id

  // Add stock mutation
  const addStockMutation = useMutation({
    mutationFn: async (ticker: string) => {
      if (!portfolioId) {
        throw new Error('No portfolio found')
      }
      await addStockToPortfolio(portfolioId, { ticker })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      setSearchQuery('')
      onSuccess()
    },
  })

  if (!isOpen) return null

  const handleSelectStock = (ticker: string) => {
    addStockMutation.mutate(ticker)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg glass-card animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-text-primary">
            Add Stock to Portfolio
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-text-secondary hover:text-text-primary hover:bg-surface-elevated rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Input */}
        <div className="relative mb-6">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by ticker or company name..."
            className={clsx(
              'w-full pl-12 pr-4 py-3 bg-surface',
              'border border-border rounded-lg',
              'text-text-primary placeholder-text-muted',
              'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
              'transition-all duration-200'
            )}
            autoFocus
          />
          {isSearching && (
            <div className="absolute right-4 top-1/2 -translate-y-1/2">
              <Loader2 className="w-5 h-5 text-accent animate-spin" />
            </div>
          )}
        </div>

        {/* Search Results */}
        <div className="max-h-80 overflow-auto scrollbar-thin">
          {searchQuery.length < 2 && (
            <div className="text-center py-8">
              <p className="text-text-secondary">
                Enter at least 2 characters to search
              </p>
            </div>
          )}

          {searchQuery.length >= 2 && !isSearching && (!searchResults || searchResults.length === 0) && (
            <div className="text-center py-8">
              <p className="text-text-secondary">No results found</p>
            </div>
          )}

          {searchResults && searchResults.length > 0 && (
            <div className="space-y-1">
              {searchResults.map((result: StockSearchResult) => (
                <button
                  key={result.ticker}
                  onClick={() => handleSelectStock(result.ticker)}
                  disabled={addStockMutation.isPending}
                  data-testid="stock-search-result"
                  className={clsx(
                    'w-full flex items-center justify-between p-4 rounded-lg',
                    'text-left transition-all duration-200',
                    'hover:bg-surface-elevated hover:border-accent/50',
                    'border border-transparent',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-accent">
                        {result.ticker.toUpperCase()}
                      </span>
                      <span className="text-text-primary truncate">
                        {result.name}
                      </span>
                    </div>
                    <p className="text-sm text-text-secondary mt-1">
                      {result.exchange}
                    </p>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-accent/10 flex items-center justify-center text-accent">
                    +
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-border flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}
