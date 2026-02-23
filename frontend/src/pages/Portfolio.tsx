import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPortfolios, deletePortfolio, createPortfolio } from '@/services/portfolios'
import { Link } from 'react-router-dom'
import { Trash2, Edit2, TrendingUp, AlertCircle, Plus } from 'lucide-react'
import clsx from 'clsx'

export default function Portfolio() {
  const queryClient = useQueryClient()
  const [selectedPortfolio, setSelectedPortfolio] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [newPortfolioName, setNewPortfolioName] = useState('')

  const {
    data: portfolios,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const response = await getPortfolios()
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: async (name: string) => {
      await createPortfolio({ name })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      setIsCreating(false)
      setNewPortfolioName('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await deletePortfolio(id)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      setSelectedPortfolio(null)
    },
  })

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (newPortfolioName.trim()) {
      createMutation.mutate(newPortfolioName.trim())
    }
  }

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    if (confirm('Are you sure you want to delete this portfolio?')) {
      deleteMutation.mutate(id)
    }
  }

  const handlePortfolioClick = (id: string) => {
    setSelectedPortfolio(id === selectedPortfolio ? null : id)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass-card">
        <div className="text-center py-12">
          <AlertCircle className="w-12 h-12 mx-auto text-danger mb-4" />
          <p className="text-danger mb-4">Failed to load portfolios</p>
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

  if (!portfolios || portfolios.length === 0) {
    return (
      <div className="glass-card">
        <div className="text-center py-16">
          <TrendingUp className="w-16 h-16 mx-auto text-text-muted mb-6" />
          <h3 className="text-xl font-semibold text-text-primary mb-2">
            No portfolios yet
          </h3>
          <p className="text-text-secondary mb-6 max-w-md mx-auto">
            Create your first portfolio to start tracking your investments
          </p>
          {!isCreating ? (
            <button
              onClick={() => setIsCreating(true)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium transition-colors"
            >
              <Plus className="w-5 h-5" />
              Create Portfolio
            </button>
          ) : (
            <form onSubmit={handleCreateSubmit} className="max-w-sm mx-auto">
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
                  disabled={createMutation.isPending || !newPortfolioName.trim()}
                  className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false)
                    setNewPortfolioName('')
                  }}
                  className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-text-primary mb-1">
          My Portfolios
        </h2>
        <p className="text-text-secondary">
          Manage and view your investment portfolios
        </p>
      </div>

      <div className="grid gap-4">
        {portfolios.map((portfolio) => (
          <div
            key={portfolio.id}
            className={clsx(
              'glass-card rounded-xl overflow-hidden transition-all duration-200',
              selectedPortfolio === portfolio.id && 'ring-2 ring-accent'
            )}
          >
            {/* Portfolio Header */}
            <div className="p-6">
              <div className="flex items-center justify-between">
                <button
                  onClick={() => handlePortfolioClick(portfolio.id)}
                  className="flex-1 text-left"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center">
                      <TrendingUp className="w-6 h-6 text-accent" />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-text-primary">
                        {portfolio.name}
                      </h3>
                      <p className="text-sm text-text-secondary">
                        {portfolio.stocks?.length || 0} holdings
                      </p>
                    </div>
                  </div>
                </button>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/portfolio/${portfolio.id}`}
                    className="p-2 text-text-secondary hover:text-accent hover:bg-surface-elevated rounded-lg transition-colors"
                    title="View details"
                  >
                    <Edit2 className="w-5 h-5" />
                  </Link>
                  <button
                    onClick={(e) => handleDelete(portfolio.id, e)}
                    disabled={deleteMutation.isPending}
                    className="p-2 text-text-secondary hover:text-danger hover:bg-surface-elevated rounded-lg transition-colors disabled:opacity-50"
                    title="Delete portfolio"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Portfolio Stocks */}
            {selectedPortfolio === portfolio.id && portfolio.stocks && portfolio.stocks.length > 0 && (
              <div className="px-6 pb-6">
                <div className="pt-4 border-t border-border">
                  <h4 className="text-sm font-medium text-text-secondary mb-3">
                    Holdings
                  </h4>
                  <div className="space-y-2">
                    {portfolio.stocks.map((stock) => (
                      <Link
                        key={stock.id}
                        to={`/stock/${stock.ticker}`}
                        className="flex items-center justify-between p-3 bg-surface rounded-lg hover:bg-surface-elevated transition-colors"
                      >
                        <div>
                          <span className="font-medium text-text-primary">
                            {stock.ticker}
                          </span>
                          <span className="text-sm text-text-secondary ml-2">
                            {stock.company_name}
                          </span>
                        </div>
                        {stock.sector && (
                          <span className="text-xs text-text-muted bg-border px-2 py-1 rounded">
                            {stock.sector}
                          </span>
                        )}
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Empty State */}
            {selectedPortfolio === portfolio.id && (!portfolio.stocks || portfolio.stocks.length === 0) && (
              <div className="px-6 pb-6">
                <div className="pt-4 border-t border-border text-center py-8">
                  <p className="text-text-secondary">
                    No stocks in this portfolio yet
                  </p>
                  <Link
                    to="/"
                    className="inline-block mt-4 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
                  >
                    Add Stocks
                  </Link>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
