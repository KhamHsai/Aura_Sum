/**
 * Receipt upload E2E tests.
 *
 * The upload step uses the real backend (file is stored on disk).
 * The extraction step (POST /api/receipts/{id}/extract) is MOCKED
 * because it calls Gemini — we must not consume real quota in automated tests.
 *
 * The mock returns an ExpenseResponse that matches the real schema so
 * the frontend can navigate to /expenses/{id}/edit as it normally would.
 * The mocked expense ID (999999) does not need to exist in the real DB
 * because we intercept the API call before it reaches the backend.
 */

import { test, expect, type Page } from '@playwright/test'
import { registerUserApi, loginAsUser } from './helpers/auth'
import { uniqueSuffix, testEmail, testUsername } from './helpers/testData'
import path from 'path'

const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

test.beforeAll(async () => {
  await registerUserApi(email, username, password)
})

/** Mock the extract endpoint to return a fake draft ExpenseResponse. */
async function mockExtractEndpoint(page: Page, expenseId: number): Promise<void> {
  const today = new Date().toISOString().slice(0, 10)
  await page.route('**/api/receipts/*/extract', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: expenseId,
        user_id: 1,
        category_id: 1,
        title: 'E2E AI Draft Expense',
        merchant_name: 'Mock Merchant',
        receipt_number: null,
        receipt_date: today,
        payment_method: null,
        currency: 'THB',
        subtotal: null,
        tax_amount: null,
        discount_amount: null,
        total_amount: '199.00',
        notes: null,
        is_confirmed: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        items: [],
      }),
    })
  })
}

// ── 1. Upload receipt → see preview ──────────────────────────────────────────
test('selecting an image file shows a preview before upload', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/receipts/upload')

  const fixturePath = path.resolve(__dirname, 'fixtures/test-receipt.png')
  await page.setInputFiles('#ru-file-input', fixturePath)

  // Image preview should appear
  await expect(page.locator('.image-preview')).toBeVisible()
  // The file name should be shown
  await expect(page.getByText('test-receipt.png')).toBeVisible()
})

// ── 2. Upload + mocked extract redirects to expense edit ─────────────────────
test('uploading a receipt with mocked extraction redirects to expense edit', async ({ page }) => {
  await loginAsUser(page, email, password)

  // We need a real receipt ID from the upload step so we can intercept extract.
  // We mock the extract endpoint to return expense id=999999.
  // We also need to intercept the edit page load for that fake ID.
  const fakeExpenseId = 999999

  // Mock extract endpoint
  await mockExtractEndpoint(page, fakeExpenseId)

  // Mock GET /api/expenses/999999 so the edit page does not 404
  const today = new Date().toISOString().slice(0, 10)
  await page.route(`**/api/expenses/${fakeExpenseId}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: fakeExpenseId,
        user_id: 1,
        category_id: 1,
        title: 'E2E AI Draft Expense',
        merchant_name: 'Mock Merchant',
        receipt_number: null,
        receipt_date: today,
        payment_method: null,
        currency: 'THB',
        subtotal: null,
        tax_amount: null,
        discount_amount: null,
        total_amount: '199.00',
        notes: null,
        is_confirmed: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        items: [],
      }),
    })
  })

  // Mock categories so the form can load
  await page.route('**/api/categories', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 1, name_en: 'Food', name_th: 'อาหาร', description: null },
      ]),
    })
  })

  await page.goto('/receipts/upload')

  const fixturePath = path.resolve(__dirname, 'fixtures/test-receipt.png')
  await page.setInputFiles('#ru-file-input', fixturePath)

  // Click the Upload & Extract button
  const submitBtn = page.locator('#ru-submit-btn')
  await submitBtn.click()

  // SweetAlert2 success popup after extraction
  const swalConfirm = page.locator('.swal2-confirm')
  await swalConfirm.waitFor({ state: 'visible', timeout: 15_000 })
  await swalConfirm.click()

  // Should redirect to /expenses/999999/edit
  await page.waitForURL(`**/expenses/${fakeExpenseId}/edit`, { timeout: 10_000 })
  await expect(page).toHaveURL(new RegExp(`/expenses/${fakeExpenseId}/edit`))
})

// ── 3. Invalid file type shows validation error ───────────────────────────────
test('selecting an unsupported file type shows a validation error', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/receipts/upload')

  // Attach a text file disguised as a different type — the frontend checks MIME
  // The browser may override the MIME when using setInputFiles, so we use a .txt file
  // which won't match the allowed MIME types list
  await page.setInputFiles('#ru-file-input', {
    name: 'bad-file.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('this is not a receipt'),
  })

  await expect(page.locator('.field-error')).toBeVisible()
})
