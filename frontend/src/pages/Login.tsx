import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { login } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'
import { TrendingUp } from 'lucide-react'
import clsx from 'clsx'

interface FormData {
  email: string
  password: string
}

interface FormErrors {
  email?: string
  password?: string
  general?: string
}

export default function Login() {
  const navigate = useNavigate()
  const { login: setAuth } = useAuthStore()
  const [formData, setFormData] = useState<FormData>({
    email: '',
    password: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})

  const loginMutation = useMutation({
    mutationFn: () => login(formData.email, formData.password),
    onSuccess: async (response) => {
      try {
        const { access_token } = response.data

        // Set token in store first so API interceptor can use it
        setAuth(access_token, { id: '', email: formData.email, full_name: '', tier: 'free' })

        // Fetch user profile with authenticated request
        const { getMe } = await import('@/services/auth')
        const userResponse = await getMe()

        // Update store with real user data
        setAuth(access_token, userResponse.data)
        navigate('/')
      } catch (error) {
        setErrors({
          general: 'Failed to load user profile. Please try again.'
        })
      }
    },
    onError: (error: any) => {
      setErrors({
        general: error.response?.data?.detail || 'Login failed. Please try again.',
      })
    },
  })

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    if (!formData.email) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email address'
    }

    if (!formData.password) {
      newErrors.password = 'Password is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      loginMutation.mutate()
    }
  }

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent mb-4">
            <TrendingUp className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-text-primary mb-2">
            Welcome Back
          </h1>
          <p className="text-text-secondary">
            Sign in to your Equity Research account
          </p>
        </div>

        {/* Login Form */}
        <div className="glass-card">
          {errors.general && (
            <div className="mb-6 p-4 bg-danger/10 border border-danger/30 rounded-lg">
              <p className="text-danger text-sm">{errors.general}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-text-secondary mb-2"
              >
                Email
              </label>
              <input
                type="email"
                id="email"
                value={formData.email}
                onChange={(e) =>
                  setFormData({ ...formData, email: e.target.value })
                }
                className={clsx(
                  'w-full px-4 py-3 bg-surface rounded-lg border',
                  'text-text-primary placeholder-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                  'transition-all duration-200',
                  errors.email && 'border-danger focus:ring-danger'
                )}
                placeholder="your@email.com"
              />
              {errors.email && (
                <p className="mt-1.5 text-sm text-danger">{errors.email}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-text-secondary mb-2"
              >
                Password
              </label>
              <input
                type="password"
                id="password"
                value={formData.password}
                onChange={(e) =>
                  setFormData({ ...formData, password: e.target.value })
                }
                className={clsx(
                  'w-full px-4 py-3 bg-surface rounded-lg border',
                  'text-text-primary placeholder-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                  'transition-all duration-200',
                  errors.password && 'border-danger focus:ring-danger'
                )}
                placeholder="••••••••"
              />
              {errors.password && (
                <p className="mt-1.5 text-sm text-danger">{errors.password}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loginMutation.isPending}
              className={clsx(
                'w-full py-3 px-4 rounded-lg font-semibold text-white',
                'bg-accent hover:bg-accent-hover',
                'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface',
                'transition-all duration-200',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {loginMutation.isPending ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-text-secondary text-sm">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="text-accent hover:text-accent-hover font-medium transition-colors"
              >
                Sign up
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
