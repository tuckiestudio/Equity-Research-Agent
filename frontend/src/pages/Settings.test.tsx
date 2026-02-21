import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Settings from './Settings'

// Mock the settingsService
vi.mock('@/services/settings', () => ({
    settingsService: {
        getSettings: vi.fn().mockResolvedValue({
            fundamentals_provider: 'fmp',
            price_provider: 'finnhub',
            profile_provider: 'fmp',
            news_provider: 'finnhub',
            fmp_api_key: 'mock-fmp-key',
        }),
        updateSettings: vi.fn(),
    },
}))

const createTestQueryClient = () =>
    new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    })

describe('Settings Page', () => {
    it('renders settings title and form elements', async () => {
        const queryClient = createTestQueryClient()

        render(
            <QueryClientProvider client={queryClient}>
                <Settings />
            </QueryClientProvider>
        )

        // Wait for loading to finish and settings to display
        await waitFor(() => {
            expect(screen.getByText('Settings')).toBeInTheDocument()
            expect(screen.getByText('Data Providers')).toBeInTheDocument()
            expect(screen.getByText('API Keys')).toBeInTheDocument()
        })
    })
})
