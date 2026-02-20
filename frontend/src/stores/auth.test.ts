import { describe, it, expect, beforeEach } from 'vitest'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/services/types'

const mockUser: User = {
    id: 'user-123',
    email: 'test@example.com',
    full_name: 'Test User',
}

describe('useAuthStore', () => {
    beforeEach(() => {
        // Reset store state before each test
        useAuthStore.setState({
            token: null,
            user: null,
            isAuthenticated: false,
        })
        localStorage.clear()
    })

    it('initializes with null token and user', () => {
        const state = useAuthStore.getState()
        expect(state.token).toBeNull()
        expect(state.user).toBeNull()
        expect(state.isAuthenticated).toBe(false)
    })

    it('login sets token, user, and isAuthenticated', () => {
        useAuthStore.getState().login('jwt-token-123', mockUser)

        const state = useAuthStore.getState()
        expect(state.token).toBe('jwt-token-123')
        expect(state.user).toEqual(mockUser)
        expect(state.isAuthenticated).toBe(true)
    })

    it('login stores token in localStorage', () => {
        useAuthStore.getState().login('jwt-token-123', mockUser)
        expect(localStorage.getItem('auth_token')).toBe('jwt-token-123')
    })

    it('logout clears token, user, and isAuthenticated', () => {
        // Login first
        useAuthStore.getState().login('jwt-token-123', mockUser)
        // Then logout
        useAuthStore.getState().logout()

        const state = useAuthStore.getState()
        expect(state.token).toBeNull()
        expect(state.user).toBeNull()
        expect(state.isAuthenticated).toBe(false)
    })

    it('logout removes token from localStorage', () => {
        useAuthStore.getState().login('jwt-token-123', mockUser)
        useAuthStore.getState().logout()
        expect(localStorage.getItem('auth_token')).toBeNull()
    })

    it('setUser updates user without changing auth status', () => {
        useAuthStore.getState().login('jwt-token-123', mockUser)

        const updatedUser = { ...mockUser, full_name: 'Updated Name' }
        useAuthStore.getState().setUser(updatedUser)

        const state = useAuthStore.getState()
        expect(state.user?.full_name).toBe('Updated Name')
        expect(state.isAuthenticated).toBe(true)
        expect(state.token).toBe('jwt-token-123')
    })

    it('handles multiple login/logout cycles', () => {
        const { login, logout } = useAuthStore.getState()

        login('token-1', mockUser)
        expect(useAuthStore.getState().isAuthenticated).toBe(true)

        logout()
        expect(useAuthStore.getState().isAuthenticated).toBe(false)

        login('token-2', { ...mockUser, email: 'new@example.com' })
        const state = useAuthStore.getState()
        expect(state.token).toBe('token-2')
        expect(state.user?.email).toBe('new@example.com')
        expect(state.isAuthenticated).toBe(true)
    })
})
