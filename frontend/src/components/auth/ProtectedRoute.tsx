import { useEffect } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMe } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'

export default function ProtectedRoute() {
  const { isAuthenticated, token, logout } = useAuthStore()
  const location = useLocation()

  // Validate token on mount
  const { isError, isLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: async () => {
      const response = await getMe()
      return response.data
    },
    enabled: !!token,
    retry: false,
  })

  useEffect(() => {
    if (isError) {
      logout()
    }
  }, [isError, logout])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
          <p className="text-text-secondary">Verifying authentication...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated || isError) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <Outlet />
}
