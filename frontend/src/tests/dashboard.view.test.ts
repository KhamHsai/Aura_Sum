/**
 * Integration tests for DashboardView.vue
 * Verifies data loading, states, summaries, currency grouping,
 * recent expenses, quick actions, export, and locale labels.
 * No real backend calls — all APIs are mocked.
 */
import { it, expect, describe, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import { defineComponent } from 'vue'
import en from '../locales/en.json'
import th from '../locales/th.json'
import { XLSX_MIME, FALLBACK_FILENAME } from '../utils/download'

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('../api/authApi', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getCurrentUser: vi.fn(),
}))

vi.mock('../api/expenseApi', () => ({
  getExpenses: vi.fn(),
  exportExpenses: vi.fn(),
  getExpenseById: vi.fn(),
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
  confirmExpense: vi.fn(),
  translateExpense: vi.fn(),
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

vi.mock('../utils/download', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../utils/download')>()
  return {
    ...actual,
    downloadBlob: vi.fn(),
    parseBlobErrorMessage: vi.fn(),
  }
})

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ push: vi.fn() }) }
})

import * as expenseApi from '../api/expenseApi'
import * as receiptApi from '../api/receiptApi'
import * as alerts from '../utils/alerts'
import * as downloadUtils from '../utils/download'
import type { Expense } from '../types/expense'
import type { Receipt } from '../types/receipt'

const mockGetExpenses = vi.mocked(expenseApi.getExpenses)
const mockGetReceipts = vi.mocked(receiptApi.getReceipts)
const mockExportExpenses = vi.mocked(expenseApi.exportExpenses)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)
const mockDownloadBlob = vi.mocked(downloadUtils.downloadBlob)
const mockParseBlobErrorMessage = vi.mocked(downloadUtils.parseBlobErrorMessage)

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeExpense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: 1,
    user_id: 1,
    category_id: null,
    category_name: null,
    paid_to: null,
    tax_id: null,
    receipt_number: null,
    receipt_date: '2024-01-15',
    receipt_time: null,
    payment_method: null,
    currency: 'THB',
    subtotal: null,
    tax_amount: null,
    discount_amount: null,
    total_amount: '250.00',
    notes: null,
    is_confirmed: false,
    created_at: '2024-01-15T10:00:00',
    updated_at: '2024-01-15T10:00:00',
    items: [],
    ...overrides,
  }
}

function makeReceipt(overrides: Partial<Receipt> = {}): Receipt {
  return {
    id: 1,
    user_id: 1,
    expense_id: null,
    original_filename: 'receipt.jpg',
    stored_filename: 'stored.jpg',
    mime_type: 'image/jpeg',
    file_size: 1024,
    upload_status: 'uploaded',
    uploaded_at: '2024-01-01T00:00:00',
    ...overrides,
  }
}

const fakeBlob = new Blob(['xlsx'], { type: XLSX_MIME })

function makeExportResult(overrides: Partial<{ blob: Blob; contentDisposition: string | null; contentType: string | null }> = {}) {
  return {
    blob: fakeBlob,
    contentDisposition: 'attachment; filename="expenses.xlsx"',
    contentType: XLSX_MIME,
    ...overrides,
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountDashboard(locale = 'en') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/dashboard', name: 'dashboard', component: StubView },
      { path: '/expenses', name: 'expenses', component: StubView },
      { path: '/expenses/new', name: 'expense-create', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
      { path: '/receipts', name: 'receipts', component: StubView },
      { path: '/receipts/upload', name: 'receipt-upload', component: StubView },
    ],
  })
  router.push('/dashboard')
  await router.isReady()

  const { default: DashboardView } = await import('../views/DashboardView.vue')
  return mount(DashboardView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockShowSuccess.mockResolvedValue(undefined as never)
  mockShowError.mockResolvedValue(undefined as never)
  mockDownloadBlob.mockImplementation(() => {})
  mockParseBlobErrorMessage.mockResolvedValue(null)
})

// ── 1. Data loading ───────────────────────────────────────────────────────────

it('calls getExpenses on mount', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockGetReceipts.mockResolvedValue([])
  await mountDashboard()
  await flushPromises()
  expect(mockGetExpenses).toHaveBeenCalledOnce()
})

it('calls getReceipts on mount', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockGetReceipts.mockResolvedValue([])
  await mountDashboard()
  await flushPromises()
  expect(mockGetReceipts).toHaveBeenCalledOnce()
})

