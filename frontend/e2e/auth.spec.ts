/**
 * Authentication E2E tests.
 *
 * Covers: register → login → dashboard → refresh → logout → protected redirect.
 * Also verifies invalid login and duplicate registration show safe errors.
 *
 * Uses the real FastAPI backend and E2E database.
 * No mocking — auth flows do not touch Gemini.
 */

import { test, expect } from '@playwright/test'
import {
  registerViaForm,
  loginViaForm,
  loginApi,
  registerUserApi,
} from './helpers/auth'
import { uniqueSuffix, testEmail, testUsername } from './helpers/testData'

// ── Unique user for this test run ─────────────────────────────────────────────
const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

// ── 1. Full register → login → dashboard flow ─────────────────────────────────
test('register via form then auto-redirect to login', async ({ page }) => {
  await registerViaForm(page, username, email, password)
  // After successful registration a success message appears and the user
  // is redirected to /login after 1.5 s
  await page.waitForURL('**/login', { timeout: 5_000 })
  await expect(page).toHaveURL(/\/login/)
})

// ── 2. Login via form reaches dashboard ───────────────────────────────────────
test('login with valid credentials reaches dashboard', async ({ page }) => {
  await registerUserApi(email, username, password)
  await loginViaForm(page, email, password)
  await expect(page).toHaveURL(/\/dashboard/)
  // Welcome message shows the username
  await expect(page.getByText(username)).toBeVisible()
})

// ── 3. Token stored in localStorage, password is NOT ─────────────────────────
test('access token is stored in localStorage after login, password is not', async ({ page }) => {
  await registerUserApi(email, username, password)
  await loginViaForm(page, email, password)
  const stored = await page.evaluate(() => {
    return {
      token: localStorage.getItem('auth_token'),
      allValues: Object.entries(localStorage).map(([, v]) => v).join(' '),
    }
  })
  expect(stored.token).not.toBeNull()
  expect(stored.token!.length).toBeGreaterThan(10)
  expect(stored.allValues).not.toContain(password)
})

// ── 4. Refresh browser keeps session ─────────────────────────────────────────
test('refreshing the browser keeps the user authenticated', async ({ page }) => {
  await registerUserApi(email, username, password)
  await loginViaForm(page, email, password)
  await expect(page).toHaveURL(/\/dashboard/)
  // Reload the page — the app reads the token from localStorage and restores the session
  await page.reload()
  await expect(page).toHaveURL(/\/dashboard/)
  await expect(page.getByText(username)).toBeVisible()
})

// ── 5. Logout clears session ──────────────────────────────────────────────────
test('logout clears the session and redirects to login', async ({ page }) => {
  await registerUserApi(email, username, password)
  await loginViaForm(page, email, password)

  // Find and click the logout button in the nav
  const logoutBtn = page.getByRole('button', { name: /logout/i })
  await logoutBtn.click()

  await page.waitForURL('**/login', { timeout: 5_000 })
  await expect(page).toHaveURL(/\/login/)

  // Token is gone from localStorage
  const token = await page.evaluate(() => localStorage.getItem('auth_token'))
  expect(token).toBeNull()
})

// ── 6. Protected page redirects unauthenticated users ─────────────────────────
test('visiting a protected page without a token redirects to login', async ({ page }) => {
  await page.goto('/dashboard')
  await page.waitForURL('**/login', { timeout: 5_000 })
  await expect(page).toHaveURL(/\/login/)
})

// ── 7. Invalid login shows a safe error message ───────────────────────────────
test('invalid login credentials show an error, not a stack trace', async ({ page }) => {
  await registerUserApi(email, username, password)
  await page.goto('/login')
  await page.fill('#email', email)
  await page.fill('#password', 'wrong-password-xyz')
  await page.click('button[type="submit"]')

  // An error message appears inside the auth card
  const errorAlert = page.locator('.alert-error')
  await expect(errorAlert).toBeVisible()

  // The error must not expose internal details
  const errorText = await errorAlert.textContent()
  expect(errorText).not.toContain('Traceback')
  expect(errorText).not.toContain('sqlalchemy')
  expect(errorText).not.toContain('stack')
  // Still on login page
  await expect(page).toHaveURL(/\/login/)
})

// ── 8. Duplicate registration shows a safe error ──────────────────────────────
test('registering with a duplicate email shows a safe error', async ({ page }) => {
  await registerUserApi(email, username, password)
  // Try to register again with the same email
  await registerViaForm(page, `other${username}`, email, password)

  const errorAlert = page.locator('.alert-error')
  await expect(errorAlert).toBeVisible()
  const errorText = await errorAlert.textContent()
  expect(errorText).not.toContain('Traceback')
  expect(errorText).not.toContain('password_hash')
  // Still on register page
  await expect(page).toHaveURL(/\/register/)
})

// ── 9. Authenticated user cannot reach /login ─────────────────────────────────
test('authenticated user visiting /login is redirected to dashboard', async ({ page }) => {
  await registerUserApi(email, username, password)
  const token = await loginApi(email, password)
  await page.goto('/login')
  await page.evaluate((t) => localStorage.setItem('auth_token', t), token)
  await page.goto('/login')
  await expect(page).toHaveURL(/\/dashboard/)
})
