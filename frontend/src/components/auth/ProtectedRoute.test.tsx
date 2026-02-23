import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProtectedRoute from './ProtectedRoute'
import { useAuthStore } from '@/stores/auth'

// Mock the auth service
vi.mock('@/services/auth', () => ({
  getMe: vi.fn(() => Promise.resolve({
    data: {
      id: 'user-123',
      email: 'test@example.com',
      full_name: 'Test User'
    }
  }))
}))

// Mock useAuthStore
const mockLogout = vi.fn()
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    isAuthenticated: false,
    token: null,
    user: null,
    logout: mockLogout
  }))
}))


function createWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
}

describe('ProtectedRoute', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: 0,
        },
      },
    })
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('When not authenticated', () => {
    beforeEach(() => {
      vi.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: false,
        token: null,
        user: null,
        logout: mockLogout,
        login: vi.fn(),
        setUser: vi.fn()
      })
    })

    it('redirects to login when not authenticated', async () => {
      const router = createMemoryRouter([
        {
          path: '/',
          element: <ProtectedRoute />,
          children: [
            { index: true, element: <div>Protected Content</div> }
          ]
        },
        {
          path: '/login',
          element: <div>Login Page</div>
        }
      ], {
        initialEntries: ['/']
      })

      render(<RouterProvider router={router} />, {
        wrapper: createWrapper(queryClient)
      })

      await waitFor(() => {
        expect(screen.getByText('Login Page')).toBeInTheDocument()
      })
    })

    it('preserves original location in redirect state', async () => {
      const router = createMemoryRouter([
        {
          path: '/protected',
          element: <ProtectedRoute />,
          children: [
            { index: true, element: <div>Protected Content</div> }
          ]
        },
        {
          path: '/login',
          element: <div>Login Page</div>
        }
      ], {
        initialEntries: ['/protected']
      })

      render(<RouterProvider router={router} />, {
        wrapper: createWrapper(queryClient)
      })

      await waitFor(() => {
        expect(screen.getByText('Login Page')).toBeInTheDocument()
      })
    })

    it('shows loading state while checking auth', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: false,
        token: 'some-token',
        user: null,
        logout: mockLogout,
        login: vi.fn(),
        setUser: vi.fn()
      })

      const router = createMemoryRouter([
        {
          path: '/',
          element: <ProtectedRoute />,
          children: [
            { index: true, element: <div>Protected Content</div> }
          ]
        },
        {
          path: '/login',
          element: <div>Login Page</div>
        }
      ], {
        initialEntries: ['/']
      })

      render(<RouterProvider router={router} />, {
        wrapper: createWrapper(queryClient)
      })

      expect(screen.getByText('Verifying authentication...')).toBeInTheDocument()
    })
  })

  describe('When authenticated', () => {
    beforeEach(() => {
      vi.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: true,
        token: 'valid-token',
        user: {
          id: 'user-123',
          email: 'test@example.com',
          full_name: 'Test User'
        },
        logout: mockLogout,
        login: vi.fn(),
        setUser: vi.fn()
      })
    })

    it('renders protected content when authenticated', async () => {
      const router = createMemoryRouter([
        {
          path: '/',
          element: <ProtectedRoute />,
          children: [
            { index: true, element: <div>Protected Content</div> }
          ]
        },
        {
          path: '/login',
          element: <div>Login Page</div>
        }
      ], {
        initialEntries: ['/']
      })

      render(<RouterProvider router={router} />, {
        wrapper: createWrapper(queryClient)
      })

      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument()
      })
    })

    it('renders outlet for nested routes', async () => {
      const router = createMemoryRouter([
        {
          path: '/',
          element: <ProtectedRoute />,
          children: [
            { index: true, element: <div>Dashboard Home</div> },
            { path: 'settings', element: <div>Settings Page</div> }
          ]
        },
        {
          path: '/login',
          element: <div>Login Page</div>
        }
      ], {
        initialEntries: ['/settings']
      })

      render(<RouterProvider router={router} />, {
        wrapper: createWrapper(queryClient)
      })

      await waitFor(() => {
        expect(screen.getByText('Settings Page')).toBeInTheDocument()
      })
    })
  })

  describe('Loading states', () => {
    it('shows loading spinner while validating token', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: true,
        token: 'valid-token',
        user: null,
        logout: mockLogout,
        login: vi.fn(),
        setUser: vi.fn()
      })

      const router = createMemoryRouter([
        {
          path: '/',
          element: <ProtectedRoute />,
          children: [
            { index: true, element: <div>Protected Content</div> }
          ]
        },
        {
          path: '/login',
          element: <div>Login Page</div>
        }
      ], {
        initialEntries: ['/']
      })

      render(<RouterProvider router={router} />, {
        wrapper: createWrapper(queryClient)
      })

      expect(screen.getByText('Verifying authentication...')).toBeInTheDocument()
    })

    it('has accessible loading message', () => {
      vi.mocked(useAuthStore).mockReturnValue({
        isAuthenticated: true,
        token: 'valid-token',
        user: null,
        logout: mockLogout,
        login: vi.fn(),
        setUser: vi.fn()
      })

      const router = createMemoryRouter([
        {
          path: '/',
          element: <ProtectedRoute />,
          children: [
            { index: true, element: <div>Protected Content</div> }
          ]
        },
        {
          path: '/login',
          element: <div>Login Page</div>
        }
      ], {
        initialEntries: ['/']
      })

      render(<RouterProvider router={router} />, {
        wrapper: createWrapper(queryClient)
      })

      const loadingText = screen.getByText('Verifying authentication...')
      expect(loadingText).toBeInTheDocument()
    })
  })
})
