import { useNavigate } from 'react-router-dom'
import type { Stock } from '@/services/types'
import clsx from 'clsx'

interface StockCardProps {
  stock: Stock
}

export default function StockCard({ stock }: StockCardProps) {
  const navigate = useNavigate()

  const isPositive = stock.change_percent !== undefined && stock.change_percent >= 0

  return (
    <button
      onClick={() => navigate(`/stock/${stock.ticker}`)}
      className="group text-left w-full"
      data-testid={`stock-card-${stock.ticker.toLowerCase()}`}
    >
      <div
        className={clsx(
          'glass-card h-40 transition-all duration-300',
          'hover:scale-[1.02] hover:shadow-lg hover:shadow-accent/10',
          'hover:border-accent/50'
        )}
      >
        {/* Ticker Badge */}
        <div className="flex items-start justify-between mb-4">
          <div className="px-3 py-1 bg-accent/20 text-accent rounded-lg font-bold text-lg">
            {stock.ticker.toUpperCase()}
          </div>
          {stock.change_percent !== undefined && (
            <div
              className={clsx(
                'flex items-center gap-1 text-sm font-medium px-2 py-1 rounded',
                isPositive
                  ? 'bg-success/10 text-success'
                  : 'bg-danger/10 text-danger'
              )}
            >
              <span>{isPositive ? '+' : ''}</span>
              <span>{stock.change_percent.toFixed(2)}%</span>
            </div>
          )}
        </div>

        {/* Company Info */}
        <div className="space-y-2">
          <h3 className="font-semibold text-text-primary truncate group-hover:text-accent transition-colors">
            {stock.company_name}
          </h3>
          {stock.sector && (
            <div className="flex items-center gap-2 text-sm text-text-secondary">
              <span className="truncate">{stock.sector}</span>
              {stock.industry && (
                <>
                  <span>•</span>
                  <span className="truncate">{stock.industry}</span>
                </>
              )}
            </div>
          )}
          {stock.current_price && (
            <div className="flex items-baseline gap-2 pt-2 border-t border-border/50">
              <span className="text-xl font-bold text-text-primary">
                ${stock.current_price.toFixed(2)}
              </span>
              {stock.market_cap && (
                <span className="text-sm text-text-secondary">
                  MCap: ${(stock.market_cap / 1e6).toFixed(1)}M
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </button>
  )
}
