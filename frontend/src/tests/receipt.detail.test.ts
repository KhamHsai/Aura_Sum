/**
 * Receipt detail view tests.
 * All API calls are mocked — no real backend required.
 */
import { it, expect, describe, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import { defineComponent } from 'vue'
import en from '../locales/en.json'
import th from '../locales/th.json'
import type { Receipt } from '../types/receipt'

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('../api/authApi', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getCurrentUser: vi.fn(),
}))

vi.mock('../api/receiptApi', () => ({
  getReceipts: vi.fn(),
  getReceiptById: vi.fn(),
  uploadReceipt: vi.fn(),
  extractReceipt: vi.fn(),
}))

vi.mock('../utils/alerts', () => ({
  showSuccessAlert: vi.fn().mockResolvedValue(undefined),
  showErrorAlert: vi.fn().mockResolvedValue(undefined),
  showDeleteConfirmation: vi.fn().mockResolvedValue({ isConfirmed: false }),
}))

const mockPush = vi.fn()
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ push: mockPush }) }
})

import * as receiptApi from '../api/receiptApi'
import * as alerts from '../utils/alerts'

const mockGetReceiptById = vi.mocked(receiptApi.getReceiptById)
const mockExtractReceipt = vi.mocked(receiptApi.extractReceipt)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeReceipt: Receipt = {
  id: 3,
  user_id: 42,
  expense_id: null,
  original_filename: 'coffee_receipt.jpg',
  stored_filename: 'uuid-coffee.jpg',
  mime_type: 'image/jpeg',
  file_size: 51200,
  upload_status: 'uploaded',
  uploaded_at: '2024-06-01T12:00:00',
}

const fakeLinkedReceipt: Receipt = {
  ...fakeReceipt,
  id: 4,
  expense_id: 9,
  upload_status: 'extracted',
}

const fakeExpense = { id: 77 }

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountDetail(id: string | number, locale = 'en') {
  const { default: ReceiptDetailView } = await import('../views/ReceiptDetailView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/receipts', name: 'receipts', component: StubView },
      { path: '/receipts/:id', name: 'receipt-detail', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
      { path: '/expenses/:id/edit', name: 'expense-edit', component: StubView },
    ],
  })
  router.push(`/receipts/${id}`)
  await router.isReady()
  return mount(ReceiptDetailView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockPush.mockClear()
  mockShowSuccess.mockResolvedValue(undefined as never)
  mockShowError.mockResolvedValue(undefined as never)
})

// ── 1. Detail loads valid route ID ────────────────────────────────────────────
it('receipt detail calls getReceiptById with the correct id', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  await mountDetail(3)
  await flushPromises()
  expect(mockGetReceiptById).toHaveBeenCalledWith(3)
})

// ── 2. Invalid route ID handled ──────────────────────────────────────────────
it('receipt detail shows not-found for a non-numeric route id', async () => {
  const wrapper = await mountDetail('abc')
  await flushPromises()
  expect(mockGetReceiptById).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain(en.receipt_not_found)
})

// ── 3. 404 response handled ───────────────────────────────────────────────────
it('receipt detail shows not-found message on 404', async () => {
  mockGetReceiptById.mockRejectedValue({ response: { status: 404 } })
  const wrapper = await mountDetail(999)
  await flushPromises()
  expect(wrapper.text()).toContain(en.receipt_not_found)
})

// ── 4. Shows receipt metadata ─────────────────────────────────────────────────
it('receipt detail shows filename, mime type, and upload status', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  const wrapper = await mountDetail(3)
  await flushPromises()
  expect(wrapper.text()).toContain('coffee_receipt.jpg')
  expect(wrapper.text()).toContain('image/jpeg')
})

// ── 5. Shows Extract Receipt button when no linked expense ────────────────────
it('shows Extract Receipt button when expense_id is null', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  const wrapper = await mountDetail(3)
  await flushPromises()
  expect(wrapper.text()).toContain(en.extract_receipt)
})

