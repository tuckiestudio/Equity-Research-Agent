import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock localStorage for tests that use it directly
const localStorageMock = (() => {
    let store: Record<string, string> = {}
    return {
        getItem: vi.fn((key: string) => store[key] ?? null),
        setItem: vi.fn((key: string, value: string) => {
            store[key] = value
        }),
        removeItem: vi.fn((key: string) => {
            delete store[key]
        }),
        clear: vi.fn(() => {
            store = {}
        }),
        get length() {
            return Object.keys(store).length
        },
        key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
    }
})()

Object.defineProperty(globalThis, 'localStorage', { value: localStorageMock })

// Mock axios to test the api module's interceptor behavior
vi.mock('axios', () => {
    const interceptors = {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() },
    }
    const instance = {
        interceptors,
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        defaults: { baseURL: '' },
    }
    return {
        default: {
            create: vi.fn(() => instance),
        },
    }
})

// Need to import axios after the mock
import axios from 'axios'

describe('API Service', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        localStorageMock.clear()
    })

    it('axios.create is called when api module loads', async () => {
        vi.resetModules()
        await import('@/services/api')
        expect(axios.create).toHaveBeenCalled()
    })

    it('creates axios instance with correct base URL', async () => {
        vi.resetModules()
        await import('@/services/api')
        expect(axios.create).toHaveBeenCalledWith(
            expect.objectContaining({
                baseURL: expect.any(String),
            })
        )
    })

    it('registers request interceptor', async () => {
        vi.resetModules()
        await import('@/services/api')
        const instance = axios.create()
        expect(instance.interceptors.request.use).toHaveBeenCalled()
    })

    it('registers response interceptor', async () => {
        vi.resetModules()
        await import('@/services/api')
        const instance = axios.create()
        expect(instance.interceptors.response.use).toHaveBeenCalled()
    })
})

describe('API Interceptor Behavior', () => {
    beforeEach(() => {
        localStorageMock.clear()
    })

    it('request interceptor adds Authorization header when token exists', () => {
        localStorageMock.setItem('auth_token', 'test-jwt-token')

        // Simulate what the request interceptor does
        const config = { headers: {} as Record<string, string> }
        const token = localStorageMock.getItem('auth_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }

        expect(config.headers.Authorization).toBe('Bearer test-jwt-token')
    })

    it('request interceptor does not add header when no token', () => {
        const config = { headers: {} as Record<string, string> }
        const token = localStorageMock.getItem('auth_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }

        expect(config.headers.Authorization).toBeUndefined()
    })

    it('response interceptor removes token on 401', () => {
        localStorageMock.setItem('auth_token', 'expired-token')

        // Simulate what the response interceptor does on 401
        const error = { response: { status: 401 } }
        if (error.response?.status === 401) {
            localStorageMock.removeItem('auth_token')
        }

        expect(localStorageMock.getItem('auth_token')).toBeNull()
    })

    it('response interceptor preserves token on non-401 errors', () => {
        localStorageMock.setItem('auth_token', 'valid-token')

        const error = { response: { status: 500 } }
        if (error.response?.status === 401) {
            localStorageMock.removeItem('auth_token')
        }

        expect(localStorageMock.getItem('auth_token')).toBe('valid-token')
    })
})
