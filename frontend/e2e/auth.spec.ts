import { test, expect } from '@playwright/test'

/**
 * E2E Tests for Authentication Flow
 *
 * Tests the critical path: Register → Login → Dashboard
 */
test.describe('Authentication Flow', () => {
  // Generate unique email for each test run to avoid conflicts
  const timestamp = Date.now()
  const testEmail = `e2e-test-${timestamp}@example.com`
  const testPassword = 'TestPassword123!'
  const testName = 'E2E Test User'

  test.beforeEach(async ({ page }) => {
    // Clear localStorage before each test
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())
  })

  test('should display login page when not authenticated', async ({ page }) => {
    await page.goto('/login')

    // Verify page title and heading
    await expect(page).toHaveTitle(/Equity Research Agent/)
    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()

    // Verify login form elements
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()

    // Verify link to registration
    await expect(page.getByRole('link', { name: 'Sign up' })).toBeVisible()
  })

  test('should display registration page', async ({ page }) => {
    await page.goto('/register')

    // Verify page title and heading
    await expect(page).toHaveTitle(/Equity Research Agent/)
    await expect(
      page.getByRole('heading', { name: 'Create Account' })
    ).toBeVisible()

    // Verify registration form elements - use id selectors to avoid ambiguity
    await expect(page.getByLabel('Full Name')).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.locator('#password')).toBeVisible()
    await expect(page.locator('#confirmPassword')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign Up' })).toBeVisible()

    // Verify link to login
    await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()
  })

  test('should show validation errors on invalid registration', async ({ page }) => {
    await page.goto('/register')

    // Try to submit with empty form
    await page.getByRole('button', { name: 'Sign Up' }).click()

    // Check for validation errors
    await expect(page.getByText('Full name is required')).toBeVisible()
    await expect(page.getByText('Email is required')).toBeVisible()
    await expect(page.getByText('Password is required')).toBeVisible()
    await expect(page.getByText('Please confirm your password')).toBeVisible()
  })

  test('should show error for mismatched passwords', async ({ page }) => {
    await page.goto('/register')

    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill('DifferentPassword123!')

    await page.getByRole('button', { name: 'Sign Up' }).click()

    await expect(page.getByText('Passwords do not match')).toBeVisible()
  })

  test('should show error for invalid email format', async ({ page }) => {
    await page.goto('/register')

    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill('invalid-email')
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)

    await page.getByRole('button', { name: 'Sign Up' }).click()

    await expect(page.getByText('Invalid email address')).toBeVisible()
  })

  test('should show error for short password', async ({ page }) => {
    await page.goto('/register')

    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill('short')
    await page.locator('#confirmPassword').fill('short')

    await page.getByRole('button', { name: 'Sign Up' }).click()

    await expect(
      page.getByText('Password must be at least 8 characters')
    ).toBeVisible()
  })

  test('should successfully register and redirect to dashboard', async ({
    page,
  }) => {
    await page.goto('/register')

    // Fill out registration form
    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)

    // Submit form
    await page.getByRole('button', { name: 'Sign Up' }).click()

    // Should redirect to dashboard
    await expect(page).toHaveURL('/')
    await expect(
      page.getByRole('heading', { name: 'Portfolio Dashboard' })
    ).toBeVisible()
  })

  test('should successfully login and redirect to dashboard', async ({
    page,
  }) => {
    // First register a user
    await page.goto('/register')
    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)
    await page.getByRole('button', { name: 'Sign Up' }).click()

    // Wait for redirect
    await expect(page).toHaveURL('/')

    // Now logout by clearing auth
    await page.evaluate(() => localStorage.clear())

    // Go to login page
    await page.goto('/login')

    // Fill out login form
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)

    // Submit form
    await page.getByRole('button', { name: 'Sign In' }).click()

    // Should redirect to dashboard
    await expect(page).toHaveURL('/')
    await expect(
      page.getByRole('heading', { name: 'Portfolio Dashboard' })
    ).toBeVisible()
  })

  test('should show error on login with invalid credentials', async ({
    page,
  }) => {
    await page.goto('/login')

    await page.getByLabel('Email').fill('nonexistent@example.com')
    await page.locator('#password').fill('WrongPassword123!')

    await page.getByRole('button', { name: 'Sign In' }).click()

    // Should show error message
    await expect(
      page.getByText(/Login failed|Incorrect email or password/)
    ).toBeVisible()
  })

  test('should persist authentication across page reloads', async ({
    page,
  }) => {
    // Register and login
    await page.goto('/register')
    await page.getByLabel('Full Name').fill(testName)
    await page.getByLabel('Email').fill(testEmail)
    await page.locator('#password').fill(testPassword)
    await page.locator('#confirmPassword').fill(testPassword)
    await page.getByRole('button', { name: 'Sign Up' }).click()

    // Wait for redirect to dashboard
    await expect(page).toHaveURL('/')

    // Reload the page
    await page.reload()

    // Should still be on dashboard (authenticated)
    await expect(
      page.getByRole('heading', { name: 'Portfolio Dashboard' })
    ).toBeVisible()
  })

  test('should redirect to login when accessing protected routes without auth', async ({
    page,
  }) => {
    // Clear any existing auth
    await page.goto('/')
    await page.evaluate(() => localStorage.clear())

    // Try to access dashboard directly
    await page.goto('/')

    // Should redirect to login or show login page
    await expect(page).toHaveURL(/\/login/)
  })
})