// ── 6. Shows Open Expense button when linked ─────────────────────────────────
it('shows Open Expense when receipt has expense_id', async () => {
  mockGetReceiptById.mockResolvedValue(fakeLinkedReceipt)
  const wrapper = await mountDetail(4)
  await flushPromises()
  expect(wrapper.text()).toContain(en.open_expense)
})

// ── 7. Does not show Extract button when already linked ───────────────────────
it('does not show Extract Receipt button when receipt is already linked', async () => {
  mockGetReceiptById.mockResolvedValue(fakeLinkedReceipt)
  const wrapper = await mountDetail(4)
  await flushPromises()
  expect(wrapper.text()).not.toContain(en.extract_receipt)
})

// ── 8. Extract action calls extractReceipt ───────────────────────────────────
it('clicking Extract Receipt calls extractReceipt', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockResolvedValue(fakeExpense)

  const wrapper = await mountDetail(3)
  await flushPromises()

  const btn = wrapper.findAll('button').find((b) => b.text().includes(en.extract_receipt))
  expect(btn).toBeDefined()
  await btn!.trigger('click')
  await flushPromises()

  expect(mockExtractReceipt).toHaveBeenCalledWith(fakeReceipt.id)
})

// ── 9. Successful extraction redirects to expense edit ───────────────────────
it('successful extraction navigates to expense edit page', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockResolvedValue(fakeExpense)

  const wrapper = await mountDetail(3)
  await flushPromises()

  const btn = wrapper.findAll('button').find((b) => b.text().includes(en.extract_receipt))
  await btn!.trigger('click')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expense-edit', params: { id: 77 } })
})

// ── 10. Extraction failure shows error alert ──────────────────────────────────
it('extraction failure shows error alert', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockRejectedValue(new Error('Gemini error'))

  const wrapper = await mountDetail(3)
  await flushPromises()

  const btn = wrapper.findAll('button').find((b) => b.text().includes(en.extract_receipt))
  await btn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockPush).not.toHaveBeenCalled()
})

// ── 11. 503 Gemini error maps to safe message ─────────────────────────────────
it('503 Gemini error shows safe gemini not configured message', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockRejectedValue({ response: { status: 503, data: { detail: 'Gemini API key is not configured' } } })

  const wrapper = await mountDetail(3)
  await flushPromises()

  const btn = wrapper.findAll('button').find((b) => b.text().includes(en.extract_receipt))
  await btn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledWith(en.extraction_failed, en.gemini_not_configured)
})

// ── 12. Back to Receipts link ─────────────────────────────────────────────────
it('receipt detail shows Back to Receipts link', async () => {
  mockGetReceiptById.mockResolvedValue(fakeReceipt)
  const wrapper = await mountDetail(3)
  await flushPromises()
  expect(wrapper.text()).toContain(en.back_to_receipts)
})

// ── 13. Linked expense label shown ───────────────────────────────────────────
it('shows linked expense id in the linked_expense field', async () => {
  mockGetReceiptById.mockResolvedValue(fakeLinkedReceipt)
  const wrapper = await mountDetail(4)
  await flushPromises()
  expect(wrapper.text()).toContain(`${fakeLinkedReceipt.expense_id}`)
})

// ── 14. Network error state ───────────────────────────────────────────────────
it('receipt detail shows error when network request fails', async () => {
  mockGetReceiptById.mockRejectedValue(new Error('Network error'))
  const wrapper = await mountDetail(3)
  await flushPromises()
  expect(wrapper.text()).toContain(en.unable_to_connect)
})

// ── 15. Thai locale ───────────────────────────────────────────────────────────
describe('locale', () => {
  it('shows Thai not_found message for invalid id in th locale', async () => {
    const wrapper = await mountDetail('xyz', 'th')
    await flushPromises()
    expect(wrapper.text()).toContain(th.receipt_not_found)
  })
})
