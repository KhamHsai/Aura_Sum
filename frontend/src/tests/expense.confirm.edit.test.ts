/**
 * Expense confirmation flow tests — edit page.
 * Covers confirm button visibility, save-then-confirm sequence, validation,
 * success, failure, and navigation.
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

vi.mock('../api/categoryApi', () => ({
  getCategories: vi.fn(),
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

import * as categoryApi from '../api/categoryApi'
import * as expenseApi from '../api/expenseApi'
import * as alerts from '../utils/alerts'

const mockGetCategories = vi.mocked(categoryApi.getCategories)
const mockGetExpenseById = vi.mocked(expenseApi.getExpenseById)
const mockUpdateExpense = vi.mocked(expenseApi.updateExpense)
const mockConfirmExpense = vi.mocked(expenseApi.confirmExpense)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)
const mockShowDeleteConfirmation = vi.mocked(alerts.showDeleteConfirmation)

const mockPush = vi.fn()
const mockRouter = { push: mockPush }

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeCategory = { id: 2, code: 'FOOD', name_en: 'Food', name_th: 'อาหาร', is_active: true, created_at: '2024-01-01T00:00:00', updated_at: '2024-01-01T00:00:00' }

const draftExpense = {
  id: 5,
  user_id: 1,
  category_id: 2,
  title: 'Lunch',
  merchant_name: 'Mango Tree',
  receipt_number: null,
  receipt_date: '2024-05-01',
  payment_method: 'Card',
  currency: 'THB',
  subtotal: null,
  tax_amount: null,
  discount_amount: null,
  total_amount: '200.00',
  notes: null,
  is_confirmed: false,
  created_at: '2024-05-01T12:00:00',
  updated_at: '2024-05-01T12:05:00',
  items: [],
}

const confirmedExpense = { ...draftExpense, is_confirmed: true }

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountEdit(id: string | number, locale = 'en') {
  const { default: ExpenseEditView } = await import('../views/ExpenseEditView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/expenses', name: 'expenses', component: StubView },
      { path: '/expenses/:id/edit', name: 'expense-edit', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
      { path: '/login', name: 'login', component: StubView },
    ],
  })
  router.push(`/expenses/${id}/edit`)
  await router.isReady()
  return mount(ExpenseEditView, {
    attachTo: document.body,
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockGetCategories.mockResolvedValue([fakeCategory])
  mockShowDeleteConfirmation.mockResolvedValue({
    isConfirmed: true,
    isDenied: false,
    isDismissed: false,
    value: undefined,
  })
  mockShowSuccess.mockResolvedValue(undefined as never)
  mockShowError.mockResolvedValue(undefined as never)
})

// ── 1. Draft expense shows Confirm Expense button ─────────────────────────────
it('shows Confirm Expense button when expense is a draft', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  const wrapper = await mountEdit(5)
  await flushPromises()
  expect(wrapper.text()).toContain(en.confirm_expense)
})

// ── 2. Confirmed expense hides Confirm Expense button ─────────────────────────
it('hides Confirm Expense button when expense is already confirmed', async () => {
  mockGetExpenseById.mockResolvedValue(confirmedExpense)
  const wrapper = await mountEdit(5)
  await flushPromises()
  expect(wrapper.text()).not.toContain(en.confirm_expense)
})

// ── 3. Clicking Confirm opens SweetAlert2 dialog ─────────────────────────────
it('clicking Confirm Expense opens a SweetAlert2 dialog', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockUpdateExpense.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowDeleteConfirmation).toHaveBeenCalledOnce()
})

// ── 4. Cancelled dialog does not save or confirm ─────────────────────────────
it('cancelling the confirmation dialog does not call updateExpense or confirmExpense', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockShowDeleteConfirmation.mockResolvedValue({
    isConfirmed: false,
    isDenied: false,
    isDismissed: true,
    value: undefined,
  })

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockUpdateExpense).not.toHaveBeenCalled()
  expect(mockConfirmExpense).not.toHaveBeenCalled()
})

// ── 5. Edit confirm saves the current expense first ───────────────────────────
it('edit confirm calls updateExpense before calling confirmExpense', async () => {
  const callOrder: string[] = []
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockUpdateExpense.mockImplementation(async () => {
    callOrder.push('update')
    return draftExpense
  })
  mockConfirmExpense.mockImplementation(async () => {
    callOrder.push('confirm')
    return confirmedExpense
  })

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(callOrder).toEqual(['update', 'confirm'])
})

// ── 6. Update failure prevents confirmation ───────────────────────────────────
it('if updateExpense fails, confirmExpense is not called', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockUpdateExpense.mockRejectedValue({ response: { status: 422 } })

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockConfirmExpense).not.toHaveBeenCalled()
})

// ── 7. Successful edit confirm navigates to the expense detail page ───────────
it('successful edit confirm navigates to expense-detail', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockUpdateExpense.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expense-detail', params: { id: 5 } })
})

// ── 8. Successful edit confirm shows success alert ────────────────────────────
it('successful edit confirm shows expense_confirmed success alert', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockUpdateExpense.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledWith(en.expense_confirmed, en.expense_confirmed_message)
})

// ── 9. Confirm failure after update is handled safely ────────────────────────
it('if confirmExpense fails after update succeeds, shows error and stays on page', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockUpdateExpense.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockRejectedValue({ response: { status: 422, data: { detail: 'Category required' } } })

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockPush).not.toHaveBeenCalled()
})

// ── 10. English labels render ─────────────────────────────────────────────────
it('renders English confirm label', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  const wrapper = await mountEdit(5, 'en')
  await flushPromises()
  expect(wrapper.text()).toContain(en.confirm_expense)
})

// ── 11. Thai labels render ────────────────────────────────────────────────────
it('renders Thai confirm label when locale is th', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  const wrapper = await mountEdit(5, 'th')
  await flushPromises()
  expect(wrapper.text()).toContain(th.confirm_expense)
})

// ── 12. confirmExpense is called with the correct expense ID ─────────────────
it('confirmExpense is called with the expense ID from the route', async () => {
  mockGetExpenseById.mockResolvedValue(draftExpense)
  mockUpdateExpense.mockResolvedValue(draftExpense)
  mockConfirmExpense.mockResolvedValue(confirmedExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  const confirmBtn = wrapper.findAll('button').find((b) => b.text().includes(en.confirm_expense))
  await confirmBtn!.trigger('click')
  await flushPromises()

  expect(mockConfirmExpense).toHaveBeenCalledWith(5)
})

// ── 13. Locale keys for confirmation are defined ──────────────────────────────
describe('locale keys', () => {
  it('en.json has confirm_expense key', () => {
    expect(en.confirm_expense).toBeDefined()
    expect(typeof en.confirm_expense).toBe('string')
  })

  it('en.json has confirming key', () => {
    expect(en.confirming).toBeDefined()
  })

  it('th.json has confirm_expense key', () => {
    expect(th.confirm_expense).toBeDefined()
    expect(typeof th.confirm_expense).toBe('string')
  })

  it('th.json has confirming key', () => {
    expect(th.confirming).toBeDefined()
  })
})
