import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StockCard from './StockCard'
import type { Stock } from '@/services/types'
import { setupRouterMocks, mockNavigate } from '@/utils/mocks'

// Setup router mocks
setupRouterMocks()

describe('StockCard Component', () => {
  const mockStock: Stock = {
    id: 'stock-1',
    ticker: 'AAPL',
    company_name: 'Apple Inc.',
    sector: 'Technology',
    industry: 'Consumer Electronics',
    market_cap: 2500000000000,
    current_price: 150.25,
    change_percent: 1.5
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Rendering', () => {
    it('renders stock ticker in uppercase', () => {
      render(<StockCard stock={mockStock} />)

      expect(screen.getByText('AAPL')).toBeInTheDocument()
    })

    it('renders company name', () => {
      render(<StockCard stock={mockStock} />)

      expect(screen.getByText('Apple Inc.')).toBeInTheDocument()
    })

    it('renders sector when available', () => {
      render(<StockCard stock={mockStock} />)

      expect(screen.getByText('Technology')).toBeInTheDocument()
    })

    it('renders industry when available', () => {
      render(<StockCard stock={mockStock} />)

      expect(screen.getByText('Consumer Electronics')).toBeInTheDocument()
    })

    it('does not render industry when not available', () => {
      const stockWithoutIndustry = { ...mockStock, industry: undefined }
      render(<StockCard stock={stockWithoutIndustry} />)

      expect(screen.queryByText('Consumer Electronics')).not.toBeInTheDocument()
    })

    it('renders current price when available', () => {
      render(<StockCard stock={mockStock} />)

      expect(screen.getByText('$150.25')).toBeInTheDocument()
    })

    it('renders market cap in millions when available', () => {
      render(<StockCard stock={mockStock} />)

      // 2.5 trillion should be shown as 2500000.0M
      expect(screen.getByText(/MCap:/)).toBeInTheDocument()
    })

    it('renders positive change percentage with + sign', () => {
      render(<StockCard stock={mockStock} />)

      expect(screen.getByText('+1.50%')).toBeInTheDocument()
    })

    it('renders negative change percentage without + sign', () => {
      const stockWithNegativeChange = { ...mockStock, change_percent: -0.75 }
      render(<StockCard stock={stockWithNegativeChange} />)

      expect(screen.getByText('-0.75%')).toBeInTheDocument()
    })

    it('does not render change percentage when not available', () => {
      const stockWithoutChange = { ...mockStock, change_percent: undefined }
      render(<StockCard stock={stockWithoutChange} />)

      expect(screen.queryByText(/\+1.50%/)).not.toBeInTheDocument()
      expect(screen.queryByText(/-0.75%/)).not.toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies positive styling for positive change', () => {
      const stockWithPositiveChange = { ...mockStock, change_percent: 1.5 }
      render(<StockCard stock={stockWithPositiveChange} />)

      const changeElement = screen.getByText('+1.50%').closest('div')
      expect(changeElement).toHaveClass('bg-success/10', 'text-success')
    })

    it('applies negative styling for negative change', () => {
      const stockWithNegativeChange = { ...mockStock, change_percent: -0.75 }
      render(<StockCard stock={stockWithNegativeChange} />)

      const changeElement = screen.getByText('-0.75%').closest('div')
      expect(changeElement).toHaveClass('bg-danger/10', 'text-danger')
    })

    it('applies hover effects to card', () => {
      const { container } = render(<StockCard stock={mockStock} />)

      const cardButton = container.querySelector('button.group')
      expect(cardButton).toHaveClass('group', 'text-left', 'w-full')
    })
  })

  describe('Navigation', () => {
    it('navigates to stock detail page on click', async () => {
      const user = userEvent.setup()
      render(<StockCard stock={mockStock} />)

      const cardButton = screen.getByText('AAPL').closest('button')
      await user.click(cardButton!)

      expect(mockNavigate).toHaveBeenCalledWith('/stock/AAPL')
    })

    it('navigates with correct ticker for different stocks', async () => {
      const user = userEvent.setup()
      const msftStock = { ...mockStock, ticker: 'MSFT', company_name: 'Microsoft' }
      render(<StockCard stock={msftStock} />)

      const cardButton = screen.getByText('MSFT').closest('button')
      await user.click(cardButton!)

      expect(mockNavigate).toHaveBeenCalledWith('/stock/MSFT')
    })
  })

  describe('Layout', () => {
    it('has correct card dimensions', () => {
      const { container } = render(<StockCard stock={mockStock} />)

      const card = container.querySelector('.glass-card')
      expect(card).toHaveClass('h-40')
    })

    it('displays ticker badge with accent color', () => {
      render(<StockCard stock={mockStock} />)

      const tickerBadge = screen.getByText('AAPL').closest('div')
      expect(tickerBadge).toHaveClass('bg-accent/20', 'text-accent', 'font-bold')
    })

    it('displays sector and industry in correct format', () => {
      render(<StockCard stock={mockStock} />)

      const sector = screen.getByText('Technology')
      const industry = screen.getByText('Consumer Electronics')

      // Both should be on the same line with bullet separator
      expect(sector).toBeInTheDocument()
      expect(industry).toBeInTheDocument()
    })

    it('shows price and market cap in bottom section with border', () => {
      const { container } = render(<StockCard stock={mockStock} />)

      const bottomSection = container.querySelector('.border-t')
      expect(bottomSection).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('handles stock with minimal data', () => {
      const minimalStock: Stock = {
        id: 'stock-2',
        ticker: 'XYZ',
        company_name: 'XYZ Corp'
      }

      render(<StockCard stock={minimalStock} />)

      expect(screen.getByText('XYZ')).toBeInTheDocument()
      expect(screen.getByText('XYZ Corp')).toBeInTheDocument()
      expect(screen.queryByText('Technology')).not.toBeInTheDocument()
      expect(screen.queryByText('$')).not.toBeInTheDocument()
    })

    it('handles very small market cap', () => {
      const smallCapStock = { ...mockStock, market_cap: 50000000, current_price: 5.25 }
      render(<StockCard stock={smallCapStock} />)

      expect(screen.getByText('$5.25')).toBeInTheDocument()
      expect(screen.getByText(/MCap:/)).toBeInTheDocument()
    })

    it('handles zero change percentage', () => {
      const zeroChangeStock = { ...mockStock, change_percent: 0 }
      render(<StockCard stock={zeroChangeStock} />)

      expect(screen.getByText('+0.00%')).toBeInTheDocument()
    })

    it('handles very large price', () => {
      const expensiveStock = { ...mockStock, current_price: 2500.75 }
      render(<StockCard stock={expensiveStock} />)

      expect(screen.getByText('$2500.75')).toBeInTheDocument()
    })

    it('handles long company name with truncation', () => {
      const longNameStock = {
        ...mockStock,
        company_name: 'Very Long Company Name That Should Be Truncated In The Display'
      }

      render(<StockCard stock={longNameStock} />)

      const companyName = screen.getByText(/Very Long Company Name/)
      expect(companyName).toHaveClass('truncate')
    })
  })

  describe('Accessibility', () => {
    it('is clickable via keyboard', async () => {
      const user = userEvent.setup()
      render(<StockCard stock={mockStock} />)

      const cardButton = screen.getByText('AAPL').closest('button')
      cardButton?.focus()

      await user.keyboard('{Enter}')

      expect(mockNavigate).toHaveBeenCalledWith('/stock/AAPL')
    })

    it('has accessible button text', () => {
      render(<StockCard stock={mockStock} />)

      const cardButton = screen.getByText('AAPL').closest('button')
      expect(cardButton?.tagName).toBe('BUTTON')
    })
  })
})
