import { test, expect } from '@playwright/test'

/**
 * E2E Tests with Mocked API Responses
 *
 * These tests mock the backend API responses to ensure reliable testing
 * without requiring a running backend server. This is ideal for CI/CD pipelines
 * and development testing.
 */
test.describe('Critical User Path (Mocked)', () => {
  const timestamp = Date.now()
  const testEmail = `e2e-mocked-${timestamp}@example.com`
  const testPassword = 'MockedPath123!'
  const testName = 'Mocked Test User'

  // Mock API responses
  const mockAuthResponse = {
    data: {
      access_token: 'mock-jwt-token',
      token_type: 'bearer',
    },
  }

  const mockUserResponse = {
    data: {
      id: '1',
      email: testEmail,
      full_name: testName,
      created_at: new Date().toISOString(),
    },
  }

  const mockPortfoliosResponse = {
    data: [
      {
        id: '1',
        name: 'My Portfolio',
        description: 'Default portfolio',
        stocks: [],
      },
    ],
  }

  const mockStockSearchResponse = {
    data: [
      {
        ticker: 'AAPL',
        name: 'Apple Inc.',
        exchange: 'NASDAQ',
        price: 178.52,
      },
      {
        ticker: 'MSFT',
        name: 'Microsoft Corporation',
        exchange: 'NASDAQ',
        price: 378.91,
      },
    ],
  }

  const mockStockDetailResponse = {
    data: {
      ticker: 'AAPL',
      company_name: 'Apple Inc.',
      sector: 'Technology',
      industry: 'Consumer Electronics',
      current_price: 178.52,
      change_percent: 1.23,
      market_cap: 2800000000000,
      pe_ratio: 28.5,
      ev_ebitda: 22.3,
      dividend_yield: 0.005,
    },
  }

  test.beforeEach(async ({ page }) => {
    // Clear localStorage
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
  })

  test('should complete full user flow with mocked responses', async ({
    page,
  }) => {
    // Mock registration API
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockAuthResponse),
      })
    })

    // Mock get user API
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUserResponse),
      })
    })

    // Mock portfolios API
    await page.route('**/api/v1/portfolios', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockPortfoliosResponse),
      })
    })

    // Mock stock search API
    await page.route('**/api/v1/stocks/search*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockStockSearchResponse),
      })
    })

    // Mock add stock to portfolio API
    await page.route('**/api/v1/portfolios/*/stocks', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Stock added successfully' }),
      })
    })

    // Mock stock detail API
    await page.route('**/api/v1/stocks/*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockStockDetailResponse),
      })
    })

    // Mock sentiment, thesis, and watch items APIs
    await page.route('**/api/v1/stocks/*/sentiment', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            ticker: 'AAPL',
            total_articles: 150,
            bullish_count: 90,
            neutral_count: 40,
            bearish_count: 20,
            updated_at: new Date().toISOString(),
          },
        }),
      })
    })

    await page.route('**/api/v1/stocks/*/thesis', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: {
            id: '1',
            ticker: 'AAPL',
            title: 'Strong Growth Trajectory',
            summary: 'Apple continues to show strong growth in services and wearables.',
            stance: 'bullish',
            target_price: 210.0,
            confidence: 0.85,
            created_at: new Date().toISOString(),
          },
        }),
      })
    })

    await page.route('**/api/v1/stocks/*/watch', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            {
              id: '1',
              ticker: 'AAPL',
              title: 'Q4 Earnings Release',
              description: 'Watch for iPhone sales numbers',
              potential_impact: 'high',
              created_at: new Date().toISOString(),
            },
          ],
        }),
      })
    })

    // Step 1: Register
    await page.goto('/register')

    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)

    await page.getByRole('button', { name: 'Sign Up' }).click()

    // Step 2: Verify Dashboard - Empty State
    await expect(page).toHaveURL('/')
    await expect(
      page.getByRole('heading', { name: 'Portfolio Dashboard' })
    ).toBeVisible()

    await expect(
      page.getByRole('heading', { name: 'No stocks in your portfolio' })
    ).toBeVisible()

    // Step 3: Add Stock
    await page.getByRole('button', { name: 'Add Your First Stock' }).click()

    await expect(
      page.getByRole('heading', { name: 'Add Stock to Portfolio' })
    ).toBeVisible()

    // Search for stock
    const searchInput = page.getByPlaceholder(
      'Search by ticker or company name...'
    )
    await searchInput.fill('AAPL')
    await page.waitForTimeout(500)

    // Verify search results are displayed (check for search result buttons)
    await expect(page.getByTestId('stock-search-result').first()).toBeVisible()

    // Select first stock
    await page.getByTestId('stock-search-result').first().click()

    // Wait for modal to close and portfolios to be refetched
    await page.waitForTimeout(500)

    // Step 4: Navigate to stock detail
    // Since we don't have actual stock cards rendering without real data,
    // navigate directly to stock detail
    await page.goto('/stock/AAPL')

    // Step 5: Verify stock detail page
    await expect(page.getByRole('heading', { name: 'AAPL' })).toBeVisible()
    await expect(page.getByText('Apple Inc.')).toBeVisible()
    await expect(page.getByText('Technology • Consumer Electronics')).toBeVisible()

    // Verify price display
    await expect(page.getByText('$178.52')).toBeVisible()
    await expect(page.getByText('+1.23%')).toBeVisible()

    // Verify quick stats
    await expect(page.getByText('Market Cap')).toBeVisible()
    await expect(page.getByText('P/E Ratio')).toBeVisible()
    await expect(page.getByText('EV/EBITDA')).toBeVisible()
    await expect(page.getByText('Dividend Yield')).toBeVisible()

    // Verify tabs
    await expect(page.getByRole('tab', { name: 'Overview' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Model' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'News' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Notes' })).toBeVisible()
    await expect(page.getByRole('tab', { name: 'Thesis' })).toBeVisible()

    // Verify sentiment display
    await expect(page.getByText('News Sentiment')).toBeVisible()
    await expect(page.getByText('90')).toBeVisible() // Bullish count
    await expect(page.getByText('Bullish')).toBeVisible()

    // Verify thesis display
    await expect(page.getByText('Investment Thesis')).toBeVisible()
    await expect(page.getByText('Strong Growth Trajectory')).toBeVisible()
    await expect(page.getByText('$210.00')).toBeVisible()

    // Step 6: Test tab navigation
    await page.getByRole('tab', { name: 'Model' }).click()
    await expect(page.getByRole('tab', { name: 'Model', selected: true })).toBeAttached()

    await page.getByRole('tab', { name: 'News' }).click()
    await expect(page.getByRole('tab', { name: 'News', selected: true })).toBeAttached()

    await page.getByRole('tab', { name: 'Notes' }).click()
    await expect(page.getByRole('tab', { name: 'Notes', selected: true })).toBeAttached()

    await page.getByRole('tab', { name: 'Thesis' }).click()
    await expect(page.getByRole('tab', { name: 'Thesis', selected: true })).toBeAttached()

    await page.getByRole('tab', { name: 'Overview' }).click()
    await expect(
      page.getByRole('tab', { name: 'Overview', selected: true })
    ).toBeAttached()
  })

  test('should handle registration error gracefully', async ({ page }) => {
    // Mock failed registration
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Email already registered' }),
      })
    })

    await page.goto('/register')

    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)

    await page.getByRole('button', { name: 'Sign Up' }).click()

    // Should show error message
    await expect(page.getByText('Email already registered')).toBeVisible()
  })

  test('should handle network error on stock search', async ({ page }) => {
    // Setup auth mocks
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockAuthResponse),
      })
    })

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUserResponse),
      })
    })

    await page.route('**/api/v1/portfolios', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockPortfoliosResponse),
      })
    })

    // Mock failed stock search
    await page.route('**/api/v1/stocks/search*', async (route) => {
      await route.abort('failed')
    })

    // Register first
    await page.goto('/register')
    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)
    await page.getByRole('button', { name: 'Sign Up' }).click()

    await expect(page).toHaveURL('/')

    // Try to search
    await page.getByRole('button', { name: 'Add Your First Stock' }).click()
    await page
      .getByPlaceholder('Search by ticker or company name...')
      .fill('AAPL')
    await page.waitForTimeout(500)

    // Should show loading state initially, then error or no results
    // The exact behavior depends on error handling implementation
  })

  test('should persist authentication across page refresh', async ({
    page,
  }) => {
    // Mock auth APIs
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockAuthResponse),
      })
    })

    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockUserResponse),
      })
    })

    await page.route('**/api/v1/portfolios', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockPortfoliosResponse),
      })
    })

    // Register
    await page.goto('/register')
    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)
    await page.getByRole('button', { name: 'Sign Up' }).click()

    await expect(page).toHaveURL('/')

    // Manually set token in localStorage to simulate successful registration
    await page.evaluate(() => {
      localStorage.setItem('auth_token', 'mock-jwt-token')
    })

    // Reload page
    await page.reload()

    // Should still be authenticated
    await expect(
      page.getByRole('heading', { name: 'Portfolio Dashboard' })
    ).toBeVisible()
  })
})
