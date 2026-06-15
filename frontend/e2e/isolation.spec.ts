/**
 * User isolation E2E tests.
 *
 * Verifies that User B cannot view, edit, delete, confirm, translate,
 * or access receipts belonging to User A.
 *
 * Tests direct URL access, not just hidden buttons.
 * Uses the real backend.
 */

import { test, expect } from '@playwright/test'
import { registerUserApi, loginAsUser } from './helpers/auth'
import {
  uniqueSuffix,
  testEmail,
  testUsername,
  getFirstCategoryId,
  createExpenseApi,
  uploadReceiptApi,
} from './helpers/testData'
import { loginApi } from './helpers/auth'
import { readFileSync } from 'fs'
import path from 'path'

const suffix = uniqueSuffix()

const emailA = testEmail(`a${suffix}`)
const usernameA = testUsername(`a${suffix}`)

const emailB = testEmail(`b${suffix}`)
const usernameB = testUsername(`b${suffix}`)

const password = 'Password123!'

let tokenA: string
let expenseIdA: number
let receiptIdA: number

test.beforeAll(async () => {
  // Create both users
  await registerUserApi(emailA, usernameA, password)
  await registerUserApi(emailB, usernameB, password)

  // Log in as User A and create data
  tokenA = await loginApi(emailA, password)
  const catId = await getFirstCategoryId(tokenA)
  const expenseA = await createExpenseApi(tokenA, 'User A Private Expense', catId)
  expenseIdA = expenseA.id

  // Upload a receipt for User A
  const fixturePath = path.resolve(__dirname, 'fixtures/test-receipt.png')
  const fileBytes = new Uint8Array(readFileSync(fixturePath))
  receiptIdA = await uploadReceiptApi(tokenA, fileBytes)
})

// ── 1. User B cannot view User A expense (direct URL) ─────────────────────────
test('User B cannot view User A expense detail', async ({ page }) => {
  await loginAsUser(page, emailB, password)
  await page.goto(`/expenses/${expenseIdA}`)

  // Should show not-found, not User A's expense title
  await expect(page.getByText('User A Private Expense')).not.toBeVisible()
})

// ── 2. User B cannot edit User A expense ─────────────────────────────────────
test('User B cannot edit User A expense', async ({ page }) => {
  await loginAsUser(page, emailB, password)
  await page.goto(`/expenses/${expenseIdA}/edit`)

  // The form should not load with User A's title
  await expect(page.locator('#ef-title')).not.toHaveValue('User A Private Expense')
})

// ── 3. User B API call to delete User A expense returns 404 ──────────────────
test('User B direct API delete of User A expense returns 404', async () => {
  const tokenB = await loginApi(emailB, password)
  const res = await fetch(`http://127.0.0.1:8000/api/expenses/${expenseIdA}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${tokenB}` },
  })
  expect(res.status).toBe(404)
})

// ── 4. User B API call to confirm User A expense returns 404 ──────────────────
test('User B direct API confirm of User A expense returns 404', async () => {
  const tokenB = await loginApi(emailB, password)
  const res = await fetch(`http://127.0.0.1:8000/api/expenses/${expenseIdA}/confirm`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${tokenB}` },
  })
  expect(res.status).toBe(404)
})

// ── 5. User B API call to translate User A expense returns 404 ────────────────
test('User B direct API translate of User A expense returns 404', async () => {
  const tokenB = await loginApi(emailB, password)
  const res = await fetch(`http://127.0.0.1:8000/api/expenses/${expenseIdA}/translate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${tokenB}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_language: 'en' }),
  })
  expect(res.status).toBe(404)
})

// ── 6. User B cannot view User A receipt ─────────────────────────────────────
test('User B cannot view User A receipt detail', async ({ page }) => {
  await loginAsUser(page, emailB, password)
  await page.goto(`/receipts/${receiptIdA}`)

  // Should show not-found state, not receipt metadata
  // The detail card should NOT contain User A's stored filename reference
  await expect(page.locator('.detail-card')).not.toBeVisible()
})

// ── 7. User B API call to extract User A receipt returns 404 ──────────────────
test('User B direct API extract of User A receipt returns 404', async () => {
  const tokenB = await loginApi(emailB, password)
  const res = await fetch(`http://127.0.0.1:8000/api/receipts/${receiptIdA}/extract`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${tokenB}` },
  })
  expect(res.status).toBe(404)
})
