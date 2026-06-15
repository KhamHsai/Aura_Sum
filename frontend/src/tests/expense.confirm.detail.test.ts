/**
 * Expense confirmation flow tests — detail page.
 * Covers confirm button visibility, dialog, success, failure, and state updates.
 * SweetAlert2, API calls, and router are all mocked.
 */
import { it, expect, describe, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import { defineComponent } from 'vue'
import en from '../locales/en.json'
import th from '../locales/th.json'

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
}))

vi.mock('../utils/alerts', () => ({
  showSuccessAlert: vi.fn().mockResolvedValue(undefined),
  showErrorAlert: vi.fn().mockResolvedValue(undefined),
  showDeleteConfirmation: vi.fn().mockResolvedValue({ isConfirmed: true }),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRouter: () => mockRouter,
  }
})

import * as expenseApi from '../api/expenseApi'
import * as alerts from '../utils/alerts'

const mockGetExpenseById = vi.mocked(expenseApi.getExpenseById)
const mockConfirmExpense = vi.mocked(expenseApi.confirmExpense)
const mockDeleteExpense = vi.mocked(expenseApi.deleteExpense)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)
const mockShowDeleteConfirmation = vi.mocked(alerts.showDeleteConfirmation)

const mockPush = vi.fn()
const mockRouter = { push: mockPush }

// ── Fixtures ──────────────────────────────────────────────────────────────────

const draftExpense = {
  id: 1,
  user_id: 42,
  category_id: 3,
  category_name: 'Food',
  paid_to: 'Blue Bottle',
  tax_id: null,
  receipt_number: 'R-001',
  receipt_date: '2024-03-01',
  receipt_time: null,
  payment_method: 'Cash',
  currency: 'THB',
  subtotal: '90.91',
  tax_amount: '6.36',
  discount_amount: '0.00',
  total_amount: '100.00',
  notes: null,
  is_confirmed: false,
  created_at: '2024-03-01T10:00:00',
  updated_at: '2024-03-01T10:05:00',
  items: [],
}

const confirmedExpense = { ...draftExpense, is_confirmed: true }

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountDetail(id: string | number, locale = 'en') {
  const { default: ExpenseDetailView } = await import('../views/ExpenseDetailView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/expenses', name: 'expenses', component: StubView },
      { path: '/expenses/:id/edit', name: 'expense-edit', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
      { path: '/login', name: 'login', component: StubView },
    ],
  })
  router.push(`/expenses/${id}`)
  await router.isReady()
  return mount(ExpenseDetailView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockShowDeleteConfirmation.mockResolvedValue({
    isConfirmed: true,
    isDenied: false,
    isDismissed: false,
    value: undefined,
  })
  mockShowSuccess.mockResolvedValue(undefined as never)
  mockShowError.mockResolvedValue(undefined as never)
  mockDeleteExpense.mockResolvedValue(undefined)
})

// ── 1. Draft expense shows Confirm Expense button ─────────────────────────────
it('shows Confirm Expense button for a draft expense', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain(en.confirm_expense)
})

// ── 2. Confirmed expense hides Confirm Expense button ─────────────────────────
it('does not show Confirm Expense button for a confirmed expense', async () => {
  mockGetExpenseById.mockResolvedValue(confirmedExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).not.toContain(en.confirm_expense)
})

// ── 3. Confirmed expense shows Confirmed badge ────────────────────────────────
it('shows Confirmed badge for a confirmed expense', async () => {
  mockGetExpenseById.mockResolvedValue(confirmedExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain(en.confirmed)
})

// ── 4. Draft expense shows Draft badge ───────────────────────────────────────
it('shows Draft badge for a draft expense', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain(en.draft)
})

// ── 5. Clicking Confirm opens the confirmation dialog ────────────────────────
it('clicking Confirm Expense opens SweetAlert2 confirmation dialog', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowDeleteConfirmation).toHaveBeenCalledOnce()
})

