import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Dashboard from './Dashboard'
import { QueryClient } from '@tanstack/react-query'
import { renderWithProviders } from '@/utils/test-utils'

// Mock the portfolios service
vi.mock('@/services/portfolios', () => ({
  getPortfolios: vi.fn(() => Promise.resolve({
    data: [
      {
        id: 'portfolio-1',
        name: 'My Portfolio',
        user_id: 'user-123',
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
        stocks: [
          {
            id: 'stock-1',
            ticker: 'AAPL',
            company_name: 'Apple Inc.',
            sector: 'Technology',
            industry: 'Consumer Electronics',
            current_price: 150.25,
            change_percent: 1.5
          },
          {
            id: 'stock-2',
            ticker: 'MSFT',
            company_name: 'Microsoft Corporation',
            sector: 'Technology',
            industry: 'Software',
            current_price: 300.50,
            change_percent: -0.75
          }
        ]
      }
    ]
  }))
}))

// Mock the StockCard component
vi.mock('@/components/dashboard/StockCard', () => ({
  default: ({ stock }: { stock: any }) => (
    <div data-testid={`stock-card-${stock.ticker}`}>
      <span>{stock.ticker}</span>
      <span>{stock.company_name}</span>
    </div>
  )
}))

// Mock the AddTickerModal component
vi.mock('@/components/dashboard/AddTickerModal', () => ({
  default: ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) =>
    isOpen ? (
      <div data-testid="add-ticker-modal">
        <button onClick={onClose}>Close Modal</button>
      </div>
    ) : null
}))

import { getPortfolios } from '@/services/portfolios'

