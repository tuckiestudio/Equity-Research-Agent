import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPortfolios, getPortfolio } from '@/services/portfolios'
import { Plus } from 'lucide-react'
import StockCard from '@/components/dashboard/StockCard'
import AddTickerModal from '@/components/dashboard/AddTickerModal'

export default function Dashboard() {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)

  const {
    data: portfolios,
    isLoading: isLoadingPortfolios,
    error,
    refetch,
  } = useQuery({
    queryKey: ['portfolios'],
    queryFn: async () => {
      const response = await getPortfolios()
      return response.data
    },
  })

  // Fetch all portfolio details to get stocks
  const { data: portfolioDetails, isLoading: isLoadingDetails } = useQuery({
    queryKey: ['portfolios', 'details'],
    queryFn: async () => {
      if (!portfolios) return []
      const details = await Promise.all(
        portfolios.map(async (p) => {
          const response = await getPortfolio(p.id)
          return response.data
        })
      )
      return details
    },
    enabled: !!portfolios,
  })

  const isLoading = isLoadingPortfolios || isLoadingDetails

  // Get all stocks from all portfolios (memoized to prevent unnecessary recalculations)
  const allStocks = useMemo(() => {
    if (!Array.isArray(portfolioDetails)) return []
    return portfolioDetails.flatMap((p) => p.stocks ?? [])
  }, [portfolioDetails])

  // Remove duplicates by ticker (memoized)
  const uniqueStocks = useMemo(() => {
    return Array.from(
      new Map(allStocks.map((stock) => [stock.ticker, stock])).values()
    )
  }, [allStocks])

  const handleAddSuccess = () => {
    setIsAddModalOpen(false)
    refetch()
  }

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-bold text-text-primary mb-1">
            Portfolio Dashboard
          </h2>
          <p className="text-text-secondary">
            Track and analyze your investment positions
          </p>
        </div>
        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium transition-colors"
        >
          <Plus className="w-5 h-5" />
          Add Stock
        </button>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="h-40 bg-surface-card rounded-xl border border-border animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="glass-card">
          <div className="text-center py-12">
            <p className="text-danger mb-4">
              Failed to load portfolio data
            </p>
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && uniqueStocks.length === 0 && (
        <div className="glass-card">
          <div className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-surface-elevated flex items-center justify-center">
              <Plus className="w-10 h-10 text-text-muted" />
            </div>
            <h3 className="text-xl font-semibold text-text-primary mb-2">
              No stocks in your portfolio
            </h3>
            <p className="text-text-secondary mb-6 max-w-md mx-auto">
              Start building your portfolio by adding stocks to track. Get
              AI-powered insights and analysis for each position.
            </p>
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium transition-colors"
            >
              <Plus className="w-5 h-5" />
              Add Your First Stock
            </button>
          </div>
        </div>
      )}

      {/* Stock Grid */}
      {!isLoading && !error && uniqueStocks.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {uniqueStocks.map((stock) => (
            <StockCard key={stock.ticker} stock={stock} />
          ))}
        </div>
      )}

      {/* Add Stock Modal */}
      {isAddModalOpen && (
        <AddTickerModal
          isOpen={isAddModalOpen}
          onClose={() => setIsAddModalOpen(false)}
          onSuccess={handleAddSuccess}
        />
      )}
    </div>
  )
}
