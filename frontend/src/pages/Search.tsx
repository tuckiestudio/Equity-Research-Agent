import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { searchStocks } from '@/services/stocks'
import { getPortfolios, addStockToPortfolio, createPortfolio } from '@/services/portfolios'
import { Search as SearchIcon, Plus, Loader2, TrendingUp, AlertCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'

interface SearchResponse {
  id: string
  ticker: string
  company_name: string
  exchange?: string
  sector?: string
  industry?: string
}

export default function Search() {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newPortfolioName, setNewPortfolioName] = useState('')

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Get portfolios for adding stocks
  const { data: portfolios, refetch: refetchPortfolios } = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const response = await getPortfolios()
      return response.data
    },
  })

  // Create portfolio mutation
  const createPortfolioMutation = useMutation({
    mutationFn: async (name: string) => {
      await createPortfolio({ name })
    },
    onSuccess: () => {
      refetchPortfolios()
      setShowCreateForm(false)
      setNewPortfolioName('')
    },
  })

  // Set first portfolio as default
  useEffect(() => {
    if (portfolios && portfolios.length > 0 && !selectedPortfolioId) {
      setSelectedPortfolioId(portfolios[0].id)
    }
  }, [portfolios, selectedPortfolioId])

  // Search stocks
  const {
    data: searchResults,
    isLoading: isSearching,
    error,
  } = useQuery({
    queryKey: ['stocks', 'search', debouncedQuery],
    queryFn: async () => {
      const response = await searchStocks(debouncedQuery)
      return response.data
    },
    enabled: debouncedQuery.length >= 2,
  })

  // Add stock mutation
  const addStockMutation = useMutation({
    mutationFn: async ({ ticker }: { ticker: string }) => {
      if (!selectedPortfolioId) {
        throw new Error('No portfolio selected. Please create or select a portfolio first.')
      }
      const response = await addStockToPortfolio(selectedPortfolioId, { ticker })
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['stocks', 'search'] })
    },
    onError: (error) => {
      console.error('Failed to add stock:', error)
    },
  })

  const handleAddStock = (ticker: string) => {
    addStockMutation.mutate({ ticker })
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-text-primary mb-1">
          Stock Search
        </h2>
        <p className="text-text-secondary">
          Find and add stocks to your portfolio
        </p>
      </div>

      {/* Search Input */}
      <div className="glass-card mb-6">
        <div className="relative">
          <SearchIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by ticker or company name..."
            className={clsx(
              'w-full pl-12 pr-4 py-4 bg-surface',
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
      </div>

      {/* Portfolio Selector or Create Form */}
      {portfolios && portfolios.length > 0 ? (
        <div className="mb-6">
          <label className="text-sm text-text-secondary mb-2 block">
            Add to portfolio:
          </label>
          <select
            value={selectedPortfolioId || ''}
            onChange={(e) => setSelectedPortfolioId(e.target.value)}
            className="px-4 py-2 bg-surface border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {portfolios.map((portfolio) => (
              <option key={portfolio.id} value={portfolio.id}>
                {portfolio.name}
              </option>
            ))}
          </select>
          {addStockMutation.error && (
            <p className="mt-2 text-sm text-danger flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {addStockMutation.error.message}
            </p>
          )}
          {addStockMutation.isSuccess && (
            <p className="mt-2 text-sm text-green-500 flex items-center gap-2">
              <span className="w-4 h-4">✓</span>
              Stock added successfully!
            </p>
          )}
        </div>
      ) : showCreateForm ? (
        <div className="glass-card mb-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">
            Create Your First Portfolio
          </h3>
          <form onSubmit={(e) => {
            e.preventDefault()
            if (newPortfolioName.trim()) {
              createPortfolioMutation.mutate(newPortfolioName.trim())
            }
          }}>
            <input
              type="text"
              value={newPortfolioName}
              onChange={(e) => setNewPortfolioName(e.target.value)}
              placeholder="Enter portfolio name"
              className="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-accent mb-3"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createPortfolioMutation.isPending || !newPortfolioName.trim()}
                className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50"
              >
                {createPortfolioMutation.isPending ? 'Creating...' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="glass-card mb-6">
          <p className="text-text-secondary mb-4">
            You need a portfolio before adding stocks
          </p>
          <button
            onClick={() => setShowCreateForm(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            Create Portfolio
          </button>
        </div>
      )}

      {/* Loading State */}
      {isSearching && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-accent animate-spin" />
          <span className="ml-3 text-text-secondary">Searching...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="glass-card">
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 mx-auto text-danger mb-4" />
            <p className="text-danger">Failed to search stocks</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {searchQuery.length < 2 && !isSearching && (
        <div className="glass-card">
          <div className="text-center py-16">
            <TrendingUp className="w-16 h-16 mx-auto text-text-muted mb-6" />
            <h3 className="text-xl font-semibold text-text-primary mb-2">
              Search for stocks
            </h3>
            <p className="text-text-secondary max-w-md mx-auto">
              Enter a ticker symbol (e.g., AAPL) or company name to find stocks
            </p>
          </div>
        </div>
      )}

      {/* No Results */}
      {searchQuery.length >= 2 && !isSearching && (!searchResults || searchResults.length === 0) && (
        <div className="glass-card">
          <div className="text-center py-12">
            <SearchIcon className="w-12 h-12 mx-auto text-text-muted mb-4" />
            <p className="text-text-secondary">No results found for "{searchQuery}"</p>
          </div>
        </div>
      )}

      {/* Search Results */}
      {searchResults && searchResults.length > 0 && (
        <div className="space-y-3">
          {(searchResults as unknown as SearchResponse[]).map((stock: SearchResponse) => (
            <div
              key={stock.id}
              className="glass-card p-4 hover:bg-surface-elevated transition-colors"
            >
              <div className="flex items-center justify-between">
                <Link
                  to={`/stock/${stock.ticker}`}
                  className="flex-1 min-w-0"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-accent/10 flex items-center justify-center">
                      <span className="font-bold text-accent text-sm">
                        {stock.ticker.substring(0, 2)}
                      </span>
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-text-primary">
                          {stock.ticker}
                        </span>
                        <span className="text-text-secondary truncate">
                          {stock.company_name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 mt-1 text-sm text-text-muted">
                        {stock.exchange && <span>{stock.exchange}</span>}
                        {stock.sector && (
                          <>
                            <span>•</span>
                            <span>{stock.sector}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
                <button
                  onClick={() => handleAddStock(stock.ticker)}
                  disabled={addStockMutation.isPending || !selectedPortfolioId}
                  className={clsx(
                    'ml-4 p-2 rounded-lg transition-colors',
                    'hover:bg-accent/10 text-accent',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                  title={!selectedPortfolioId ? 'Create a portfolio first' : 'Add to portfolio'}
                >
                  {addStockMutation.isSuccess ? (
                    <span className="text-green-500">✓</span>
                  ) : addStockMutation.isPending ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <Plus className="w-5 h-5" />
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
