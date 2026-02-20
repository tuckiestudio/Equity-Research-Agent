# E2E Tests for Equity Research Agent

This directory contains end-to-end browser tests using Playwright for the Equity Research Agent application.

## Overview

The E2E tests cover the critical user paths:

- **Authentication Flow**: Registration, login, validation, and session persistence
- **Critical User Path**: Register → Dashboard → Add Stock → View Detail
- **API Mocking**: Tests with mocked responses for reliable CI/CD execution

## Prerequisites

- Node.js and npm installed
- Dependencies installed: `npm install`
- Playwright browsers installed: `npm run test:e2e:install`

## Running Tests

```bash
# Run all E2E tests (headless)
npm run test:e2e

# Run tests with UI mode (interactive)
npm run test:e2e:ui

# Run tests in headed mode (visible browser)
npm run test:e2e:headed

# Debug tests with Playwright Inspector
npm run test:e2e:debug

# View HTML test report
npm run test:e2e:report

# Run all tests (unit + E2E)
npm run test:all
```

## Test Structure

```
e2e/
├── auth.spec.ts              # Authentication flow tests
├── critical-path.spec.ts      # Full user journey tests
├── mocked-critical-path.spec.ts # Tests with mocked API responses
└── helpers/
    └── test-helpers.ts        # Reusable test utilities
```

## Test Files

### `auth.spec.ts`

Tests the authentication system:

- Display of login and registration pages
- Form validation (email format, password length, matching passwords)
- Successful registration and login
- Error handling for invalid credentials
- Session persistence across page reloads
- Protected route redirection

### `critical-path.spec.ts`

Tests the complete user journey:

- Registration → Dashboard → Add Stock → View Detail
- Adding multiple stocks to portfolio
- Tab navigation on stock detail page
- Search functionality and error states
- Modal interactions (open, close, cancel)
- Navigation between dashboard and stock detail

**Note**: These tests require a running backend server or will skip tests when APIs return no data.

### `mocked-critical-path.spec.ts`

Tests with mocked API responses for reliable execution:

- Complete user flow without backend dependency
- Registration error handling
- Network error handling
- Authentication persistence

These tests are ideal for CI/CD pipelines as they don't require backend services.

## Configuration

Playwright is configured in `playwright.config.ts`:

- **Test Directory**: `./e2e`
- **Base URL**: `http://localhost:5173`
- **Browser**: Chromium (Desktop and Mobile viewports)
- **Dev Server**: Auto-started using `npm run dev`
- **Reporters**: HTML report + list output
- **Artifacts**: Screenshots and videos on failure

## Writing New Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test'

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
    await page.goto('/')
  })

  test('should do something', async ({ page }) => {
    // Test implementation
    await expect(page.getByRole('heading')).toBeVisible()
  })
})
```

### Using Test Helpers

```typescript
import { test, expect } from '@playwright/test'
import { registerUser, addStock, goToStockDetail } from './helpers/test-helpers'

test('my test', async ({ page }) => {
  await registerUser(page)
  await addStock(page, 'AAPL')
  await goToStockDetail(page, 'AAPL')
})
```

### Mocking API Responses

```typescript
test('my mocked test', async ({ page }) => {
  await page.route('**/api/v1/endpoint', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: 'mocked response' }),
    })
  })

  // Continue with test...
})
```

## Best Practices

1. **Use data-testid attributes**: Add `data-testid` to components for reliable selection
2. **Mock external dependencies**: Use API mocking for tests that shouldn't depend on backend
3. **Wait for states**: Use `waitForSelector` or `waitForTimeout` for async operations
4. **Use descriptive names**: Make test names describe what they test
5. **Keep tests independent**: Each test should be able to run independently
6. **Clean up state**: Clear localStorage/auth state in `beforeEach` hooks

## Troubleshooting

### Tests Fail Due to Backend Not Running

Use the mocked tests instead:

```bash
npx playwright test e2e/mocked-critical-path.spec.ts
```

### Tests Timeout

Increase timeout in `playwright.config.ts`:

```typescript
use: {
  actionTimeout: 10000,
  navigationTimeout: 30000,
}
```

### Browsers Not Installed

```bash
npm run test:e2e:install
```

## CI/CD Integration

For CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Install Playwright Browsers
  run: npm run test:e2e:install

- name: Run E2E Tests
  run: npm run test:e2e

- name: Upload Test Report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: playwright-report/
```

## Additional Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Testing Library Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
