/**
 * Auth helpers for E2E tests.
 * All helpers call the real backend API — no mocking for auth flows.
 */

import type { Page } from '@playwright/test'

const API_BASE = 'http://127.0.0.1:8000/api'

/** Register a new user via the API directly (faster than filling the form). */
export async function registerUserApi(
  email: string,
  username: string,
  password: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, username, password }),
  })
  if (!res.ok && res.status !== 409) {
    throw new Error(`Register failed: ${res.status} ${await res.text()}`)
  }
}

/** Login via the API and return the access token. */
export async function loginApi(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(`Login failed: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return data.access_token as string
}

/**
 * Inject a valid token directly into localStorage then navigate to the dashboard.
 * This avoids the login form and makes test setup faster.
 */
export async function loginAsUser(page: Page, email: string, password: string): Promise<void> {
  const token = await loginApi(email, password)
  await page.goto('/login')
  await page.evaluate((t: string) => {
    localStorage.setItem('auth_token', t)
  }, token)
  await page.goto('/dashboard')
  // Wait for the dashboard to actually load
  await page.waitForURL('**/dashboard')
}

/** Fill and submit the login form through the browser (used for auth flow tests). */
export async function loginViaForm(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login')
  await page.fill('#email', email)
  await page.fill('#password', password)
  await page.click('button[type="submit"]')
  await page.waitForURL('**/dashboard')
}

/** Fill and submit the register form through the browser. */
export async function registerViaForm(
  page: Page,
  username: string,
  email: string,
  password: string,
): Promise<void> {
  await page.goto('/register')
  await page.fill('#username', username)
  await page.fill('#email', email)
  await page.fill('#password', password)
  await page.fill('#confirm_password', password)
  await page.click('button[type="submit"]')
}
