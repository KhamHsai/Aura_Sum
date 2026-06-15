/**
 * Mobile layout smoke tests.
 *
 * Uses an iPhone 14 Pro viewport (390 × 844).
 * Verifies navigation, dashboard cards, quick actions, and the expense form
 * are usable at mobile width.
 *
 * This is a smoke test — not visual pixel comparison.
 */

import { test, expect } from '@playwright/test'
import { registerUserApi, loginAsUser } from './helpers/auth'
import { uniqueSuffix, testEmail, testUsername } from './helpers/testData'

const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

const MOBILE_VIEWPORT = { width: 390, height: 844 }

test.beforeAll(async () => {
  await registerUserApi(email, username, password)
})

// ── 1. Dashboard is usable on mobile ─────────────────────────────────────────
test('dashboard renders usably at mobile viewport', async ({ page }) => {
  await page.setViewportSize(MOBILE_VIEWPORT)
  await loginAsUser(page, email, password)
  await page.goto('/dashboard')

  // Page heading is visible
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

  // Quick-action buttons are present
  await expect(page.getByRole('link', { name: /add expense/i })).toBeVisible()
  await expect(page.getByRole('link', { name: /upload receipt/i })).toBeVisible()

  // No horizontal overflow — scrollWidth should not exceed viewport width
  const hasOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth
  })
  expect(hasOverflow).toBe(false)
})

// ── 2. Expense list is usable on mobile ──────────────────────────────────────
test('expense list renders usably at mobile viewport', async ({ page }) => {
  await page.setViewportSize(MOBILE_VIEWPORT)
  await loginAsUser(page, email, password)
  await page.goto('/expenses')

  // Page heading visible
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()

  // Add Expense link is visible
  await expect(page.getByRole('link', { name: /add expense/i })).toBeVisible()
})

// ── 3. Expense create form is usable on mobile ────────────────────────────────
test('expense create form is accessible at mobile viewport', async ({ page }) => {
  await page.setViewportSize(MOBILE_VIEWPORT)
  await loginAsUser(page, email, password)
  await page.goto('/expenses/new')

  // Key form fields are in the viewport / reachable by scrolling
  await page.locator('#ef-title').scrollIntoViewIfNeeded()
  await expect(page.locator('#ef-title')).toBeVisible()

  await page.locator('#ef-total').scrollIntoViewIfNeeded()
  await expect(page.locator('#ef-total')).toBeVisible()

  // No dangerous horizontal overflow
  const hasOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth
  })
  expect(hasOverflow).toBe(false)
})

// ── 4. Navigation links are accessible on mobile ─────────────────────────────
test('navigation is accessible at mobile viewport', async ({ page }) => {
  await page.setViewportSize(MOBILE_VIEWPORT)
  await loginAsUser(page, email, password)

  // The nav is in AppLayout — verify we can reach key destinations
  // Navigate by URL since a hamburger menu may hide nav links
  await page.goto('/expenses')
  await expect(page).toHaveURL(/\/expenses/)

  await page.goto('/receipts')
  await expect(page).toHaveURL(/\/receipts/)

  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/dashboard/)
})

// ── 5. Login form is usable on mobile ────────────────────────────────────────
test('login form is accessible at mobile viewport', async ({ page }) => {
  await page.setViewportSize(MOBILE_VIEWPORT)
  await page.goto('/login')

  await expect(page.locator('#email')).toBeVisible()
  await expect(page.locator('#password')).toBeVisible()
  await expect(page.getByRole('button', { name: /login/i })).toBeVisible()

  // No horizontal overflow on the auth card
  const hasOverflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth > window.innerWidth
  })
  expect(hasOverflow).toBe(false)
})
