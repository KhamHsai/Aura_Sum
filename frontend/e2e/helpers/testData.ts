/**
 * Test data helpers for E2E tests.
 *
 * Uses unique timestamps so each test run creates fresh records.
 * All calls go directly to the real FastAPI backend.
 */

const API_BASE = 'http://127.0.0.1:8000/api'

/** Create a unique timestamp-based suffix for this test run. */
export function uniqueSuffix(): string {
  return Date.now().toString()
}

/** Build a unique test user email. */
export function testEmail(suffix: string): string {
  return `e2e-user-${suffix}@example.com`
}

/** Build a unique test username. */
export function testUsername(suffix: string): string {
  // Max 20 chars to stay under backend username limits
  return `e2e${suffix.slice(-10)}`
}

/** Fetch the first available category ID (needed to create expenses). */
export async function getFirstCategoryId(token: string): Promise<number> {
  const res = await fetch(`${API_BASE}/categories`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`Get categories failed: ${res.status}`)
  const cats = await res.json() as { id: number }[]
  if (cats.length === 0) throw new Error('No categories found — seed the E2E database first')
  return cats[0].id
}

export interface CreatedExpense {
  id: number
  title: string
  is_confirmed: boolean
}

/** Create a draft expense via the API for a given user. */
export async function createExpenseApi(
  token: string,
  title: string,
  categoryId: number,
  currency = 'THB',
  total = '100.00',
): Promise<CreatedExpense> {
  const today = new Date().toISOString().slice(0, 10)
  const body = {
    category_id: categoryId,
    title,
    receipt_date: today,
    currency,
    total_amount: total,
    items: [
      {
        original_name: 'Test Item',
        quantity: '1',
        total_price: total,
        discount_amount: '0',
      },
    ],
  }
  const res = await fetch(`${API_BASE}/expenses`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Create expense failed: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return { id: data.id as number, title: data.title as string, is_confirmed: data.is_confirmed as boolean }
}

/** Delete an expense via the API. */
export async function deleteExpenseApi(token: string, expenseId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/expenses/${expenseId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok && res.status !== 404) {
    throw new Error(`Delete expense failed: ${res.status}`)
  }
}

/** Upload a receipt via the API and return the receipt ID. */
export async function uploadReceiptApi(token: string, fileBytes: Uint8Array): Promise<number> {
  const formData = new FormData()
  formData.append('file', new Blob([fileBytes], { type: 'image/png' }), 'test-receipt.png')
  const res = await fetch(`${API_BASE}/receipts/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!res.ok) throw new Error(`Upload receipt failed: ${res.status} ${await res.text()}`)
  const data = await res.json()
  return data.id as number
}

/** Dismiss a SweetAlert2 popup by clicking its confirm button. */
export async function confirmSweetAlert(page: import('@playwright/test').Page): Promise<void> {
  const confirmBtn = page.locator('.swal2-confirm')
  await confirmBtn.waitFor({ state: 'visible', timeout: 8_000 })
  await confirmBtn.click()
  await confirmBtn.waitFor({ state: 'hidden', timeout: 5_000 })
}

/** Dismiss a SweetAlert2 popup by clicking its cancel button. */
export async function cancelSweetAlert(page: import('@playwright/test').Page): Promise<void> {
  const cancelBtn = page.locator('.swal2-cancel')
  await cancelBtn.waitFor({ state: 'visible', timeout: 8_000 })
  await cancelBtn.click()
  await cancelBtn.waitFor({ state: 'hidden', timeout: 5_000 })
}
