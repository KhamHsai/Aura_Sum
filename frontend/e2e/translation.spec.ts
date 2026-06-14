/**
 * Translation E2E tests.
 *
 * POST /api/expenses/{id}/translate calls Gemini, so we mock it here.
 * The mock response matches the real ExpenseTranslationResponse schema.
 *
 * The expense itself is real (created via API).
 * Normal expense loading (GET /api/expenses/{id}) is NOT mocked.
 */

import { test, expect } from '@playwright/test'
import { registerUserApi, loginAsUser, loginApi } from './helpers/auth'
import {
  uniqueSuffix,
  testEmail,
  testUsername,
  getFirstCategoryId,
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

/** Mock the translate endpoint with a realistic response. */
async function mockTranslateEndpoint(page: import('@playwright/test').Page, expenseId: number): Promise<void> {
  await page.route(`**/api/expenses/${expenseId}/translate`, async (route) => {
    const body = await route.request().postDataJSON() as { target_language: string }
    const isToThai = body.target_language === 'th'
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        expense_id: expenseId,
        source_language: isToThai ? 'en' : 'th',
        target_language: isToThai ? 'th' : 'en',
        translated_title: isToThai ? 'ค่าใช้จ่ายทดสอบ E2E' : 'E2E Test Expense',
        translated_notes: null,
        items: [
          {
            item_id: 1,
            original_name: 'Test Item',
            name_en: 'Test Item',
            name_th: 'สินค้าทดสอบ',
            translated_name: isToThai ? 'สินค้าทดสอบ' : 'Test Item',
          },
        ],
        reused_existing_translation: false,
      }),
    })
  })
}

// ── 1. Translate to Thai ──────────────────────────────────────────────────────
test('translate expense to Thai shows translated title and item', async ({ page }) => {
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const today = new Date().toISOString().slice(0, 10)

  // Create expense with an item (item IDs are assigned by the backend)
  const createRes = await fetch('http://127.0.0.1:8000/api/expenses', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category_id: catId,
      title: 'E2E Translation Test',
      receipt_date: today,
      currency: 'THB',
      total_amount: '100.00',
      items: [
        {
          original_name: 'Test Item',
          name_en: 'Test Item',
          name_th: null,
          quantity: '1',
          total_price: '100.00',
          discount_amount: '0',
        },
      ],
    }),
  })
  const expense = await createRes.json() as { id: number }

  await mockTranslateEndpoint(page, expense.id)

  await loginAsUser(page, email, password)
  await page.goto(`/expenses/${expense.id}`)

  // Select Thai as target language
  await page.locator('#target-language-select').selectOption('th')

  // Click Translate
  await page.getByRole('button', { name: /^translate$/i }).click()

  // Loading state appears briefly
  await expect(page.getByText(/translating/i)).toBeVisible()

  // Wait for the success alert and dismiss it
  await confirmSweetAlert(page)

  // Translated title should appear
  await expect(page.getByText('ค่าใช้จ่ายทดสอบ E2E')).toBeVisible()

  // Original title still visible
  await expect(page.getByText('E2E Translation Test')).toBeVisible()

  // Translated item name should appear
  await expect(page.getByText('สินค้าทดสอบ')).toBeVisible()
})

// ── 2. Translate to English ───────────────────────────────────────────────────
test('translate expense to English shows English translated title', async ({ page }) => {
  const token = await loginApi(email, password)
  const catId = await getFirstCategoryId(token)
  const today = new Date().toISOString().slice(0, 10)

  const createRes = await fetch('http://127.0.0.1:8000/api/expenses', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      category_id: catId,
      title: 'ค่าใช้จ่าย EN Test',
      receipt_date: today,
      currency: 'THB',
      total_amount: '50.00',
      items: [
        {
          original_name: 'Test Item',
          name_en: 'Test Item',
          name_th: null,
          quantity: '1',
          total_price: '50.00',
          discount_amount: '0',
        },
      ],
    }),
  })
  const expense = await createRes.json() as { id: number }

  await mockTranslateEndpoint(page, expense.id)

  await loginAsUser(page, email, password)
  await page.goto(`/expenses/${expense.id}`)

  await page.locator('#target-language-select').selectOption('en')
  await page.getByRole('button', { name: /^translate$/i }).click()

  await confirmSweetAlert(page)

  // The English translated title appears in the result panel
  await expect(page.getByText('E2E Test Expense')).toBeVisible()
})
