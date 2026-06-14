/**
 * Manual expense E2E tests.
 *
 * Covers: create → view detail → edit → export Excel → delete.
 * Uses the real FastAPI backend and E2E database.
 * No mocking — standard expense CRUD does not touch Gemini.
 */

import { test, expect } from '@playwright/test'
import { registerUserApi, loginAsUser } from './helpers/auth'
import {
  uniqueSuffix,
  testEmail,
  testUsername,
  getFirstCategoryId,
  loginApi,
  confirmSweetAlert,
} from './helpers/testData'

const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

// Set up the user once for this test file
test.beforeAll(async () => {
  await registerUserApi(email, username, password)
})

// ── 1. Create a manual expense ────────────────────────────────────────────────
test('create a manual expense and see it in the list', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/expenses/new')

  // Wait for the category dropdown to load
  const categorySelect = page.locator('#ef-category')
  await categorySelect.waitFor({ state: 'visible' })
  // Select the first real option (not the placeholder)
  await categorySelect.selectOption({ index: 1 })

  await page.fill('#ef-title', 'E2E Manual Expense')
  await page.fill('#ef-merchant', 'E2E Merchant')
  await page.locator('#ef-currency').selectOption('THB')
  await page.fill('#ef-total', '250.00')

  // Add one item
  await page.getByRole('button', { name: /add item/i }).click()
  // Fill item name in the first item row
  const originalNameInput = page.locator('input[placeholder="Original Name"]').first()
  await originalNameInput.fill('E2E Test Item')
  const quantityInput = page.locator('input[placeholder="1"]').first()
  await quantityInput.fill('1')
  const totalPriceInput = page.locator('input[placeholder="0.00"]').last()
  await totalPriceInput.fill('250.00')

  await page.getByRole('button', { name: /save expense/i }).click()

  // SweetAlert2 success popup — confirm it
  await confirmSweetAlert(page)

  // Should redirect to expense detail
  await expect(page).toHaveURL(/\/expenses\/\d+$/)
  await expect(page.getByText('E2E Manual Expense')).toBeVisible()
})

// ── 2. Edit an existing expense ───────────────────────────────────────────────
test('edit an expense and see updated title in detail view', async ({ page }) => {
  await loginAsUser(page, email, password)

  // Create an expense first via API for speed
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const today = new Date().toISOString().slice(0, 10)
  const createRes = await fetch('http://127.0.0.1:8000/api/expenses', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category_id: catId,
      title: 'E2E Before Edit',
      receipt_date: today,
      currency: 'THB',
      total_amount: '100.00',
      items: [{ original_name: 'Item A', quantity: '1', total_price: '100.00', discount_amount: '0' }],
    }),
  })
  const expense = await createRes.json() as { id: number }

  await page.goto(`/expenses/${expense.id}/edit`)
  await page.waitForURL(`**/expenses/${expense.id}/edit`)

  // Clear title and type new value
  await page.fill('#ef-title', '')
  await page.fill('#ef-title', 'E2E Edited Expense')
  await page.getByRole('button', { name: /update expense/i }).click()
  await confirmSweetAlert(page)

  // Should redirect to expense detail
  await page.waitForURL(`**/expenses/${expense.id}`)
  await expect(page.getByText('E2E Edited Expense')).toBeVisible()
})

// ── 3. Delete an expense ──────────────────────────────────────────────────────
test('delete an expense and confirm it disappears from the list', async ({ page }) => {
  await loginAsUser(page, email, password)

  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const today = new Date().toISOString().slice(0, 10)
  const createRes = await fetch('http://127.0.0.1:8000/api/expenses', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category_id: catId,
      title: 'E2E Delete Me',
      receipt_date: today,
      currency: 'THB',
      total_amount: '50.00',
      items: [{ original_name: 'Delete Item', quantity: '1', total_price: '50.00', discount_amount: '0' }],
    }),
  })
  const expense = await createRes.json() as { id: number }

  // Open the detail page and delete
  await page.goto(`/expenses/${expense.id}`)
  await page.getByRole('button', { name: /delete expense/i }).click()
  // SweetAlert2 confirmation — confirm delete
  await confirmSweetAlert(page)
  // SweetAlert2 success — dismiss
  await confirmSweetAlert(page)

  // Should redirect to expenses list
  await page.waitForURL('**/expenses', { timeout: 8_000 })

  // The deleted expense should no longer appear
  await expect(page.getByText('E2E Delete Me')).not.toBeVisible()
})

// ── 4. Export Excel triggers a download ──────────────────────────────────────
test('export Excel from the expense list triggers a .xlsx download', async ({ page }) => {
  await loginAsUser(page, email, password)

  // Ensure there is at least one expense
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const today = new Date().toISOString().slice(0, 10)
  await fetch('http://127.0.0.1:8000/api/expenses', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category_id: catId,
      title: 'E2E Export Expense',
      receipt_date: today,
      currency: 'THB',
      total_amount: '300.00',
      items: [{ original_name: 'Export Item', quantity: '1', total_price: '300.00', discount_amount: '0' }],
    }),
  })

  await page.goto('/expenses')

  // Capture the download event before clicking
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /export excel/i }).click()
  const download = await downloadPromise

  const suggestedName = download.suggestedFilename()
  expect(suggestedName).toMatch(/\.xlsx$/)

  // The downloaded file is not empty
  const path = await download.path()
  expect(path).not.toBeNull()
  const { statSync } = await import('fs')
  const stats = statSync(path!)
  expect(stats.size).toBeGreaterThan(0)
})
