/**
 * Test Helpers and Utilities
 *
 * Common utilities and helper functions for E2E tests
 */

export const TEST_CREDENTIALS = {
  email: `test-${Date.now()}@example.com`,
  password: 'TestPassword123!',
  fullName: 'E2E Test User',
}

/**
 * Register a new user and return the page
 */
export async function registerUser(
  page: any,
  credentials = TEST_CREDENTIALS
) {
  await page.goto('/register')
  await page.getByLabel('Full Name').fill(credentials.fullName)
  await page.getByLabel('Email').fill(credentials.email)
  await page.locator('#password').fill(credentials.password)
  await page.locator('#confirmPassword').fill(credentials.password)
  await page.getByRole('button', { name: 'Sign Up' }).click()

  // Wait for navigation to dashboard
  await page.waitForURL('/', { timeout: 5000 })
}

/**
 * Login a user and return the page
 */
export async function loginUser(
  page: any,
  credentials = TEST_CREDENTIALS
) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(credentials.email)
  await page.locator('#password').fill(credentials.password)
  await page.getByRole('button', { name: 'Sign In' }).click()

  // Wait for navigation to dashboard
  await page.waitForURL('/', { timeout: 5000 })
}

/**
 * Add a stock to portfolio via the modal
 */
export async function addStock(page: any, ticker: string) {
  // Open add stock modal
  await page.getByRole('button', { name: /Add Stock/i }).click()

  // Wait for modal to appear
  await page.waitForSelector('text=Add Stock to Portfolio')

  // Search for stock
  await page
    .getByPlaceholder('Search by ticker or company name...')
    .fill(ticker)

  // Wait for search debounce
  await page.waitForTimeout(500)

  // Click first result (if available)
  const firstResult = page.locator('[data-testid="stock-search-result"]').first()

  const count = await firstResult.count()
  if (count > 0) {
    await firstResult.click()
  }

  // Wait for modal to close
  await page.waitForSelector('text=Add Stock to Portfolio', { state: 'hidden' })
}

/**
 * Navigate to stock detail page
 */
export async function goToStockDetail(page: any, ticker: string) {
  await page.goto(`/stock/${ticker}`)

  // Wait for stock detail to load
  await page.waitForSelector(`text=${ticker.toUpperCase()}`)
}

/**
 * Clear authentication state
 */
export async function clearAuth(page: any) {
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
}

/**
 * Mock authentication APIs
 */
export function mockAuthAPIs(page: any, userData: any) {
  page.route('**/api/v1/auth/register', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
        },
      }),
    })
  })

  page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          access_token: 'mock-jwt-token',
          token_type: 'bearer',
        },
      }),
    })
  })

  page.route('**/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: userData }),
    })
  })
}

/**
 * Mock portfolio APIs
 */
export function mockPortfolioAPIs(page: any, portfolios: any) {
  page.route('**/api/v1/portfolios', async (route) => {
    const method = route.request().method()

    if (method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ data: portfolios }),
      })
    } else if (method === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ data: portfolios[0] }),
      })
    }
  })

  page.route('**/api/v1/portfolios/*/stocks', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Stock added successfully' }),
    })
  })
}

/**
 * Mock stock APIs
 */
export function mockStockAPIs(page: any) {
  page.route('**/api/v1/stocks/search*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
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
          {
            ticker: 'GOOGL',
            name: 'Alphabet Inc.',
            exchange: 'NASDAQ',
            price: 141.8,
          },
        ],
      }),
    })
  })

  page.route('**/api/v1/stocks/*', async (route) => {
    const url = route.request().url()
    const ticker = url.split('/').pop()?.toUpperCase()

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          ticker: ticker || 'AAPL',
          company_name: `${ticker || 'Apple'} Inc.`,
          sector: 'Technology',
          industry: 'Consumer Electronics',
          current_price: 178.52,
          change_percent: 1.23,
          market_cap: 2800000000000,
          pe_ratio: 28.5,
          ev_ebitda: 22.3,
          dividend_yield: 0.005,
        },
      }),
    })
  })

  // Mock sentiment, thesis, and watch items
  page.route('**/api/v1/stocks/*/sentiment', async (route) => {
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

  page.route('**/api/v1/stocks/*/thesis', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: {
          id: '1',
          ticker: 'AAPL',
          title: 'Strong Growth Trajectory',
          summary: 'Continued innovation in product lineup',
          stance: 'bullish',
          target_price: 210.0,
          confidence: 0.85,
          created_at: new Date().toISOString(),
        },
      }),
    })
  })

  page.route('**/api/v1/stocks/*/watch', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        data: [
          {
            id: '1',
            ticker: 'AAPL',
            title: 'Q4 Earnings Release',
            description: 'Key metrics to watch',
            potential_impact: 'high',
            created_at: new Date().toISOString(),
          },
        ],
      }),
    })
  })
}

/**
 * Wait for loading state to complete
 */
export async function waitForLoading(page: any) {
  await page.waitForSelector('[data-testid="loading"]', { state: 'hidden', timeout: 5000 })
}

/**
 * Take screenshot on failure
 */
export async function screenshotOnFailure(page: any, testName: string) {
  const screenshotPath = `test-screenshots/${testName}-failed.png`
  await page.screenshot({ path: screenshotPath, fullPage: true })
}

/**
 * Generate unique test credentials
 */
export function generateTestCredentials(prefix = 'test') {
  const timestamp = Date.now()
  return {
    email: `${prefix}-${timestamp}@example.com`,
    password: 'TestPassword123!',
    fullName: `${prefix} User ${timestamp}`,
  }
}
