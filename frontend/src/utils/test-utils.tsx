/**
 * Test utilities for React component tests
 * Provides common mocks for React Query, React Router, and other dependencies
 */

import { render } from '@testing-library/react'
import type { ReactElement } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'

/**
 * Creates a test QueryClient with disabled retries and logging
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  })
}

/**
 * Wrapper component that provides all necessary context for tests
 */
interface AllTheProvidersProps {
  children: React.ReactNode
  queryClient?: QueryClient
}

export function AllTheProviders({
  children,
  queryClient = createTestQueryClient(),
}: AllTheProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  )
}

/**
 * Custom render function that includes all providers
 */
export function renderWithProviders(
  ui: ReactElement,
  { queryClient }: { queryClient?: QueryClient } = {}
) {
  return render(ui, {
    wrapper: ({ children }) => (
      <AllTheProviders queryClient={queryClient}>{children}</AllTheProviders>
    ),
  })
}
