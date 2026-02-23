import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Login from './Login'
import { renderWithProviders, createTestQueryClient } from '@/utils/test-utils'

// Mock the auth service
vi.mock('@/services/auth', () => ({
  login: vi.fn(() => Promise.resolve({
    data: {
      access_token: 'test-token',
      token_type: 'bearer'
    }
  })),
  getMe: vi.fn(() => Promise.resolve({
    data: {
      id: 'user-123',
      email: 'test@example.com',
      full_name: 'Test User'
    }
  }))
}))

// Mock useAuthStore
const mockLogin = vi.fn()
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    login: mockLogin,
    token: null,
    user: null,
    isAuthenticated: false
  }))
}))

import { login, getMe } from '@/services/auth'

describe('Login Page', () => {
  let queryClient: ReturnType<typeof createTestQueryClient>

  beforeEach(() => {
    queryClient = createTestQueryClient()
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('Rendering', () => {
    it('renders the login form', () => {
      renderWithProviders(<Login />, { queryClient })

      expect(screen.getByText('Welcome Back')).toBeInTheDocument()
      expect(screen.getByLabelText('Email')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument()
    })

    it('renders the logo and title', () => {
      renderWithProviders(<Login />, { queryClient })

      expect(screen.getByText('Welcome Back')).toBeInTheDocument()
      expect(screen.getByText('Sign in to your Equity Research account')).toBeInTheDocument()
    })

    it('renders the sign up link', () => {
      renderWithProviders(<Login />, { queryClient })

      const signUpLink = screen.getByRole('link', { name: /Sign up/i })
      expect(signUpLink).toBeInTheDocument()
      expect(signUpLink).toHaveAttribute('href', '/register')
    })

    it('shows placeholder text correctly', () => {
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')

      expect(emailInput).toHaveAttribute('placeholder', 'your@email.com')
      expect(passwordInput).toHaveAttribute('placeholder', '••••••••')
    })
  })

  describe('Form Validation', () => {
    it('shows error when email is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })
    })

    it('shows error when email is invalid', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      await user.type(emailInput, 'invalid-email')

      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Invalid email address')).toBeInTheDocument()
      })
    })

    it('shows error when password is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      await user.type(emailInput, 'test@example.com')

      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Password is required')).toBeInTheDocument()
      })
    })

    it('clears errors when user starts typing', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })

      const emailInput = screen.getByLabelText('Email')
      await user.type(emailInput, 't')

      await waitFor(() => {
        expect(screen.queryByText('Email is required')).not.toBeInTheDocument()
      })
    })

    it('does not submit with invalid email format', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'notanemail')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Invalid email address')).toBeInTheDocument()
        expect(login).not.toHaveBeenCalled()
      })
    })
  })

  describe('Form Submission', () => {
    it('calls login service with correct credentials', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(login).toHaveBeenCalledWith('test@example.com', 'password123')
      })
    })

    it('stores token and fetches user profile on success', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(localStorage.getItem('auth_token')).toBe('test-token')
        expect(getMe).toHaveBeenCalled()
      })
    })

    it('updates auth store on successful login', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith(
          'test-token',
          expect.objectContaining({
            id: 'user-123',
            email: 'test@example.com'
          })
        )
      })
    })

    it('shows loading state while submitting', async () => {
      const user = userEvent.setup()
      // Mock a delayed response
      vi.mocked(login).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve({
          data: { access_token: 'test-token', token_type: 'bearer' }
        } as any), 100))
      )

      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Signing in...' })).toBeInTheDocument()
      })

      // Button should be disabled
      expect(submitButton).toBeDisabled()
    })
  })

  describe('Error Handling', () => {
    it('shows general error message on login failure', async () => {
      const user = userEvent.setup()
      vi.mocked(login).mockRejectedValueOnce({
        response: { data: { detail: 'Invalid credentials' } }
      })

      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongpassword')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
      })
    })

    it('shows default error message when no detail provided', async () => {
      const user = userEvent.setup()
      vi.mocked(login).mockRejectedValueOnce({})

      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Login failed. Please try again.')).toBeInTheDocument()
      })
    })

    it('shows error when getMe fails after successful login', async () => {
      const user = userEvent.setup()
      vi.mocked(getMe).mockRejectedValueOnce(new Error('Failed to fetch user'))

      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Failed to load user profile. Please try again.')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels', () => {
      renderWithProviders(<Login />, { queryClient })

      expect(screen.getByLabelText('Email')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
    })

    it('submits form with Enter key', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')

      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123{Enter}')

      await waitFor(() => {
        expect(login).toHaveBeenCalled()
      })
    })

    it('applies error styles to invalid fields', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Login />, { queryClient })

      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })

      const emailInput = screen.getByLabelText('Email')
      expect(emailInput).toHaveClass('border-danger')
    })
  })
})
