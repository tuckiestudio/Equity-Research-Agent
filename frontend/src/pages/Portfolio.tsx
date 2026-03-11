import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPortfolios, getPortfolio, deletePortfolio, createPortfolio, updatePortfolio, removeStockFromPortfolio, archiveStock, restoreStock, getArchivedStocks } from '@/services/portfolios'
import { Link } from 'react-router-dom'
import { Trash2, Edit2, TrendingUp, AlertCircle, Plus, Archive, Undo2 } from 'lucide-react'
import clsx from 'clsx'

export default function Portfolio() {
  const queryClient = useQueryClient()
  const [selectedPortfolio, setSelectedPortfolio] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [newPortfolioName, setNewPortfolioName] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [editingPortfolioId, setEditingPortfolioId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')

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

  // Fetch portfolio details when one is selected
  const { data: selectedPortfolioData } = useQuery({
    queryKey: ['portfolio', selectedPortfolio],
    queryFn: async () => {
      if (!selectedPortfolio) return null
      const response = await getPortfolio(selectedPortfolio)
      return response.data
    },
    enabled: !!selectedPortfolio,
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

  const updateMutation = useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) => {
      await updatePortfolio(id, { name })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio', selectedPortfolio] })
      setEditingPortfolioId(null)
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

  const removeStockMutation = useMutation({
    mutationFn: async ({ portfolioId, ticker }: { portfolioId: string; ticker: string }) => {
      await removeStockFromPortfolio(portfolioId, ticker)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio', selectedPortfolio] })
    },
  })

  const archiveStockMutation = useMutation({
    mutationFn: async ({ portfolioId, ticker }: { portfolioId: string; ticker: string }) => {
      await archiveStock(portfolioId, ticker)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio', selectedPortfolio] })
      queryClient.invalidateQueries({ queryKey: ['archivedStocks', selectedPortfolio] })
    },
  })

  const restoreStockMutation = useMutation({
    mutationFn: async ({ portfolioId, ticker }: { portfolioId: string; ticker: string }) => {
      await restoreStock(portfolioId, ticker)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio', selectedPortfolio] })
      queryClient.invalidateQueries({ queryKey: ['archivedStocks', selectedPortfolio] })
    },
  })

  const { data: archivedStocks } = useQuery({
    queryKey: ['archivedStocks', selectedPortfolio],
    queryFn: async () => {
      if (!selectedPortfolio) return []
      const response = await getArchivedStocks(selectedPortfolio)
      return response.data
    },
    enabled: !!selectedPortfolio && showArchived,
  })

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (newPortfolioName.trim()) {
      createMutation.mutate(newPortfolioName.trim())
    }
  }

  const handleStartEdit = (portfolioId: string, currentName: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setEditingPortfolioId(portfolioId)
    setEditName(currentName)
  }

  const handleSaveEdit = (portfolioId: string, e: React.FormEvent) => {
    e.preventDefault()
    if (editName.trim()) {
      updateMutation.mutate({ id: portfolioId, name: editName.trim() })
    }
  }

  const handleCancelEdit = () => {
    setEditingPortfolioId(null)
    setEditName('')
  }

  const handleDelete = (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    if (confirm('Are you sure you want to delete this portfolio?')) {
      deleteMutation.mutate(id)
    }
  }

  const handleRemoveStock = (portfolioId: string, ticker: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (confirm(`Are you sure you want to remove ${ticker} from this portfolio?`)) {
      removeStockMutation.mutate({ portfolioId, ticker })
    }
  }

  const handleArchiveStock = (portfolioId: string, ticker: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (confirm(`Archive ${ticker}? The stock will be hidden from your portfolio but all your research (theses, notes) will be saved. You can restore it anytime.`)) {
      archiveStockMutation.mutate({ portfolioId, ticker })
    }
  }

  const handleRestoreStock = (portfolioId: string, ticker: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    restoreStockMutation.mutate({ portfolioId, ticker })
  }

  const handleToggleArchived = () => {
    setShowArchived(!showArchived)
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
                {editingPortfolioId === portfolio.id ? (
                  // Edit mode
                  <form onSubmit={(e) => handleSaveEdit(portfolio.id, e)} className="flex-1 flex items-center gap-3">
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 px-3 py-2 bg-surface border border-border rounded-lg text-text-primary focus:outline-none focus:ring-2 focus:ring-accent"
                      autoFocus
                      placeholder="Portfolio name"
                    />
                    <button
                      type="submit"
                      disabled={updateMutation.isPending || !editName.trim()}
                      className="px-3 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50"
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={handleCancelEdit}
                      className="px-3 py-2 text-text-secondary hover:text-text-primary transition-colors"
                    >
                      Cancel
                    </button>
                  </form>
                ) : (
                  // View mode
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
                          {portfolio.stock_count} holdings
                        </p>
                      </div>
                    </div>
                  </button>
                )}
                <div className="flex items-center gap-2">
                  {!editingPortfolioId ? (
                    <>
                      <button
                        onClick={(e) => handleStartEdit(portfolio.id, portfolio.name, e)}
                        className="p-2 text-text-secondary hover:text-accent hover:bg-surface-elevated rounded-lg transition-colors"
                        title="Rename portfolio"
                      >
                        <Edit2 className="w-5 h-5" />
                      </button>
                      <button
                        onClick={(e) => handleDelete(portfolio.id, e)}
                        disabled={deleteMutation.isPending}
                        className="p-2 text-text-secondary hover:text-danger hover:bg-surface-elevated rounded-lg transition-colors disabled:opacity-50"
                        title="Delete portfolio"
                      >
                        <Trash2 className="w-5 h-5" />
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
            </div>

            {/* Portfolio Stocks */}
            {selectedPortfolio === portfolio.id && (
              <div className="px-6 pb-6">
                <div className="pt-4 border-t border-border">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-text-secondary">
                      Holdings
                    </h4>
                    {archivedStocks && archivedStocks.length > 0 && (
                      <button
                        onClick={handleToggleArchived}
                        className="text-xs text-accent hover:text-accent-hover flex items-center gap-1"
                      >
                        <Archive className="w-3 h-3" />
                        {showArchived ? 'Hide' : 'Show'} Archived ({archivedStocks.length})
                      </button>
                    )}
                  </div>

                  {/* Active Stocks */}
                  {selectedPortfolioData?.stocks && selectedPortfolioData.stocks.length > 0 ? (
                    <div className="space-y-2">
                      {selectedPortfolioData.stocks.map((stock) => (
                        <div
                          key={stock.id}
                          className="flex items-center justify-between p-3 bg-surface rounded-lg hover:bg-surface-elevated transition-colors"
                        >
                          <Link
                            to={`/stock/${stock.ticker}`}
                            className="flex-1"
                          >
                            <div>
                              <span className="font-medium text-text-primary">
                                {stock.ticker}
                              </span>
                              <span className="text-sm text-text-secondary ml-2">
                                {stock.company_name}
                              </span>
                            </div>
                          </Link>
                          <div className="flex items-center gap-2">
                            {stock.sector && (
                              <span className="text-xs text-text-muted bg-border px-2 py-1 rounded">
                                {stock.sector}
                              </span>
                            )}
                            <button
                              onClick={(e) => handleArchiveStock(selectedPortfolio, stock.ticker, e)}
                              disabled={archiveStockMutation.isPending}
                              className="p-2 text-text-secondary hover:text-accent hover:bg-surface-elevated rounded-lg transition-colors disabled:opacity-50"
                              title={`Archive ${stock.ticker}`}
                            >
                              <Archive className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleRemoveStock(selectedPortfolio, stock.ticker, e)}
                              disabled={removeStockMutation.isPending}
                              className="p-2 text-text-secondary hover:text-danger hover:bg-surface-elevated rounded-lg transition-colors disabled:opacity-50"
                              title={`Remove ${stock.ticker} from portfolio`}
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-text-secondary">
                      <p>No stocks in this portfolio yet</p>
                      <Link
                        to="/"
                        className="inline-block mt-4 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
                      >
                        Add Stocks
                      </Link>
                    </div>
                  )}

                  {/* Archived Stocks */}
                  {showArchived && archivedStocks && archivedStocks.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-border">
                      <h5 className="text-xs font-medium text-text-muted mb-3">
                        Archived
                      </h5>
                      <div className="space-y-2">
                        {archivedStocks.map((stock) => (
                          <div
                            key={stock.id}
                            className="flex items-center justify-between p-3 bg-surface/50 rounded-lg opacity-75"
                          >
                            <Link
                              to={`/stock/${stock.ticker}`}
                              className="flex-1"
                            >
                              <div>
                                <span className="font-medium text-text-primary">
                                  {stock.ticker}
                                </span>
                                <span className="text-sm text-text-secondary ml-2">
                                  {stock.company_name}
                                </span>
                              </div>
                            </Link>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={(e) => handleRestoreStock(selectedPortfolio, stock.ticker, e)}
                                disabled={restoreStockMutation.isPending}
                                className="p-2 text-text-secondary hover:text-accent hover:bg-surface-elevated rounded-lg transition-colors disabled:opacity-50"
                                title={`Restore ${stock.ticker}`}
                              >
                                <Undo2 className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

          </div>
        ))}
      </div>
    </div>
  )
}
