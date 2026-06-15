/**
 * Export button integration tests for ExpenseListView.
 * Covers button rendering, loading state, duplicate prevention,
 * success/error alert behaviour, and locale switching.
 * No real file download occurs — all APIs and browser helpers are mocked.
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
  getExpenseById: vi.fn(),
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
  confirmExpense: vi.fn(),
  translateExpense: vi.fn(),
  exportExpenses: vi.fn(),
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
import * as alerts from '../utils/alerts'
import * as downloadUtils from '../utils/download'

const mockGetExpenses = vi.mocked(expenseApi.getExpenses)
const mockExportExpenses = vi.mocked(expenseApi.exportExpenses)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)
const mockDownloadBlob = vi.mocked(downloadUtils.downloadBlob)
const mockParseBlobErrorMessage = vi.mocked(downloadUtils.parseBlobErrorMessage)

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeBlob = new Blob(['xlsx-data'], { type: XLSX_MIME })
const fakeContentDisposition = 'attachment; filename="smart_receipt_expenses_2024-06-14.xlsx"'

function makeExportResult(overrides: Partial<{ blob: Blob; contentDisposition: string | null; contentType: string | null }> = {}) {
  return {
    blob: fakeBlob,
    contentDisposition: fakeContentDisposition,
    contentType: XLSX_MIME,
    ...overrides,
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountList(locale = 'en') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/expenses', name: 'expenses', component: StubView },
      { path: '/expenses/new', name: 'expense-create', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
    ],
  })
  router.push('/expenses')
  await router.isReady()

  const { default: ExpenseListView } = await import('../views/ExpenseListView.vue')
  return mount(ExpenseListView, {
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
  // Default: parseBlobErrorMessage returns null (no parseable message)
  mockParseBlobErrorMessage.mockResolvedValue(null)
})

// ── 18. Export button appears on expense list ─────────────────────────────────
it('export button is rendered on the expense list', async () => {
  mockGetExpenses.mockResolvedValue([])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.export_excel)
})

// 19. Clicking export starts the API request
it('clicking Export Excel calls exportExpenses', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult())
  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))
  await exportBtn!.trigger('click')
  await flushPromises()

  expect(mockExportExpenses).toHaveBeenCalledOnce()
})

// 20. Button is disabled while exporting
it('export button is disabled while exporting', async () => {
  mockGetExpenses.mockResolvedValue([])
  // Never resolves — keeps isExporting true
  mockExportExpenses.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')

  await flushPromises()
  // After click but before resolution, the button text changes and it is disabled
  expect(wrapper.text()).toContain(en.exporting)
  expect(exportBtn.attributes('disabled')).toBeDefined()
})

// 21. Duplicate export clicks are prevented
it('duplicate clicks do not start a second export', async () => {
  mockGetExpenses.mockResolvedValue([])
  let resolveExport!: (v: ReturnType<typeof makeExportResult>) => void
  mockExportExpenses.mockReturnValue(new Promise((res) => { resolveExport = res }))

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  // Click twice rapidly
  await exportBtn.trigger('click')
  await exportBtn.trigger('click')
  await flushPromises()

  // Only one API call, not two
  expect(mockExportExpenses).toHaveBeenCalledOnce()

  // Clean up
  resolveExport(makeExportResult())
  await flushPromises()
})

// 22. Valid Blob starts download
it('valid blob triggers downloadBlob', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult())

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockDownloadBlob).toHaveBeenCalledOnce()
})

// 23. Success alert is shown after download
it('shows success alert after a successful export', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult())

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledOnce()
  expect(mockShowSuccess).toHaveBeenCalledWith(en.export_completed, en.export_completed_message)
})

// 24. Empty Blob shows error alert
it('shows error alert when blob is empty', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue({
    blob: new Blob([]),   // size 0
    contentDisposition: fakeContentDisposition,
    contentType: XLSX_MIME,
  })

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockDownloadBlob).not.toHaveBeenCalled()
})

// 25. Missing filename uses fallback
it('uses the fallback filename when Content-Disposition is missing', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult({ contentDisposition: null }))

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockDownloadBlob).toHaveBeenCalledWith(fakeBlob, FALLBACK_FILENAME)
})

// 26. Backend JSON error Blob is parsed safely
it('parses a JSON error blob and shows a safe error message', async () => {
  mockGetExpenses.mockResolvedValue([])
  const errorBlob = new Blob([JSON.stringify({ detail: 'Export generation failed' })], { type: 'application/json' })
  mockExportExpenses.mockRejectedValue({ response: { data: errorBlob } })
  mockParseBlobErrorMessage.mockResolvedValue('Export generation failed')

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockShowError.mock.calls[0][0]).toBe(en.unable_to_export_expenses)
  // The parsed message is shown, not the generic fallback
  expect(mockShowError.mock.calls[0][1]).toBe('Export generation failed')
})

// 27. FastAPI array error is parsed safely
it('shows a safe error message for a FastAPI array error blob', async () => {
  mockGetExpenses.mockResolvedValue([])
  const errorBlob = new Blob(
    [JSON.stringify({ detail: [{ loc: ['body'], msg: 'invalid request', type: 'value_error' }] })],
    { type: 'application/json' },
  )
  mockExportExpenses.mockRejectedValue({ response: { data: errorBlob } })
  mockParseBlobErrorMessage.mockResolvedValue('invalid request')

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockShowError.mock.calls[0][1]).toBe('invalid request')
})

// 28. Invalid JSON blob uses generic message
it('uses generic error message when error blob is not JSON', async () => {
  mockGetExpenses.mockResolvedValue([])
  const errorBlob = new Blob(['internal server error'], { type: 'text/plain' })
  mockExportExpenses.mockRejectedValue({ response: { data: errorBlob } })
  // parseBlobErrorMessage returns null → view uses the generic fallback
  mockParseBlobErrorMessage.mockResolvedValue(null)

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockShowError.mock.calls[0][1]).toBe(en.export_failed_message)
})

// 29. Network failure shows safe error alert
it('shows an error alert on network failure', async () => {
  mockGetExpenses.mockResolvedValue([])
  // A plain Error has no response.data blob — goes straight to generic message
  mockExportExpenses.mockRejectedValue(new Error('Network Error'))

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockShowError.mock.calls[0][0]).toBe(en.unable_to_export_expenses)
})

// 30. No real file download occurs in tests (downloadBlob is mocked)
it('downloadBlob mock prevents real file writes during tests', async () => {
  mockGetExpenses.mockResolvedValue([])
  mockExportExpenses.mockResolvedValue(makeExportResult())

  const wrapper = await mountList()
  await flushPromises()

  const exportBtn = wrapper.findAll('button').find((b) => b.text().includes(en.export_excel))!
  await exportBtn.trigger('click')
  await flushPromises()

  // Mock was called — no real browser download
  expect(mockDownloadBlob).toHaveBeenCalledOnce()
})

// 31. English labels render
it('export button shows English label in English locale', async () => {
  mockGetExpenses.mockResolvedValue([])
  const wrapper = await mountList('en')
  await flushPromises()
  expect(wrapper.text()).toContain(en.export_excel)
})

// 32. Thai labels render
it('export button shows Thai label in Thai locale', async () => {
  mockGetExpenses.mockResolvedValue([])
  const wrapper = await mountList('th')
  await flushPromises()
  expect(wrapper.text()).toContain(th.export_excel)
})

// 33. Existing expense list tests still work (smoke check)
describe('existing list features unaffected', () => {
  it('still loads and displays expenses', async () => {
    mockGetExpenses.mockResolvedValue([
      {
        id: 1, user_id: 1, category_id: 1, category_name: 'Food', paid_to: 'Coffee Shop',
        tax_id: null, receipt_number: null, receipt_date: '2024-01-01', receipt_time: null,
        payment_method: 'Cash', currency: 'THB', subtotal: null, tax_amount: null,
        discount_amount: null, total_amount: '50.00', notes: null, is_confirmed: false,
        created_at: '2024-01-01T00:00:00', updated_at: '2024-01-01T00:00:00', items: [],
      },
    ])
    const wrapper = await mountList()
    await flushPromises()
    expect(wrapper.text()).toContain('Coffee Shop')
  })

  it('still shows the Add Expense button', async () => {
    mockGetExpenses.mockResolvedValue([])
    const wrapper = await mountList()
    await flushPromises()
    expect(wrapper.text()).toContain(en.add_expense)
  })
})
