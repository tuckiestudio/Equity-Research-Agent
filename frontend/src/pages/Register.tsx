import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { register } from '@/services/auth'
import { useAuthStore } from '@/stores/auth'
import { TrendingUp } from 'lucide-react'
import clsx from 'clsx'

interface FormData {
  full_name: string
  email: string
  password: string
  confirmPassword: string
}

interface FormErrors {
  full_name?: string
  email?: string
  password?: string
  confirmPassword?: string
  general?: string
}

export default function Register() {
  const navigate = useNavigate()
  const { login: setAuth } = useAuthStore()
  const [formData, setFormData] = useState<FormData>({
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})

  const registerMutation = useMutation({
    mutationFn: () =>
      register(formData.email, formData.password, formData.full_name),
    onSuccess: async (response) => {
      try {
        const { access_token } = response.data
        // Store token first so getMe interceptor works
        localStorage.setItem('auth_token', access_token)

        // Fetch user profile
        const { getMe } = await import('@/services/auth')
        const userResponse = await getMe()

        // Update store with real user data
        setAuth(access_token, userResponse.data)
        navigate('/')
      } catch (error) {
        // If profile fetch fails, redirect to login
        navigate('/login')
      }
    },
    onError: (error: any) => {
      setErrors({
        general:
          error.response?.data?.detail || 'Registration failed. Please try again.',
      })
    },
  })

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    if (!formData.full_name.trim()) {
      newErrors.full_name = 'Full name is required'
    } else if (formData.full_name.trim().length < 2) {
      newErrors.full_name = 'Name must be at least 2 characters'
    }

    if (!formData.email) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email address'
    }

    if (!formData.password) {
      newErrors.password = 'Password is required'
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters'
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = 'Please confirm your password'
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      registerMutation.mutate()
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
            Create Account
          </h1>
          <p className="text-text-secondary">
            Join Equity Research for AI-powered analysis
          </p>
        </div>

        {/* Register Form */}
        <div className="glass-card">
          {errors.general && (
            <div className="mb-6 p-4 bg-danger/10 border border-danger/30 rounded-lg">
              <p className="text-danger text-sm">{errors.general}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="full_name"
                className="block text-sm font-medium text-text-secondary mb-2"
              >
                Full Name
              </label>
              <input
                type="text"
                id="full_name"
                value={formData.full_name}
                onChange={(e) =>
                  setFormData({ ...formData, full_name: e.target.value })
                }
                className={clsx(
                  'w-full px-4 py-3 bg-surface rounded-lg border',
                  'text-text-primary placeholder-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                  'transition-all duration-200',
                  errors.full_name && 'border-danger focus:ring-danger'
                )}
                placeholder="John Doe"
              />
              {errors.full_name && (
                <p className="mt-1.5 text-sm text-danger">{errors.full_name}</p>
              )}
            </div>

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

            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-text-secondary mb-2"
              >
                Confirm Password
              </label>
              <input
                type="password"
                id="confirmPassword"
                value={formData.confirmPassword}
                onChange={(e) =>
                  setFormData({ ...formData, confirmPassword: e.target.value })
                }
                className={clsx(
                  'w-full px-4 py-3 bg-surface rounded-lg border',
                  'text-text-primary placeholder-text-muted',
                  'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
                  'transition-all duration-200',
                  errors.confirmPassword && 'border-danger focus:ring-danger'
                )}
                placeholder="••••••••"
              />
              {errors.confirmPassword && (
                <p className="mt-1.5 text-sm text-danger">
                  {errors.confirmPassword}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={registerMutation.isPending}
              className={clsx(
                'w-full py-3 px-4 rounded-lg font-semibold text-white',
                'bg-accent hover:bg-accent-hover',
                'focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-surface',
                'transition-all duration-200',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {registerMutation.isPending ? 'Creating account...' : 'Sign Up'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-text-secondary text-sm">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-accent hover:text-accent-hover font-medium transition-colors"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