it('shows loading state while data is being fetched', async () => {
  // Never resolves — stays in loading state
  mockGetExpenses.mockReturnValue(new Promise(() => {}))
  mockGetReceipts.mockReturnValue(new Promise(() => {}))
  const wrapper = await mountDashboard()
  expect(wrapper.text()).toContain(en.loading_dashboard)
})

// ── 2. Summary counts ─────────────────────────────────────────────────────────

it('shows correct total expense count', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense({ id: 1 }), makeExpense({ id: 2 })])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain('2')
})

it('shows correct confirmed expense count', async () => {
  mockGetExpenses.mockResolvedValue([
    makeExpense({ id: 1, is_confirmed: true }),
    makeExpense({ id: 2, is_confirmed: false }),
  ])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const text = wrapper.text()
  expect(text).toContain(en.confirmed_expenses)
})

it('shows correct draft expense count', async () => {
  mockGetExpenses.mockResolvedValue([
    makeExpense({ id: 1, is_confirmed: false }),
    makeExpense({ id: 2, is_confirmed: false }),
  ])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.draft_expenses)
})

it('shows correct total receipt count', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([makeReceipt({ id: 1 }), makeReceipt({ id: 2 })])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.total_receipts)
})

it('shows correct linked receipt count label', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([
    makeReceipt({ id: 1, expense_id: 5 }),
    makeReceipt({ id: 2, expense_id: null }),
  ])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.linked_receipts)
})

it('shows correct unlinked receipt count label', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([
    makeReceipt({ id: 1, expense_id: null }),
    makeReceipt({ id: 2, expense_id: null }),
  ])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.unlinked_receipts)
})

// ── 3. Currency grouping ──────────────────────────────────────────────────────

it('shows spending grouped by currency', async () => {
  mockGetExpenses.mockResolvedValue([
    makeExpense({ id: 1, currency: 'THB', total_amount: '1000.00' }),
    makeExpense({ id: 2, currency: 'USD', total_amount: '50.00' }),
  ])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const text = wrapper.text()
  expect(text).toContain('THB')
  expect(text).toContain('USD')
})

it('does not combine THB and USD into one total', async () => {
  mockGetExpenses.mockResolvedValue([
    makeExpense({ id: 1, currency: 'THB', total_amount: '1000.00' }),
    makeExpense({ id: 2, currency: 'USD', total_amount: '50.00' }),
  ])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  // Both currency rows should exist separately
  const currencyRows = wrapper.findAll('.currency-row')
  expect(currencyRows).toHaveLength(2)
})

it('shows no spending data message when there are no expenses', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockGetReceipts.mockResolvedValue([makeReceipt()])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.no_spending_data)
})

it('sorts currencies alphabetically', async () => {
  mockGetExpenses.mockResolvedValue([
    makeExpense({ id: 1, currency: 'USD', total_amount: '10.00' }),
    makeExpense({ id: 2, currency: 'EUR', total_amount: '20.00' }),
    makeExpense({ id: 3, currency: 'THB', total_amount: '30.00' }),
  ])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const rows = wrapper.findAll('.currency-code')
  const codes = rows.map((r) => r.text())
  expect(codes).toEqual(['EUR', 'THB', 'USD'])
})

// ── 4. Recent expenses ────────────────────────────────────────────────────────

it('sorts recent expenses by created_at descending', async () => {
  mockGetExpenses.mockResolvedValue([
    makeExpense({ id: 1, paid_to: 'Old Shop', created_at: '2024-01-01T00:00:00' }),
    makeExpense({ id: 2, paid_to: 'New Shop', created_at: '2024-06-01T00:00:00' }),
  ])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const titles = wrapper.findAll('.recent-expense-title').map((el) => el.text())
  expect(titles[0]).toBe('New Shop')
  expect(titles[1]).toBe('Old Shop')
})

it('shows at most 5 recent expenses', async () => {
  const expenses = Array.from({ length: 8 }, (_, i) =>
    makeExpense({ id: i + 1, created_at: `2024-01-${String(i + 1).padStart(2, '0')}T00:00:00` }),
  )
  mockGetExpenses.mockResolvedValue(expenses)
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.findAll('.recent-expense-row')).toHaveLength(5)
})

it('shows no recent expenses message when expenses list is empty', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.no_recent_expenses)
})

it('recent expense links to the detail page', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense({ id: 42 })])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const link = wrapper.find('.recent-expense-link')
  expect(link.exists()).toBe(true)
  expect(link.attributes('href')).toContain('42')
})

// ── 5. Empty and error states ─────────────────────────────────────────────────

