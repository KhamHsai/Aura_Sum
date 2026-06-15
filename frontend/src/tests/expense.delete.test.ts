/**
 * Expense delete flow tests — detail page.
 * Covers delete button, confirmation dialog, success, failure, and navigation.
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
}))

// SweetAlert2 mock — tracks calls and returns controllable results
const mockSwalFire = vi.fn()
vi.mock('sweetalert2', () => ({
  default: { fire: mockSwalFire },
}))

// Alerts utility mock — wraps Swal.fire, tracks helpers individually
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
const mockDeleteExpense = vi.mocked(expenseApi.deleteExpense)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)
const mockShowDeleteConfirmation = vi.mocked(alerts.showDeleteConfirmation)

const mockPush = vi.fn()
const mockRouter = { push: mockPush }

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeExpense = {
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
  notes: 'Team breakfast',
  is_confirmed: true,
  created_at: '2024-03-01T10:00:00',
  updated_at: '2024-03-01T10:05:00',
  items: [],
}

// ── Helpers ────────────────────────────────────────────────────────────────────

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
  // Default: confirmation is accepted
  mockShowDeleteConfirmation.mockResolvedValue({ isConfirmed: true, isDenied: false, isDismissed: false, value: undefined })
  mockShowSuccess.mockResolvedValue(undefined as never)
  mockShowError.mockResolvedValue(undefined as never)
})

// ── 1. Delete button is visible after load ─────────────────────────────────
it('shows Delete Expense button when expense is loaded', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain(en.delete_expense)
})

// ── 2. Delete button is NOT shown while loading ────────────────────────────
it('does not show Delete button while loading', async () => {
  mockGetExpenseById.mockReturnValue(new Promise(() => {}))
  const wrapper = await mountDetail(1)
  // Still loading — no expense rendered yet
  expect(wrapper.text()).not.toContain(en.delete_expense)
})

// ── 3. Delete button is NOT shown on not-found ─────────────────────────────
it('does not show Delete button when expense is not found', async () => {
  mockGetExpenseById.mockRejectedValue({ response: { status: 404 } })
  const wrapper = await mountDetail(99)
  await flushPromises()
  expect(wrapper.text()).not.toContain(en.delete_expense)
})

// ── 4. Clicking Delete opens confirmation dialog ───────────────────────────
it('clicking Delete calls showDeleteConfirmation', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockResolvedValue(undefined)
  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockShowDeleteConfirmation).toHaveBeenCalledOnce()
})

// ── 5. Cancelled confirmation does not call the API ───────────────────────
it('cancelling confirmation does not call deleteExpense', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockShowDeleteConfirmation.mockResolvedValue({ isConfirmed: false, isDenied: false, isDismissed: true, value: undefined })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockDeleteExpense).not.toHaveBeenCalled()
})

// ── 6. Confirmed deletion calls deleteExpense ──────────────────────────────
it('confirming delete calls deleteExpense with correct id', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockResolvedValue(undefined)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockDeleteExpense).toHaveBeenCalledWith(1)
})

// ── 7. Delete success shows success alert ─────────────────────────────────
it('delete success shows success alert', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockResolvedValue(undefined)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledOnce()
})

// ── 8. Delete success redirects to /expenses ──────────────────────────────
it('delete success redirects to expenses list', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockResolvedValue(undefined)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expenses' })
})

// ── 9. Delete failure shows error alert ───────────────────────────────────
it('delete failure shows error alert', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockRejectedValue({ response: { status: 500 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
})

// ── 10. Delete failure stays on detail page ───────────────────────────────
it('delete failure does not redirect away from detail page', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockRejectedValue({ response: { status: 500 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockPush).not.toHaveBeenCalled()
})

// ── 11. Delete button disabled while request is running ───────────────────
it('delete button is disabled while deleting', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  // Never resolves — simulates an in-flight request
  mockDeleteExpense.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  // Confirmation resolves synchronously (already mocked as isConfirmed: true)
  await flushPromises()

  // After clicking and confirming, the button should be disabled
  const btn = wrapper.findAll('button').find((b) =>
    b.text().includes(en.delete_expense) || b.attributes('disabled') !== undefined
  )
  // At least one of: disabled attribute or text changed to saving
  const isDisabled = btn?.attributes('disabled') !== undefined || wrapper.text().includes(en.saving)
  expect(isDisabled).toBe(true)
})

// ── 12. Confirmation dialog contains expense title ────────────────────────
it('delete confirmation is called with delete_expense_title from i18n', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockResolvedValue(undefined)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  expect(mockShowDeleteConfirmation).toHaveBeenCalledWith(
    expect.objectContaining({ title: en.delete_expense_title })
  )
})

// ── 13. Locale: English labels render ─────────────────────────────────────
it('delete button shows English label', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountDetail(1, 'en')
  await flushPromises()
  expect(wrapper.text()).toContain(en.delete_expense)
})

// ── 14. Locale: Thai labels render ────────────────────────────────────────
it('delete button shows Thai label when locale is th', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountDetail(1, 'th')
  await flushPromises()
  expect(wrapper.text()).toContain(th.delete_expense)
})

// ── 15. Confirmation text is soft-delete safe (no "permanent") ────────────
it('delete confirmation message does not claim permanent deletion', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockDeleteExpense.mockResolvedValue(undefined)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const deleteBtn = wrapper.findAll('button').find((b) => b.text().includes(en.delete_expense))
  await deleteBtn!.trigger('click')
  await flushPromises()

  const callArg = mockShowDeleteConfirmation.mock.calls[0][0]
  expect(callArg.text.toLowerCase()).not.toContain('permanent')
})

// ── 16. Locale keys for delete are defined ────────────────────────────────
describe('locale keys', () => {
  it('en.json has delete_expense key', () => {
    expect(en.delete_expense).toBeDefined()
    expect(typeof en.delete_expense).toBe('string')
  })

  it('en.json has delete_expense_title key', () => {
    expect(en.delete_expense_title).toBeDefined()
  })

  it('en.json has delete_expense_message key', () => {
    expect(en.delete_expense_message).toBeDefined()
  })

  it('en.json has expense_deleted key', () => {
    expect(en.expense_deleted).toBeDefined()
  })

  it('en.json has unable_to_delete_expense key', () => {
    expect(en.unable_to_delete_expense).toBeDefined()
  })

  it('th.json has delete_expense key', () => {
    expect(th.delete_expense).toBeDefined()
    expect(typeof th.delete_expense).toBe('string')
  })

  it('th.json has expense_deleted key', () => {
    expect(th.expense_deleted).toBeDefined()
  })
})
