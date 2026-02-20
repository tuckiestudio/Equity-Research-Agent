import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Register from './Register'
import { renderWithProviders, createTestQueryClient } from '@/utils/test-utils'

// Mock the auth service
vi.mock('@/services/auth', () => ({
  register: vi.fn(() => Promise.resolve({
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

const mockLogin = vi.fn()
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    login: mockLogin,
    token: null,
    user: null,
    isAuthenticated: false
  }))
}))

import { register, getMe } from '@/services/auth'

describe('Register Page', () => {
  let queryClient: ReturnType<typeof createTestQueryClient>

  beforeEach(() => {
    queryClient = createTestQueryClient()
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('Rendering', () => {
    it('renders the registration form', () => {
      renderWithProviders(<Register />, { queryClient })

      expect(screen.getByText('Create Account')).toBeInTheDocument()
      expect(screen.getByLabelText('Full Name')).toBeInTheDocument()
      expect(screen.getByLabelText('Email')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sign Up' })).toBeInTheDocument()
    })

    it('renders the logo and title', () => {
      renderWithProviders(<Register />, { queryClient })

      expect(screen.getByText('Create Account')).toBeInTheDocument()
      expect(screen.getByText('Join Equity Research for AI-powered analysis')).toBeInTheDocument()
    })

    it('renders the sign in link', () => {
      renderWithProviders(<Register />, { queryClient })

      const signInLink = screen.getByRole('link', { name: /Sign in/i })
      expect(signInLink).toBeInTheDocument()
      expect(signInLink).toHaveAttribute('href', '/login')
    })
  })

  describe('Form Validation', () => {
    it('shows error when full name is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Full name is required')).toBeInTheDocument()
      })
    })

    it('shows error when full name is too short', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      await user.type(nameInput, 'A')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Name must be at least 2 characters')).toBeInTheDocument()
      })
    })

    it('shows error when email is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      await user.type(nameInput, 'John Doe')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })
    })

    it('shows error when email is invalid', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'invalid-email')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Invalid email address')).toBeInTheDocument()
      })
    })

    it('shows error when password is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Password is required')).toBeInTheDocument()
      })
    })

    it('shows error when password is too short', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'pass')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Password must be at least 8 characters')).toBeInTheDocument()
      })
    })

    it('shows error when confirm password is empty', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Please confirm your password')).toBeInTheDocument()
      })
    })

    it('shows error when passwords do not match', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'different123')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
      })
    })

    it('trims whitespace from name validation', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      await user.type(nameInput, '   ')

      const submitButton = screen.getByRole('button', { name: 'Sign Up' })
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Full name is required')).toBeInTheDocument()
      })
    })
  })

  describe('Form Submission', () => {
    it('calls register service with correct credentials', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')
      const submitButton = screen.getByRole('button', { name: 'Sign Up' })

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(register).toHaveBeenCalledWith('test@example.com', 'password123', 'John Doe')
      })
    })

    it('stores token and fetches user profile on success', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')
      const submitButton = screen.getByRole('button', { name: 'Sign Up' })

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(localStorage.getItem('auth_token')).toBe('test-token')
        expect(getMe).toHaveBeenCalled()
      })
    })

    it('updates auth store on successful registration', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')
      const submitButton = screen.getByRole('button', { name: 'Sign Up' })

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith(
          'test-token',
          expect.objectContaining({
            id: 'user-123',
            email: 'test@example.com',
            full_name: 'Test User'
          })
        )
      })
    })

    it('shows loading state while submitting', async () => {
      const user = userEvent.setup()
      vi.mocked(register).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve({
          data: { access_token: 'test-token', token_type: 'bearer' }
        }), 100))
      )

      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')
      const submitButton = screen.getByRole('button', { name: 'Sign Up' })

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Creating account...' })).toBeInTheDocument()
      })

      expect(submitButton).toBeDisabled()
    })
  })

  describe('Error Handling', () => {
    it('shows general error message on registration failure', async () => {
      const user = userEvent.setup()
      vi.mocked(register).mockRejectedValueOnce({
        response: { data: { detail: 'Email already exists' } }
      })

      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')
      const submitButton = screen.getByRole('button', { name: 'Sign Up' })

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'existing@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Email already exists')).toBeInTheDocument()
      })
    })

    it('shows default error message when no detail provided', async () => {
      const user = userEvent.setup()
      vi.mocked(register).mockRejectedValueOnce({})

      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')
      const submitButton = screen.getByRole('button', { name: 'Sign Up' })

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText('Registration failed. Please try again.')).toBeInTheDocument()
      })
    })

    it('redirects to login when getMe fails after successful registration', async () => {
      const user = userEvent.setup()
      vi.mocked(getMe).mockRejectedValueOnce(new Error('Failed to fetch user'))

      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')
      const submitButton = screen.getByRole('button', { name: 'Sign Up' })

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123')
      await user.click(submitButton)

      await waitFor(() => {
        expect(getMe).toHaveBeenCalled()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels', () => {
      renderWithProviders(<Register />, { queryClient })

      expect(screen.getByLabelText('Full Name')).toBeInTheDocument()
      expect(screen.getByLabelText('Email')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument()
    })

    it('submits form with Enter key', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Register />, { queryClient })

      const nameInput = screen.getByLabelText('Full Name')
      const emailInput = screen.getByLabelText('Email')
      const passwordInput = screen.getByLabelText('Password')
      const confirmInput = screen.getByLabelText('Confirm Password')

      await user.type(nameInput, 'John Doe')
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'password123')
      await user.type(confirmInput, 'password123{Enter}')

      await waitFor(() => {
        expect(register).toHaveBeenCalled()
      })
    })
  })
})
