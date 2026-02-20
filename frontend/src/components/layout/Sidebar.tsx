import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Briefcase,
  Search,
  LogOut,
  TrendingUp,
} from 'lucide-react'
import { useAuthStore } from '@/stores/auth'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { path: '/search', label: 'Search', icon: Search },
  { path: '/market', label: 'Market', icon: TrendingUp },
]

export default function Sidebar() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const isActive = (path: string) => location.pathname === path

  return (
    <aside className="w-[260px] bg-surface-card border-r border-border flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-border">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary">
              Equity Research
            </h1>
            <p className="text-xs text-text-secondary">AI-Powered Analysis</p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                ${
                  isActive(item.path)
                    ? 'bg-accent text-white shadow-lg shadow-accent/20'
                    : 'text-text-secondary hover:bg-surface-elevated hover:text-text-primary'
                }
              `}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* User Section */}
      <div className="p-4 border-t border-border">
        <div className="glass rounded-lg p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-accent-muted flex items-center justify-center text-white font-semibold">
              {user?.full_name?.charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary truncate">
                {user?.full_name || 'User'}
              </p>
              <p className="text-xs text-text-secondary truncate">
                {user?.email || ''}
              </p>
            </div>
            <button
              onClick={logout}
              className="p-2 text-text-secondary hover:text-danger hover:bg-surface-elevated rounded-lg transition-colors"
              aria-label="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </aside>
  )
}
