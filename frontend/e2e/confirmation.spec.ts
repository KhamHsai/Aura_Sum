/**
 * AI Draft Confirmation E2E tests.
 *
 * Creates a real draft expense via the API (no Gemini involved),
 * then confirms it through the browser UI.
 * The confirm endpoint itself does NOT call Gemini, so we use the real backend.
 */

import { test, expect } from '@playwright/test'
import { registerUserApi, loginAsUser } from './helpers/auth'
import {
  uniqueSuffix,
  testEmail,
  testUsername,
  getFirstCategoryId,
  loginApi,
  createExpenseApi,
  confirmSweetAlert,
} from './helpers/testData'

const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

test.beforeAll(async () => {
  await registerUserApi(email, username, password)
})

// ── 1. Confirm a draft expense from the detail page ───────────────────────────
test('confirm a draft expense from the detail page shows confirmed badge', async ({ page }) => {
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const draft = await createExpenseApi(token, 'E2E Confirm Test', catId)

  await loginAsUser(page, email, password)
  await page.goto(`/expenses/${draft.id}`)

  // The Draft badge should be visible
  await expect(page.locator('.badge-draft')).toBeVisible()

  // Click the Confirm Expense button
  await page.getByRole('button', { name: /confirm expense/i }).click()

  // SweetAlert2 confirmation dialog — click confirm
  await confirmSweetAlert(page)

  // SweetAlert2 success dialog — dismiss
  await confirmSweetAlert(page)

  // The Confirmed badge should now appear
  await expect(page.locator('.badge-confirmed')).toBeVisible()
  // The Confirm button should be gone
  await expect(page.getByRole('button', { name: /confirm expense/i })).not.toBeVisible()
})

// ── 2. Confirm via the edit page ──────────────────────────────────────────────
test('confirm a draft expense from the edit page and see confirmed detail', async ({ page }) => {
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const draft = await createExpenseApi(token, 'E2E Confirm Via Edit', catId)

  await loginAsUser(page, email, password)
  await page.goto(`/expenses/${draft.id}/edit`)

  // Wait for the form to load
  await expect(page.locator('#ef-title')).toHaveValue('E2E Confirm Via Edit')

  // Click the Confirm Expense button (below the form)
  await page.getByRole('button', { name: /confirm expense/i }).click()
  // SweetAlert2 confirmation — confirm
  await confirmSweetAlert(page)
  // SweetAlert2 success — dismiss
  await confirmSweetAlert(page)

  // Redirected to detail page
  await page.waitForURL(`**/expenses/${draft.id}`, { timeout: 8_000 })
  await expect(page.locator('.badge-confirmed')).toBeVisible()
})

// ── 3. Already-confirmed expense shows no confirm button ──────────────────────
test('already-confirmed expense does not show a confirm button', async ({ page }) => {
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const draft = await createExpenseApi(token, 'E2E Already Confirmed', catId)

  // Confirm it via API directly
  await fetch(`http://127.0.0.1:8000/api/expenses/${draft.id}/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  })

  await loginAsUser(page, email, password)
  await page.goto(`/expenses/${draft.id}`)

  await expect(page.locator('.badge-confirmed')).toBeVisible()
  await expect(page.getByRole('button', { name: /confirm expense/i })).not.toBeVisible()
})
