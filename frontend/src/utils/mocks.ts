/**
 * Mock setup file for vitest
 * This file should be imported in test files that need React Router mocking
 */

import { vi } from 'vitest'

/**
 * Mock navigation function - exported for tests to assert on navigation calls
 */
export const mockNavigate = vi.fn()

/**
 * Setup React Router mocks
 * Call this in your test file before importing components that use useNavigate
 */
export function setupRouterMocks() {
  vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom')
    return {
      ...actual as any,
      useNavigate: () => mockNavigate,
      Navigate: () => null,
      Outlet: () => null,
    }
  })
}
