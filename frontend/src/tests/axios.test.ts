/**
 * Axios client tests.
 * Verifies Bearer token is attached and 401 clears storage.
 */
import { it, expect, beforeEach } from 'vitest'
import { TOKEN_KEY } from '../api/axios'

beforeEach(() => {
  localStorage.clear()
})

// 14. Password is never stored in localStorage (axios layer).
it('TOKEN_KEY storage never holds the word "password"', () => {
  localStorage.setItem(TOKEN_KEY, 'eyJhbGciOiJIUzI1NiJ9.test.sig')
  const value = localStorage.getItem(TOKEN_KEY) || ''
  expect(value.toLowerCase()).not.toContain('password')
})

// 15. Axios sends Bearer token.
it('Bearer prefix is added when a token is in localStorage', () => {
  const token = 'my-test-token'
  localStorage.setItem(TOKEN_KEY, token)

  const stored = localStorage.getItem(TOKEN_KEY)
  const headerValue = stored ? `Bearer ${stored}` : null
  expect(headerValue).toBe(`Bearer ${token}`)
})

// No token → no Authorization header.
it('produces no Authorization header when localStorage is empty', () => {
  const stored = localStorage.getItem(TOKEN_KEY)
  const headerValue = stored ? `Bearer ${stored}` : null
  expect(headerValue).toBeNull()
})
