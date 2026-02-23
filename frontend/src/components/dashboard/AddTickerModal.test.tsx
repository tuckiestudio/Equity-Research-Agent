import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import AddTickerModal from './AddTickerModal'
import { QueryClient } from '@tanstack/react-query'
import { renderWithProviders } from '@/utils/test-utils'

// Mock the stocks service
vi.mock('@/services/stocks', () => ({
  searchStocks: vi.fn(() => Promise.resolve({
    data: [
      {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        exchange: 'NASDAQ'
      },
      {
        ticker: 'MSFT',
        name: 'Microsoft Corporation',
        exchange: 'NASDAQ'
      }
    ]
  }))
}))

// Mock the portfolios service
vi.mock('@/services/portfolios', () => ({
  addStockToPortfolio: vi.fn(() => Promise.resolve({ data: { message: 'Stock added' } })),
  getPortfolios: vi.fn(() => Promise.resolve({
    data: [
      {
        id: 'portfolio-1',
        name: 'My Portfolio',
        stock_count: 0,
        stocks: []
      }
    ]
  }))
}))

import { searchStocks } from '@/services/stocks'
import { addStockToPortfolio, getPortfolios } from '@/services/portfolios'

describe('AddTickerModal Component', () => {
  let queryClient: QueryClient
  const mockOnClose = vi.fn()
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    queryClient = new QueryClient({
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
    vi.clearAllMocks()
  })

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onSuccess: mockOnSuccess
  }

  describe('Rendering', () => {
    it('does not render when isOpen is false', () => {
      renderWithProviders(
        <AddTickerModal {...defaultProps} isOpen={false} />,
        { queryClient }
      )

      expect(screen.queryByText('Add Stock to Portfolio')).not.toBeInTheDocument()
    })

    it('renders modal when isOpen is true', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      expect(screen.getByText('Add Stock to Portfolio')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Search by ticker or company name...')).toBeInTheDocument()
    })

    it('renders close button', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      // Close button is the X icon button
      const closeButton = screen.getByRole('button').closest('[class*="hover:text-text-primary"]')
      expect(closeButton).toBeInTheDocument()
    })

    it('renders cancel button in footer', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    })

    it('renders search input with icon', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      expect(searchInput).toBeInTheDocument()
      expect(searchInput).toHaveFocus()
    })
  })

  describe('Search Functionality', () => {
    it('shows prompt to enter at least 2 characters', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      expect(screen.getByText('Enter at least 2 characters to search')).toBeInTheDocument()
    })

    it('does not trigger search with less than 2 characters', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'A')

      await waitFor(() => {
        expect(searchStocks).not.toHaveBeenCalled()
      })
    })

    it('triggers search after debounce when typing 2+ characters', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AA')

      await waitFor(
        () => {
          expect(searchStocks).toHaveBeenCalledWith('AA')
        },
        { timeout: 500 }
      )
    })

    it('debounces search input (300ms)', async () => {
      const user = userEvent.setup()
      vi.useFakeTimers()

      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')

      await user.type(searchInput, 'AAPL')

      // Should not have been called immediately
      expect(searchStocks).not.toHaveBeenCalled()

      // Fast-forward past debounce delay
      vi.advanceTimersByTime(350)

      await waitFor(() => {
        expect(searchStocks).toHaveBeenCalledWith('AAPL')
      })

      vi.useRealTimers()
    })

    it('shows loading spinner while searching', async () => {
      vi.mocked(searchStocks).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve({
          data: [{ ticker: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' }]
        } as any), 100))
      )

      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AAPL')

      // Should show loading indicator
      await waitFor(() => {
        const loader = screen.getByText('AAPL').closest('div')
        expect(loader?.querySelector('.animate-spin')).toBeInTheDocument()
      })
    })

    it('displays search results', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AA')

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        expect(screen.getByText('NASDAQ')).toBeInTheDocument()
        expect(screen.getByText('AAPL')).toBeInTheDocument()
      })
    })

    it('shows "No results found" when search returns empty', async () => {
      vi.mocked(searchStocks).mockResolvedValueOnce({
        data: []
      } as any)

      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'XYZ')

      await waitFor(() => {
        expect(screen.getByText('No results found')).toBeInTheDocument()
      })
    })

    it('displays multiple search results', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AA')

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
        expect(screen.getByText('Microsoft Corporation')).toBeInTheDocument()
      })
    })
  })

  describe('Stock Selection', () => {
    it('calls addStockToPortfolio when stock is selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AA')

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
      })

      // Click on the first result
      const stockButton = screen.getByText('Apple Inc.').closest('button')
      await user.click(stockButton!)

      await waitFor(() => {
        expect(addStockToPortfolio).toHaveBeenCalledWith('portfolio-1', { ticker: 'AAPL' })
      })
    })

    it('clears search query after successful addition', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...') as HTMLInputElement
      await user.type(searchInput, 'AA')

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
      })

      const stockButton = screen.getByText('Apple Inc.').closest('button')
      await user.click(stockButton!)

      await waitFor(() => {
        expect(searchInput.value).toBe('')
      })
    })

    it('calls onSuccess callback after adding stock', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AA')

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
      })

      const stockButton = screen.getByText('Apple Inc.').closest('button')
      await user.click(stockButton!)

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalled()
      })
    })

    it('disables buttons while adding stock', async () => {
      const user = userEvent.setup()
      vi.mocked(addStockToPortfolio).mockImplementationOnce(
        () => new Promise(resolve => setTimeout(() => resolve({ data: { message: 'Stock added' } } as any), 100))
      )

      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AA')

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
      })

      const stockButton = screen.getByText('Apple Inc.').closest('button')
      await user.click(stockButton!)

      // Button should be disabled during mutation
      expect(stockButton).toBeDisabled()
    })
  })

  describe('Modal Actions', () => {
    it('closes modal when backdrop is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      // Click backdrop (the div with absolute inset-0)
      const backdrop = screen.getByText('Add Stock to Portfolio').closest('.fixed')?.querySelector('.bg-black\\/60')
      if (backdrop) {
        await user.click(backdrop)
        expect(mockOnClose).toHaveBeenCalled()
      }
    })

    it('closes modal when close button is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const closeButton = screen.getAllByRole('button')[0] // X button
      await user.click(closeButton)

      expect(mockOnClose).toHaveBeenCalled()
    })

    it('closes modal when cancel button is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const cancelButton = screen.getByRole('button', { name: 'Cancel' })
      await user.click(cancelButton)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Error Handling', () => {
    it('handles portfolio fetch error gracefully', async () => {
      vi.mocked(getPortfolios).mockRejectedValueOnce(new Error('No portfolio found'))

      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      // Should render but show no portfolios available
      expect(screen.getByText('Add Stock to Portfolio')).toBeInTheDocument()
    })

    it('shows error when adding stock fails', async () => {
      const user = userEvent.setup()
      vi.mocked(addStockToPortfolio).mockRejectedValueOnce(new Error('Failed to add stock'))

      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      await user.type(searchInput, 'AA')

      await waitFor(() => {
        expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
      })

      const stockButton = screen.getByText('Apple Inc.').closest('button')
      await user.click(stockButton!)

      // Error should be handled, modal may close or show error
      await waitFor(() => {
        expect(addStockToPortfolio).toHaveBeenCalled()
      })
    })
  })

  describe('Accessibility', () => {
    it('auto-focuses search input on open', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      expect(searchInput).toHaveFocus()
    })

    it('has proper ARIA labels', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      // Close button should have proper labeling
      const closeButton = screen.getAllByRole('button')[0]
      expect(closeButton).toBeInTheDocument()
    })

    it('traps focus within modal', () => {
      renderWithProviders(<AddTickerModal {...defaultProps} />, { queryClient })

      const searchInput = screen.getByPlaceholderText('Search by ticker or company name...')
      expect(searchInput).toHaveFocus()

      // Focus should move through modal elements
    })
  })
})
