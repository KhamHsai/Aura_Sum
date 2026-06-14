/**
 * Error-handling smoke tests.
 *
 * Uses Playwright route interception to simulate server errors
 * without touching the real backend data or Gemini.
 *
 * Verifies that error messages are safe — no stack traces,
 * API keys, file paths, or raw database errors.
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
} from './helpers/testData'

const suffix = uniqueSuffix()
const email = testEmail(suffix)
const username = testUsername(suffix)
const password = 'Password123!'

test.beforeAll(async () => {
  await registerUserApi(email, username, password)
})

/** Assert that the visible page text does not contain dangerous content. */
async function expectSafePageContent(page: import('@playwright/test').Page): Promise<void> {
  const body = await page.locator('body').textContent()
  expect(body).not.toContain('Traceback')
  expect(body).not.toContain('sqlalchemy')
  expect(body).not.toContain('GEMINI_API_KEY')
  expect(body).not.toContain('uploads/receipts')
  expect(body).not.toContain('Exception')
  expect(body).not.toContain('password_hash')
}

// ── 1. Invalid expense ID shows not-found, not a stack trace ─────────────────
test('navigating to an invalid expense ID shows safe not-found message', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/expenses/999999999')

  // Should show a not-found error element
  await expect(page.locator('.alert-error')).toBeVisible()
  await expectSafePageContent(page)
})

// ── 2. Invalid receipt ID shows not-found safely ─────────────────────────────
test('navigating to an invalid receipt ID shows safe not-found message', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/receipts/999999999')

  await expect(page.locator('.alert-error')).toBeVisible()
  await expectSafePageContent(page)
})

// ── 3. Backend 500 on expense list shows safe error ──────────────────────────
test('a 500 response from the expense list API shows a safe error message', async ({ page }) => {
  await loginAsUser(page, email, password)

  // Intercept the expenses list request and return a 500
  await page.route('**/api/expenses', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      })
    } else {
      await route.continue()
    }
  })

  await page.goto('/expenses')

  await expect(page.locator('.alert-error')).toBeVisible()
  await expectSafePageContent(page)
})

// ── 4. Gemini not configured (503) on extraction shows safe message ───────────
test('Gemini not configured shows a safe error on the upload page', async ({ page }) => {
  await loginAsUser(page, email, password)

  // Mock upload to succeed, extract to return 503
  const today = new Date().toISOString().slice(0, 10)
  await page.route('**/api/receipts/upload', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 1,
        user_id: 1,
        expense_id: null,
        original_filename: 'test-receipt.png',
        stored_filename: 'abc.png',
        mime_type: 'image/png',
        file_size: 69,
        upload_status: 'uploaded',
        uploaded_at: new Date().toISOString(),
      }),
    })
  })
  await page.route('**/api/receipts/*/extract', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Gemini not configured' }),
    })
  })

  await page.goto('/receipts/upload')

  const { default: path } = await import('path')
  const fixturePath = path.resolve(__dirname, 'fixtures/test-receipt.png')
  await page.setInputFiles('#ru-file-input', fixturePath)
  await page.locator('#ru-submit-btn').click()

  // SweetAlert2 error popup should appear
  const swalPopup = page.locator('.swal2-popup')
  await expect(swalPopup).toBeVisible({ timeout: 10_000 })

  // Message should NOT contain API key details
  const popupText = await swalPopup.textContent()
  expect(popupText).not.toContain('GEMINI_API_KEY')
  expect(popupText).not.toContain('Traceback')
  // Should contain the safe mapped message
  expect(popupText?.length).toBeGreaterThan(0)

  // Dismiss the alert
  await page.locator('.swal2-confirm').click()
})

// ── 5. Gemini quota exceeded (429) shows safe message ────────────────────────
test('Gemini quota exceeded shows a safe error on the upload page', async ({ page }) => {
  await loginAsUser(page, email, password)

  await page.route('**/api/receipts/upload', async (route) => {
    await route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 2, user_id: 1, expense_id: null,
        original_filename: 'test-receipt.png', stored_filename: 'abc.png',
        mime_type: 'image/png', file_size: 69,
        upload_status: 'uploaded', uploaded_at: new Date().toISOString(),
      }),
    })
  })
  await page.route('**/api/receipts/*/extract', async (route) => {
    await route.fulfill({
      status: 429,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Gemini quota exceeded' }),
    })
  })

  await page.goto('/receipts/upload')
  const { default: path } = await import('path')
  const fixturePath = path.resolve(__dirname, 'fixtures/test-receipt.png')
  await page.setInputFiles('#ru-file-input', fixturePath)
  await page.locator('#ru-submit-btn').click()

  const swalPopup = page.locator('.swal2-popup')
  await expect(swalPopup).toBeVisible({ timeout: 10_000 })
  const popupText = await swalPopup.textContent()
  expect(popupText).not.toContain('AIzaSy')  // typical Gemini key prefix
  expect(popupText).not.toContain('Traceback')
  await page.locator('.swal2-confirm').click()
})

// ── 6. Translation service failure (503) shows safe message ──────────────────
test('translation service failure shows a safe error, not a stack trace', async ({ page }) => {
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const expense = await createExpenseApi(token, 'E2E Error Translation Test', catId)

  await loginAsUser(page, email, password)

  // Mock translate to return 503
  await page.route(`**/api/expenses/${expense.id}/translate`, async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Translation service unavailable' }),
    })
  })

  await page.goto(`/expenses/${expense.id}`)
  await page.locator('#target-language-select').selectOption('th')
  await page.getByRole('button', { name: /^translate$/i }).click()

  // SweetAlert2 error popup
  const swalPopup = page.locator('.swal2-popup')
  await expect(swalPopup).toBeVisible({ timeout: 10_000 })
  const popupText = await swalPopup.textContent()
  expect(popupText).not.toContain('Traceback')
  expect(popupText).not.toContain('GEMINI_API_KEY')
  await page.locator('.swal2-confirm').click()
})

// ── 7. Unsupported file type shows client-side validation error ───────────────
test('uploading an unsupported file type shows a validation error, not a server error', async ({ page }) => {
  await loginAsUser(page, email, password)
  await page.goto('/receipts/upload')

  await page.setInputFiles('#ru-file-input', {
    name: 'script.js',
    mimeType: 'application/javascript',
    buffer: Buffer.from('alert(1)'),
  })

  // Client-side validation error should appear, never reaching the server
  await expect(page.locator('.field-error')).toBeVisible()
  await expectSafePageContent(page)
})