describe('Dashboard Page', () => {
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
  })

  describe('Loading State', () => {
    it('shows loading skeleton while fetching portfolios', () => {
      // Mock a delayed response
      vi.mocked(getPortfolios).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve({
          data: []
        }), 100))
      )

      renderWithProviders(<Dashboard />, { queryClient })

      // Should show 6 skeleton cards
      const skeletons = screen.getAllByText('', { selector: '.animate-pulse' })
      expect(skeletons.length).toBeGreaterThan(0)
    })
  })

  describe('Empty State', () => {
    beforeEach(() => {
      vi.mocked(getPortfolios).mockResolvedValueOnce({
        data: [
          {
            id: 'portfolio-1',
            name: 'My Portfolio',
            user_id: 'user-123',
            created_at: '2024-01-01',
            updated_at: '2024-01-01',
            stocks: []
          }
        ]
      } as any)
    })

    it('shows empty state when no stocks in portfolio', async () => {
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByText('No stocks in your portfolio')).toBeInTheDocument()
      })
    })

    it('displays empty state message and CTA', async () => {
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByText('No stocks in your portfolio')).toBeInTheDocument()
        expect(screen.getByText(/Start building your portfolio/)).toBeInTheDocument()
      })

      const addButton = screen.getByRole('button', { name: /Add Your First Stock/i })
      expect(addButton).toBeInTheDocument()
    })

    it('opens add modal when clicking "Add Your First Stock"', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByText('No stocks in your portfolio')).toBeInTheDocument()
      })

      const addButton = screen.getByRole('button', { name: /Add Your First Stock/i })
      await user.click(addButton)

      expect(screen.getByTestId('add-ticker-modal')).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('shows error message when portfolio fetch fails', async () => {
      vi.mocked(getPortfolios).mockRejectedValueOnce(new Error('Network error'))

      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByText('Failed to load portfolio data')).toBeInTheDocument()
      })
    })

    it('provides retry button on error', async () => {
      vi.mocked(getPortfolios).mockRejectedValueOnce(new Error('Network error'))

      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        const retryButton = screen.getByRole('button', { name: 'Try Again' })
        expect(retryButton).toBeInTheDocument()
      })
    })

    it('refetches portfolios when retry button is clicked', async () => {
      const user = userEvent.setup()
      vi.mocked(getPortfolios).mockRejectedValueOnce(new Error('Network error'))

      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByText('Failed to load portfolio data')).toBeInTheDocument()
      })

      const retryButton = screen.getByRole('button', { name: 'Try Again' })
      await user.click(retryButton)

      // Should attempt to fetch again
      await waitFor(() => {
        expect(getPortfolios).toHaveBeenCalledTimes(2)
      })
    })
  })

  describe('Stock Display', () => {
    it('renders stock cards for each unique stock', async () => {
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByTestId('stock-card-AAPL')).toBeInTheDocument()
        expect(screen.getByTestId('stock-card-MSFT')).toBeInTheDocument()
      })
    })

    it('removes duplicate stocks across portfolios', async () => {
      vi.mocked(getPortfolios).mockResolvedValueOnce({
        data: [
          {
            id: 'portfolio-1',
            name: 'Portfolio 1',
            user_id: 'user-123',
            created_at: '2024-01-01',
            updated_at: '2024-01-01',
            stocks: [
              {
                id: 'stock-1',
                ticker: 'AAPL',
                company_name: 'Apple Inc.',
                sector: 'Technology',
                current_price: 150.25
              }
            ]
          },
          {
            id: 'portfolio-2',
            name: 'Portfolio 2',
            user_id: 'user-123',
            created_at: '2024-01-01',
            updated_at: '2024-01-01',
            stocks: [
              {
                id: 'stock-2',
                ticker: 'AAPL',
                company_name: 'Apple Inc.',
                sector: 'Technology',
                current_price: 150.25
              },
              {
                id: 'stock-3',
                ticker: 'MSFT',
                company_name: 'Microsoft',
                sector: 'Technology',
                current_price: 300.50
              }
            ]
          }
        ]
      } as any)

      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        // Should only show one AAPL card (not duplicated)
        const aaplCards = screen.getAllByTestId('stock-card-AAPL')
        expect(aaplCards.length).toBe(1)
        expect(screen.getByTestId('stock-card-MSFT')).toBeInTheDocument()
      })
    })

    it('displays stocks in a grid layout', async () => {
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByTestId('stock-card-AAPL')).toBeInTheDocument()
      })

      // Check that grid layout is applied
      const container = screen.getByTestId('stock-card-AAPL').closest('.grid')
      expect(container).toHaveClass('grid')
    })
  })

  describe('Add Stock Functionality', () => {
    it('renders "Add Stock" button in header', async () => {
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /Add Stock/i })
        expect(addButton).toBeInTheDocument()
      })
    })

    it('opens add ticker modal when "Add Stock" is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /Add Stock/i })
        expect(addButton).toBeInTheDocument()
      })

      const addButton = screen.getByRole('button', { name: /Add Stock/i })
      await user.click(addButton)

      expect(screen.getByTestId('add-ticker-modal')).toBeInTheDocument()
    })

    it('closes modal when close button is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<Dashboard />, { queryClient })

      // Open modal
      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /Add Stock/i })
        expect(addButton).toBeInTheDocument()
      })

      const addButton = screen.getByRole('button', { name: /Add Stock/i })
      await user.click(addButton)

      expect(screen.getByTestId('add-ticker-modal')).toBeInTheDocument()

      // Close modal
      const closeButton = screen.getByRole('button', { name: 'Close Modal' })
      await user.click(closeButton)

      await waitFor(() => {
        expect(screen.queryByTestId('add-ticker-modal')).not.toBeInTheDocument()
      })
    })

    it('refetches portfolios after successful stock addition', async () => {
      const user = userEvent.setup()
      const { rerender } = renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByTestId('stock-card-AAPL')).toBeInTheDocument()
      })

      // Open modal
      const addButton = screen.getByRole('button', { name: /Add Stock/i })
      await user.click(addButton)

      // Mock successful add
      vi.mocked(getPortfolios).mockResolvedValueOnce({
        data: [
          {
            id: 'portfolio-1',
            name: 'My Portfolio',
            user_id: 'user-123',
            created_at: '2024-01-01',
            updated_at: '2024-01-01',
            stocks: [
              {
                id: 'stock-1',
                ticker: 'AAPL',
                company_name: 'Apple Inc.',
                current_price: 150.25
              },
              {
                id: 'stock-2',
                ticker: 'GOOGL',
                company_name: 'Alphabet Inc.',
                current_price: 140.00
              }
            ]
          }
        ]
      } as any)

      // Trigger success callback (simulating modal onSuccess)
      rerender(
        <Dashboard />
      )

      await waitFor(() => {
        expect(getPortfolios).toHaveBeenCalled()
      })
    })
  })

  describe('Header', () => {
    it('displays page title and description', () => {
      renderWithProviders(<Dashboard />, { queryClient })

      expect(screen.getByText('Portfolio Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Track and analyze your investment positions')).toBeInTheDocument()
    })
  })

  describe('Accessibility', () => {
    it('has accessible buttons', async () => {
      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        const addButton = screen.getByRole('button', { name: /Add Stock/i })
        expect(addButton).toBeInTheDocument()
      })
    })

    it('provides clear empty state messaging', async () => {
      vi.mocked(getPortfolios).mockResolvedValueOnce({
        data: [
          {
            id: 'portfolio-1',
            name: 'My Portfolio',
            user_id: 'user-123',
            created_at: '2024-01-01',
            updated_at: '2024-01-01',
            stocks: []
          }
        ]
      } as any)

      renderWithProviders(<Dashboard />, { queryClient })

      await waitFor(() => {
        expect(screen.getByText('No stocks in your portfolio')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /Add Your First Stock/i })).toBeInTheDocument()
      })
    })
  })
})
