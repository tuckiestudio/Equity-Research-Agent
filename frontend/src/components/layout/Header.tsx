import { useLocation } from 'react-router-dom'
import { Bell } from 'lucide-react'

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/portfolio': 'Portfolio',
  '/search': 'Search Stocks',
  '/market': 'Market Overview',
}

export default function Header() {
  const location = useLocation()
  const pageTitle = pageTitles[location.pathname] || 'Equity Research'

  // Get dynamic page title for stock detail pages
  const getDynamicTitle = () => {
    if (location.pathname.startsWith('/stock/')) {
      const ticker = location.pathname.split('/')[2]
      return ticker ? `${ticker.toUpperCase()} - Analysis` : 'Stock Analysis'
    }
    return pageTitle
  }

  return (
    <header className="h-16 bg-surface-card border-b border-border flex items-center justify-between px-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">
          {getDynamicTitle()}
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="relative p-2 text-text-secondary hover:text-text-primary hover:bg-surface-elevated rounded-lg transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-accent rounded-full"></span>
        </button>
      </div>
    </header>
  )
}
