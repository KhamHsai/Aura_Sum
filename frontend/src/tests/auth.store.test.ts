/**
 * Auth store tests.
 * All backend calls are mocked — no real server required.
 */
import { it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// ── Mock the API modules ──────────────────────────────────────────────────────
vi.mock('../api/authApi', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getCurrentUser: vi.fn(),
}))

// Mock the router so store actions that call useRouter() don't blow up.
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

import { useAuthStore } from '../stores/auth'
import * as authApi from '../api/authApi'
import { TOKEN_KEY } from '../api/axios'

// Typed helpers for the mocked functions.
const mockLogin = vi.mocked(authApi.loginUser)
const mockGetMe = vi.mocked(authApi.getCurrentUser)

const fakeToken = 'fake-access-token'
const fakeUser = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  full_name: null,
  preferred_language: 'en',
  role: 'user',
  is_active: true,
  created_at: '2024-01-01T00:00:00',
  updated_at: '2024-01-01T00:00:00',
}
const fakeLoginResponse = {
  access_token: fakeToken,
  refresh_token: 'fake-refresh',
  token_type: 'bearer',
  expires_in: 1800,
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

// 1. Login stores token.
it('login stores access token in state and localStorage', async () => {
  mockLogin.mockResolvedValue(fakeLoginResponse)
  mockGetMe.mockResolvedValue(fakeUser)

  const auth = useAuthStore()
  await auth.login({ email: 'test@example.com', password: 'password123' })

  expect(auth.token).toBe(fakeToken)
  expect(localStorage.getItem(TOKEN_KEY)).toBe(fakeToken)
})

// 2. Current user loads after login.
it('login loads the current user into the store', async () => {
  mockLogin.mockResolvedValue(fakeLoginResponse)
  mockGetMe.mockResolvedValue(fakeUser)

  const auth = useAuthStore()
  await auth.login({ email: 'test@example.com', password: 'password123' })

  expect(auth.user).toEqual(fakeUser)
  expect(auth.isAuthenticated).toBe(true)
})

// 3. Invalid session clears token.
it('initializeAuth clears token when /me returns 401', async () => {
  localStorage.setItem(TOKEN_KEY, fakeToken)
  mockGetMe.mockRejectedValue(new Error('Unauthorized'))

  const auth = useAuthStore()
  await auth.initializeAuth()

  expect(auth.token).toBeNull()
  expect(auth.user).toBeNull()
  expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
})

// 4. Logout clears store and localStorage.
it('logout clears token, user, and localStorage', async () => {
  mockLogin.mockResolvedValue(fakeLoginResponse)
  mockGetMe.mockResolvedValue(fakeUser)

  const auth = useAuthStore()
  await auth.login({ email: 'test@example.com', password: 'password123' })

  auth.logout()

  expect(auth.token).toBeNull()
  expect(auth.user).toBeNull()
  expect(localStorage.getItem(TOKEN_KEY)).toBeNull()
})

// 14. Password is never saved in localStorage.
it('password is never stored in localStorage', async () => {
  mockLogin.mockResolvedValue(fakeLoginResponse)
  mockGetMe.mockResolvedValue(fakeUser)

  const auth = useAuthStore()
  await auth.login({ email: 'test@example.com', password: 'supersecret' })

  const allStorage = Object.entries(localStorage).map(([, v]) => v).join(' ')
  expect(allStorage).not.toContain('supersecret')
})

// initializeAuth restores a valid session.
it('initializeAuth restores a valid session', async () => {
  localStorage.setItem(TOKEN_KEY, fakeToken)
  mockGetMe.mockResolvedValue(fakeUser)

  const auth = useAuthStore()
  await auth.initializeAuth()

  expect(auth.user).toEqual(fakeUser)
  expect(auth.isAuthenticated).toBe(true)
})

// initializeAuth does nothing when no token is saved.
it('initializeAuth does nothing when no token in storage', async () => {
  const auth = useAuthStore()
  await auth.initializeAuth()

  expect(auth.user).toBeNull()
  expect(mockGetMe).not.toHaveBeenCalled()
})
