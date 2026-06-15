/**
 * Dashboard consistency E2E tests.
 *
 * Seeds known data and verifies the summary cards show correct counts.
 * Verifies THB and USD remain separate, deleted expenses are excluded,
 * and only 5 recent expenses appear at most.
 */

import { test, expect } from '@playwright/test'
import { registerUserApi, loginAsUser, loginApi } from './helpers/auth'
import {
  uniqueSuffix,
  testEmail,
  testUsername,
  getFirstCategoryId,
  createExpenseApi,
  deleteExpenseApi,
} from './helpers/testData'

const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

let token: string
let catId: number

test.beforeAll(async () => {
  await registerUserApi(email, username, password)
  token = await loginApi(email, password)
  catId = await getFirstCategoryId(token)

  const today = new Date().toISOString().slice(0, 10)

  // Create 3 THB expenses (2 draft, 1 confirmed)
  const [e1, e2, e3] = await Promise.all([
    createExpenseApi(token, 'Dashboard THB 1', catId, 'THB', '100.00'),
    createExpenseApi(token, 'Dashboard THB 2', catId, 'THB', '200.00'),
    createExpenseApi(token, 'Dashboard THB Confirmed', catId, 'THB', '300.00'),
  ])
  // Confirm e3
  await fetch(`http://127.0.0.1:8000/api/expenses/${e3.id}/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })

  // Create 1 USD expense
  await createExpenseApi(token, 'Dashboard USD 1', catId, 'USD', '50.00')

  // Create 1 expense that will be deleted — should not appear in dashboard
  const toDelete = await createExpenseApi(token, 'Dashboard Deleted', catId, 'THB', '999.00')
  await deleteExpenseApi(token, toDelete.id)

  // Create 2 more THB expenses to ensure recent list (max 5)
  await createExpenseApi(token, 'Dashboard THB 4', catId, 'THB', '10.00')
  await createExpenseApi(token, 'Dashboard THB 5', catId, 'THB', '20.00')
  await createExpenseApi(token, 'Dashboard THB 6', catId, 'THB', '30.00')
})

// ── 1. Summary card counts ────────────────────────────────────────────────────
test('dashboard summary cards show correct total, confirmed, and draft counts', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/dashboard')

  // Wait for data to load
  await expect(page.getByText(/total expenses/i)).toBeVisible()

  // We have: 3 THB + 1 USD + 2 more THB (total 6; deleted one is excluded) + THB 4, 5, 6 = 7
  // Exact counts: e1, e2, e3, USD1, THB4, THB5, THB6 = 7 expenses total
  // 1 confirmed (e3), 6 draft

  const summaryCards = page.locator('.summary-card')
  await expect(summaryCards.first()).toBeVisible()

  // Total expenses card value should be 7
  const totalExpensesValue = page.locator('.summary-card').nth(0).locator('.summary-card-value')
  await expect(totalExpensesValue).toHaveText('7')

  // Confirmed count = 1
  const confirmedValue = page.locator('.summary-card').nth(1).locator('.summary-card-value')
  await expect(confirmedValue).toHaveText('1')

  // Draft count = 6
  const draftValue = page.locator('.summary-card').nth(2).locator('.summary-card-value')
  await expect(draftValue).toHaveText('6')
})

// ── 2. Currency totals keep THB and USD separate ──────────────────────────────
test('dashboard spending by currency shows THB and USD separately', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/dashboard')

  await expect(page.getByText('THB')).toBeVisible()
  await expect(page.getByText('USD')).toBeVisible()

  // They must be in separate rows — verify both currency codes are shown
  const currencyRows = page.locator('.currency-row')
  const count = await currencyRows.count()
  expect(count).toBeGreaterThanOrEqual(2)
})

// ── 3. Deleted expense is NOT shown in recent list ────────────────────────────
test('deleted expense does not appear in the recent expenses list', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/dashboard')

  await expect(page.getByText(/recent expenses/i)).toBeVisible()
  await expect(page.getByText('Dashboard Deleted')).not.toBeVisible()
})

// ── 4. Recent expenses list shows at most 5 ───────────────────────────────────
test('recent expenses list shows at most 5 items', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/dashboard')

  await expect(page.getByText(/recent expenses/i)).toBeVisible()

  // Wait for actual expense rows to load
  const recentRows = page.locator('.recent-expense-row')
  await expect(recentRows.first()).toBeVisible()

  const count = await recentRows.count()
  expect(count).toBeLessThanOrEqual(5)
})