// ── 6. Cancelled confirmation does not call the API ──────────────────────────
it('cancelling the confirmation dialog does not call confirmExpense', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockShowDeleteConfirmation.mockResolvedValue({
    isConfirmed: false,
    isDenied: false,
    isDismissed: true,
    value: undefined,
  })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockConfirmExpense).not.toHaveBeenCalled()
})

// ── 7. Confirmed action calls confirmExpense with the correct ID ─────────────
it('confirming the dialog calls confirmExpense with the correct expense ID', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockConfirmExpense).toHaveBeenCalledWith(1)
})

// ── 8. Confirmation success shows success alert ──────────────────────────────
it('success shows the expense_confirmed success alert', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledOnce()
  expect(mockShowSuccess).toHaveBeenCalledWith(en.expense_confirmed, en.expense_confirmed_message)
})

// ── 9. Confirmation success updates the displayed expense state ───────────────
it('success updates the expense to is_confirmed: true without a page reload', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)

  const wrapper = await mountDetail(1)
  await flushPromises()

  // Before confirm — shows Confirm button
  expect(wrapper.text()).toContain(en.confirm_expense)

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  // After confirm — Confirm button should be hidden, Confirmed badge visible
  expect(wrapper.text()).not.toContain(en.confirm_expense)
  expect(wrapper.text()).toContain(en.confirmed)
})

// ── 10. Confirmation failure shows error alert ────────────────────────────────
it('confirmation failure shows an error alert', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockRejectedValue({ response: { status: 500 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
})

// ── 11. Confirmation failure stays on the current page ───────────────────────
it('confirmation failure does not navigate away', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockRejectedValue({ response: { status: 500 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockPush).not.toHaveBeenCalled()
})

// ── 12. 409 Already confirmed — shows appropriate error ──────────────────────
it('409 response shows an error alert (already confirmed)', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockRejectedValue({
    response: { status: 409, data: { detail: 'Expense is already confirmed' } },
  })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
})

// ── 13. 422 Incomplete expense — shows appropriate error ─────────────────────
it('422 response shows an error alert (incomplete data)', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockRejectedValue({
    response: { status: 422, data: { detail: 'Category is required' } },
  })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
})

// ── 14. Duplicate confirmation is prevented while in-flight ──────────────────
it('confirm button is disabled while a confirmation request is in-flight', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  // Never resolves — simulates an in-flight request
  mockConfirmExpense.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountDetail(1)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  // Button should be disabled or show loading state
  const btn = wrapper.findAll('button').find(
    (b) => b.attributes('disabled') !== undefined || b.text().includes(en.confirming)
  )
  expect(btn).toBeDefined()
})

// ── 15. English labels render ─────────────────────────────────────────────────
it('renders English confirm label', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  const wrapper = await mountDetail(1, 'en')
  await flushPromises()
  expect(wrapper.text()).toContain(en.confirm_expense)
})

// ── 16. Thai labels render ────────────────────────────────────────────────────
it('renders Thai confirm label when locale is th', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  const wrapper = await mountDetail(1, 'th')
  await flushPromises()
  expect(wrapper.text()).toContain(th.confirm_expense)
})

// ── 17. Locale keys are defined ───────────────────────────────────────────────
describe('locale keys', () => {
  it('en.json has confirm_expense key', () => {
    expect(en.confirm_expense).toBeDefined()
    expect(typeof en.confirm_expense).toBe('string')
  })

  it('en.json has expense_confirmed key', () => {
    expect(en.expense_confirmed).toBeDefined()
  })

  it('en.json has unable_to_confirm_expense key', () => {
    expect(en.unable_to_confirm_expense).toBeDefined()
  })

  it('en.json has confirm_expense_title key', () => {
    expect(en.confirm_expense_title).toBeDefined()
  })

  it('en.json has confirm_expense_message key', () => {
    expect(en.confirm_expense_message).toBeDefined()
  })

  it('th.json has confirm_expense key', () => {
    expect(th.confirm_expense).toBeDefined()
    expect(typeof th.confirm_expense).toBe('string')
  })

  it('th.json has expense_confirmed key', () => {
    expect(th.expense_confirmed).toBeDefined()
  })
})