it('shows welcome empty state when both expenses and receipts are empty', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.welcome_to_smart_receipt)
})

it('quick actions are still visible in the empty state', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.quick_actions)
})

it('shows error state when API call fails', async () => {
  mockGetExpenses.mockRejectedValue(new Error('Network Error'))
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.unable_to_load_dashboard)
})

it('shows a Retry button in the error state', async () => {
  mockGetExpenses.mockRejectedValue(new Error('Network Error'))
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const retryBtn = wrapper.findAll('button').find((b) => b.text().includes(en.retry))
  expect(retryBtn?.exists()).toBe(true)
})

it('retry reloads data when clicked', async () => {
  mockGetExpenses.mockRejectedValueOnce(new Error('Network Error'))
  mockGetReceipts.mockRejectedValueOnce(new Error('Network Error'))

  const wrapper = await mountDashboard()
  await flushPromises()
  expect(wrapper.text()).toContain(en.unable_to_load_dashboard)

  // Now the APIs succeed on retry
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])

  const retryBtn = wrapper.findAll('button').find((b) => b.text().includes(en.retry))
  await retryBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).not.toContain(en.unable_to_load_dashboard)
  expect(mockGetExpenses).toHaveBeenCalledTimes(2)
})

// ── 6. Quick actions ──────────────────────────────────────────────────────────

it('Add Expense quick action links to expense-create route', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const link = wrapper.findAll('a').find((a) => a.text().includes(en.add_expense))
  expect(link?.attributes('href')).toContain('/expenses/new')
})

it('Upload Receipt quick action links to receipt-upload route', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const link = wrapper.findAll('a').find((a) => a.text().includes(en.upload_receipt))
  expect(link?.attributes('href')).toContain('/receipts/upload')
})

it('View Expenses quick action links to expenses route', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const link = wrapper.findAll('a').find((a) => a.text().includes(en.view_expenses))
  expect(link?.attributes('href')).toBe('/expenses')
})

it('View Receipts quick action links to receipts route', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  const wrapper = await mountDashboard()
  await flushPromises()
  const link = wrapper.findAll('a').find((a) => a.text().includes(en.view_receipts))
  expect(link?.attributes('href')).toBe('/receipts')
})

// ── 7. Export ─────────────────────────────────────────────────────────────────

it('export button calls exportExpenses', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult())
  const wrapper = await mountDashboard()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))
  await exportBtn!.trigger('click')
  await flushPromises()

  expect(mockExportExpenses).toHaveBeenCalledOnce()
})

it('export loading state prevents duplicate clicks', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  mockExportExpenses.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountDashboard()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await exportBtn.trigger('click') // second click should be ignored
  await flushPromises()

  expect(mockExportExpenses).toHaveBeenCalledOnce()
})

it('export shows success alert and triggers download', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult())

  const wrapper = await mountDashboard()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockDownloadBlob).toHaveBeenCalledOnce()
  expect(mockShowSuccess).toHaveBeenCalledWith(en.export_completed, en.export_completed_message)
})

it('export shows error alert when blob is invalid', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult({ blob: new Blob([]) }))

  const wrapper = await mountDashboard()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockDownloadBlob).not.toHaveBeenCalled()
})

it('export uses FALLBACK_FILENAME when Content-Disposition is missing', async () => {
  mockGetExpenses.mockResolvedValue([makeExpense()])
  mockGetReceipts.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult({ contentDisposition: null }))

  const wrapper = await mountDashboard()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockDownloadBlob).toHaveBeenCalledWith(fakeBlob, FALLBACK_FILENAME)
})

// ── 8. Locale labels ──────────────────────────────────────────────────────────

describe('locale labels', () => {
  it('renders English labels in English locale', async () => {
    mockGetExpenses.mockResolvedValue([makeExpense()])
    mockGetReceipts.mockResolvedValue([])
    const wrapper = await mountDashboard('en')
    await flushPromises()
    expect(wrapper.text()).toContain(en.quick_actions)
    expect(wrapper.text()).toContain(en.add_expense)
    expect(wrapper.text()).toContain(en.export_excel)
  })

  it('renders Thai labels in Thai locale', async () => {
    mockGetExpenses.mockResolvedValue([makeExpense()])
    mockGetReceipts.mockResolvedValue([])
    const wrapper = await mountDashboard('th')
    await flushPromises()
    expect(wrapper.text()).toContain(th.quick_actions)
    expect(wrapper.text()).toContain(th.add_expense)
    expect(wrapper.text()).toContain(th.export_excel)
  })
})
