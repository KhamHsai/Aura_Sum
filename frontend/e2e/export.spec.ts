/**
 * Excel export E2E tests.
 *
 * Tests the Excel download from both the Expenses list and the Dashboard.
 * Uses the real backend — export does not touch Gemini.
 */

import { test, expect } from '@playwright/test'
import { registerUserApi, loginAsUser } from './helpers/auth'
import {
  uniqueSuffix,
  testEmail,
  testUsername,
  getFirstCategoryId,
} from './helpers/testData'
import { loginApi } from './helpers/auth'

const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

test.beforeAll(async () => {
  // Set up user and seed one expense so the export is never empty
  await registerUserApi(email, username, password)
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const today = new Date().toISOString().slice(0, 10)
  await fetch('http://127.0.0.1:8000/api/expenses', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category_id: catId,
      title: 'E2E Export Seed Expense',
      receipt_date: today,
      currency: 'USD',
      total_amount: '42.00',
      items: [{ original_name: 'Export Seed Item', quantity: '1', total_price: '42.00', discount_amount: '0' }],
    }),
  })
})

// ── 1. Export from Expenses list ──────────────────────────────────────────────
test('Export Excel from expenses list downloads a .xlsx file', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/expenses')

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /export excel/i }).click()
  const download = await downloadPromise

  expect(download.suggestedFilename()).toMatch(/\.xlsx$/)

  const filePath = await download.path()
  expect(filePath).not.toBeNull()

  const { statSync } = await import('fs')
  expect(statSync(filePath!).size).toBeGreaterThan(0)
})

// ── 2. Export from Dashboard ──────────────────────────────────────────────────
test('Export Excel from dashboard downloads a .xlsx file', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/dashboard')

  // Wait for the page to load its data
  await expect(page.getByText(/export excel/i)).toBeVisible()

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: /export excel/i }).click()
  const download = await downloadPromise

  expect(download.suggestedFilename()).toMatch(/\.xlsx$/)

  const filePath = await download.path()
  expect(filePath).not.toBeNull()

  const { statSync } = await import('fs')
  expect(statSync(filePath!).size).toBeGreaterThan(0)
})
