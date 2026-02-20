import api from './api'
import type { AuthResponse, User } from './types'

export const login = (email: string, password: string) =>
  api.post<AuthResponse>('/v1/auth/login', { email, password })

export const register = (email: string, password: string, full_name: string) =>
  api.post<AuthResponse>('/v1/auth/register', {
    email,
    password,
    full_name,
  })

export const getMe = () => api.get<User>('/v1/auth/me')
