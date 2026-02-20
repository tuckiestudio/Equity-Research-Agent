import { test, expect } from '@playwright/test'

/**
 * Example E2E Test
 *
 * This is a simple example to demonstrate basic Playwright testing patterns.
 * You can use this as a reference when writing new tests.
 */

test.describe('Example Tests', () => {
  test.beforeEach(async ({ page }) => {
    // This runs before each test
    await page.goto('/')
  })

  test('basic navigation test', async ({ page }) => {
    // Navigate to a page
    await page.goto('/login')

    // Verify URL
    await expect(page).toHaveURL('/login')

    // Verify page content
    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()
  })

  test('interacting with form elements', async ({ page }) => {
    await page.goto('/register')

    // Fill in form fields
    await page.getByLabel('Full Name').fill('Test User')
    await page.getByLabel('Email').fill('test@example.com')

    // Use id selector for password fields (avoids ambiguity)
    await page.locator('#password').fill('password123')
    await page.locator('#confirmPassword').fill('password123')

    // Verify values were filled
    await expect(page.getByLabel('Full Name')).toHaveValue('Test User')
    await expect(page.getByLabel('Email')).toHaveValue('test@example.com')
  })

  test('clicking buttons and links', async ({ page }) => {
    await page.goto('/login')

    // Find and click a link
    await page.getByRole('link', { name: 'Sign up' }).click()

    // Verify navigation occurred
    await expect(page).toHaveURL('/register')
    await expect(page.getByRole('heading', { name: 'Create Account' })).toBeVisible()
  })

  test('waiting for elements', async ({ page }) => {
    await page.goto('/register')

    // Wait for a specific element to be visible
    await expect(page.getByLabel('Full Name')).toBeVisible()

    // Wait for URL to change
    await page.getByRole('link', { name: 'Sign in' }).click()
    await page.waitForURL('/login')

    // Verify we're on the login page
    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible()
  })

  test('using data-testid selectors', async ({ page }) => {
    // Use data-testid attributes for reliable element selection
    // These are added to components for testing purposes

    await page.goto('/register')

    // Example: if a button has data-testid="submit-button"
    // await page.getByTestId('submit-button').click()
  })

  test('handling multiple matching elements', async ({ page }) => {
    await page.goto('/register')

    // When multiple elements match, use .first(), .last(), or .nth()
    const passwordFields = page.locator('input[type="password"]')

    await expect(passwordFields).toHaveCount(2)

    // Fill first password field
    await passwordFields.first().fill('password123')

    // Fill second password field
    await passwordFields.last().fill('password123')

    // Or use nth()
    await passwordFields.nth(0).fill('password123')
    await passwordFields.nth(1).fill('password123')
  })
})

/**
 * Best Practices for Writing E2E Tests:
 *
 * 1. Use descriptive test names that explain what is being tested
 * 2. Use data-testid attributes for reliable element selection
 * 3. Use getByRole, getByLabel, getByText for accessibility-friendly selectors
 * 4. Use locators with id(#) or class(.) when needed, but prefer semantic selectors
 * 5. Use expect().toBeVisible() to verify elements are present
 * 6. Use waitForURL() to verify navigation completed
 * 7. Mock API responses for tests that shouldn't depend on backend
 * 8. Clean up state in beforeEach hooks (clear localStorage, etc.)
 * 9. Keep tests independent - each test should work in isolation
 * 10. Use page objects or helper functions for repeated actions
 */
