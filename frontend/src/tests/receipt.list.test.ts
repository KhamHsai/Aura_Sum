/**
 * Receipt list view tests.
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

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ push: vi.fn() }) }
})

import * as receiptApi from '../api/receiptApi'
const mockGetReceipts = vi.mocked(receiptApi.getReceipts)

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeReceipt: Receipt = {
  id: 1,
  user_id: 42,
  expense_id: null,
  original_filename: 'lunch_receipt.jpg',
  stored_filename: 'uuid-lunch.jpg',
  mime_type: 'image/jpeg',
  file_size: 204800,
  upload_status: 'uploaded',
  uploaded_at: '2024-06-01T10:00:00',
}

const fakeLinkedReceipt: Receipt = {
  ...fakeReceipt,
  id: 2,
  original_filename: 'dinner.pdf',
  mime_type: 'application/pdf',
  upload_status: 'extracted',
  expense_id: 7,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountList(locale = 'en') {
  const { default: ReceiptListView } = await import('../views/ReceiptListView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/receipts', name: 'receipts', component: StubView },
      { path: '/receipts/upload', name: 'receipt-upload', component: StubView },
      { path: '/receipts/:id', name: 'receipt-detail', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
    ],
  })
  router.push('/receipts')
  await router.isReady()
  return mount(ReceiptListView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ── 1. List API calls /receipts ───────────────────────────────────────────────
it('receipt list calls getReceipts on mount', async () => {
  mockGetReceipts.mockResolvedValue([])
  await mountList()
  await flushPromises()
  expect(mockGetReceipts).toHaveBeenCalledOnce()
})

// ── 2. Loading state ──────────────────────────────────────────────────────────
it('receipt list shows loading text while fetching', async () => {
  mockGetReceipts.mockReturnValue(new Promise(() => {}))
  const wrapper = await mountList()
  expect(wrapper.text()).toContain(en.loading_receipts)
})

// ── 3. Displays receipt data ──────────────────────────────────────────────────
it('receipt list displays receipt filenames', async () => {
  mockGetReceipts.mockResolvedValue([fakeReceipt, fakeLinkedReceipt])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain('lunch_receipt.jpg')
  expect(wrapper.text()).toContain('dinner.pdf')
})

// ── 4. Empty state ────────────────────────────────────────────────────────────
it('receipt list shows empty state when no receipts', async () => {
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.no_receipts_found)
  expect(wrapper.text()).toContain(en.no_receipts_subtitle)
})

// ── 5. Error state ────────────────────────────────────────────────────────────
it('receipt list shows error message when fetch fails', async () => {
  mockGetReceipts.mockRejectedValue(new Error('Network error'))
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.unable_to_load_receipts)
})

// ── 6. Error state shows Retry button ────────────────────────────────────────
it('receipt list shows Retry button on error', async () => {
  mockGetReceipts.mockRejectedValue(new Error('Network error'))
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.retry)
})

// ── 7. View Receipt link ──────────────────────────────────────────────────────
it('receipt list renders a View Receipt link for each receipt', async () => {
  mockGetReceipts.mockResolvedValue([fakeReceipt])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.view_receipt)
})

// ── 8. Open Expense link shown when linked ────────────────────────────────────
it('receipt list shows Open Expense link when receipt has expense_id', async () => {
  mockGetReceipts.mockResolvedValue([fakeLinkedReceipt])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.open_expense)
})

// ── 9. No Open Expense link when unlinked ────────────────────────────────────
it('receipt list does not show Open Expense when receipt has no expense', async () => {
  mockGetReceipts.mockResolvedValue([fakeReceipt])
  const wrapper = await mountList()
  await flushPromises()
  // view_receipt link should be there but open_expense should not
  expect(wrapper.text()).toContain(en.view_receipt)
  // fakeReceipt has expense_id null, so Open Expense should not appear
  const links = wrapper.findAll('a')
  const openExpenseLinks = links.filter((l) => l.attributes('href')?.includes('/expenses/'))
  expect(openExpenseLinks).toHaveLength(0)
})

// ── 10. Upload Receipt link in header ─────────────────────────────────────────
it('receipt list shows Upload Receipt link', async () => {
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.upload_receipt)
})

// ── 11. File size displayed in human-readable form ────────────────────────────
it('receipt list displays file size in KB or MB', async () => {
  mockGetReceipts.mockResolvedValue([fakeReceipt])
  const wrapper = await mountList()
  await flushPromises()
  // 204800 bytes = 200.0 KB
  expect(wrapper.text()).toContain('KB')
})

// ── 12. Mime type shown ───────────────────────────────────────────────────────
it('receipt list displays mime type', async () => {
  mockGetReceipts.mockResolvedValue([fakeReceipt])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain('image/jpeg')
})

// ── 13. Thai locale ───────────────────────────────────────────────────────────
describe('locale', () => {
  it('shows Thai empty state when locale is th', async () => {
    mockGetReceipts.mockResolvedValue([])
    const wrapper = await mountList('th')
    await flushPromises()
    expect(wrapper.text()).toContain(th.no_receipts_found)
  })

  it('shows Thai loading text when locale is th', async () => {
    mockGetReceipts.mockReturnValue(new Promise(() => {}))
    const wrapper = await mountList('th')
    expect(wrapper.text()).toContain(th.loading_receipts)
  })
})
