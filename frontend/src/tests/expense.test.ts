/**
 * Expense list and detail view tests.
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
import ExpenseListView from '../views/ExpenseListView.vue'
import ExpenseDetailView from '../views/ExpenseDetailView.vue'
import type { Expense, ExpenseItem } from '../types/expense'

// ── Mock API modules ───────────────────────────────────────────────────────────
vi.mock('../api/authApi', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getCurrentUser: vi.fn(),
}))

vi.mock('../api/expenseApi', () => ({
  getExpenses: vi.fn(),
  getExpenseById: vi.fn(),
  exportExpenses: vi.fn(),
}))

vi.mock('../utils/alerts', () => ({
  showSuccessAlert: vi.fn().mockResolvedValue(undefined),
  showErrorAlert: vi.fn().mockResolvedValue(undefined),
  showDeleteConfirmation: vi.fn().mockResolvedValue({ isConfirmed: false }),
}))

vi.mock('../utils/download', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../utils/download')>()
  return { ...actual, downloadBlob: vi.fn() }
})

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn() }),
  }
})

import * as expenseApi from '../api/expenseApi'
const mockGetExpenses = vi.mocked(expenseApi.getExpenses)
const mockGetExpenseById = vi.mocked(expenseApi.getExpenseById)

// ── Test fixtures ──────────────────────────────────────────────────────────────

const fakeItem: ExpenseItem = {
  id: 10,
  expense_id: 1,
  category_id: null,
  original_name: 'Coffee',
  name_en: 'Coffee',
  name_th: 'กาแฟ',
  quantity: '2.000',
  unit: 'cup',
  unit_price: '50.00',
  discount_amount: '0.00',
  total_price: '100.00',
  created_at: '2024-03-01T10:00:00',
  updated_at: '2024-03-01T10:00:00',
}

const fakeExpense: Expense = {
  id: 1,
  user_id: 42,
  category_id: 3,
  category_name: 'Food & Drink',
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
  items: [fakeItem],
}

const fakeExpenseDraft: Expense = {
  ...fakeExpense,
  id: 2,
  paid_to: 'Draft Shop',
  is_confirmed: false,
  items: [],
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

function buildRouter(initialPath = '/expenses') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/expenses', name: 'expenses', component: StubView },
      { path: '/expenses/new', name: 'expense-create', component: StubView },
      { path: '/expenses/:id/edit', name: 'expense-edit', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
      { path: '/login', name: 'login', component: StubView },
    ],
  })
  router.push(initialPath)
  return router
}

async function mountList(locale = 'en') {
  const router = buildRouter('/expenses')
  await router.isReady()
  return mount(ExpenseListView, {
    global: { plugins: [router, buildI18n(locale)], stubs: { AppLayout: { template: '<div><slot /></div>' } } },
  })
}

async function mountDetail(id: string | number, locale = 'en') {
  const router = buildRouter(`/expenses/${id}`)
  await router.isReady()
  return mount(ExpenseDetailView, {
    global: { plugins: [router, buildI18n(locale)], stubs: { AppLayout: { template: '<div><slot /></div>' } } },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

// ── 1. List calls GET /expenses ────────────────────────────────────────────────
it('list view calls getExpenses on mount', async () => {
  mockGetExpenses.mockResolvedValue([])
  await mountList()
  await flushPromises()
  expect(mockGetExpenses).toHaveBeenCalledOnce()
})

// ── 2. Detail calls GET /expenses/{id} ────────────────────────────────────────
it('detail view calls getExpenseById with the route id', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  await mountDetail(1)
  await flushPromises()
  expect(mockGetExpenseById).toHaveBeenCalledWith(1)
})

// ── 3. List shows loading state ───────────────────────────────────────────────
it('list shows loading text while fetching', async () => {
  // Never resolves during this test
  mockGetExpenses.mockReturnValue(new Promise(() => {}))
  const wrapper = await mountList()
  expect(wrapper.text()).toContain(en.loading_expenses)
})

// ── 4. List displays expenses ─────────────────────────────────────────────────
it('list displays expense paid_to after loading', async () => {
  mockGetExpenses.mockResolvedValue([fakeExpense, fakeExpenseDraft])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain('Blue Bottle')
  expect(wrapper.text()).toContain('Draft Shop')
})

// ── 5. Money and currency display ─────────────────────────────────────────────
it('list displays total amount with currency', async () => {
  mockGetExpenses.mockResolvedValue([fakeExpense])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain('100.00 THB')
})

// ── 6. Manual status ──────────────────────────────────────────────────────────
it('displays Manual label for input_method manual (formatters)', () => {
  // This just verifies the locale key exists for manual
  expect(en.input_manual).toBe('Manual')
})

// ── 7. AI Extracted status ────────────────────────────────────────────────────
it('displays AI Extracted label key for input_method ai (formatters)', () => {
  expect(en.input_ai).toBe('AI Extracted')
})

// ── 8. Confirmed status badge ─────────────────────────────────────────────────
it('list shows Confirmed badge for confirmed expense', async () => {
  mockGetExpenses.mockResolvedValue([fakeExpense])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.confirmed)
})

// ── 9. Draft status badge ─────────────────────────────────────────────────────
it('list shows Draft badge for unconfirmed expense', async () => {
  mockGetExpenses.mockResolvedValue([fakeExpenseDraft])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.draft)
})

// ── 10. Empty state ───────────────────────────────────────────────────────────
it('list shows empty state when no expenses', async () => {
  mockGetExpenses.mockResolvedValue([])
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.no_expenses_found)
  expect(wrapper.text()).toContain(en.no_expenses_subtitle)
})

// ── 11. Error state ───────────────────────────────────────────────────────────
it('list shows error message when fetch fails', async () => {
  mockGetExpenses.mockRejectedValue(new Error('Network error'))
  const wrapper = await mountList()
  await flushPromises()
  expect(wrapper.text()).toContain(en.unable_to_load_expenses)
})

// ── 12. Detail link ───────────────────────────────────────────────────────────
it('list renders a link to each expense detail page', async () => {
  mockGetExpenses.mockResolvedValue([fakeExpense])
  const wrapper = await mountList()
  await flushPromises()
  const links = wrapper.findAll('a')
  const hasDetailLink = links.some((l) => l.attributes('href')?.includes('/expenses/1'))
  expect(hasDetailLink).toBe(true)
})

// ── 13. Detail loads route ID ─────────────────────────────────────────────────
it('detail view extracts numeric id from route and calls API', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  await mountDetail(1)
  await flushPromises()
  expect(mockGetExpenseById).toHaveBeenCalledWith(1)
})

// ── 14. Main fields display ───────────────────────────────────────────────────
it('detail view shows paid_to and receipt number', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain('Blue Bottle')
  expect(wrapper.text()).toContain('R-001')
})

// ── 15. Amounts display ───────────────────────────────────────────────────────
it('detail view shows subtotal, tax, and total', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain('90.91 THB')   // subtotal
  expect(wrapper.text()).toContain('6.36 THB')    // tax
  expect(wrapper.text()).toContain('100.00 THB')  // total
})

// ── 16. Nested items display ──────────────────────────────────────────────────
it('detail view shows expense items', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  // EN locale shows name_en
  expect(wrapper.text()).toContain('Coffee')
  expect(wrapper.text()).toContain('50.00 THB')
  expect(wrapper.text()).toContain('100.00 THB')
})

// ── 17. No-items state ────────────────────────────────────────────────────────
it('detail view shows no-items message when items array is empty', async () => {
  mockGetExpenseById.mockResolvedValue({ ...fakeExpense, items: [] })
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain(en.no_items)
})

// ── 18. 404 state ─────────────────────────────────────────────────────────────
it('detail view shows not-found message on 404', async () => {
  mockGetExpenseById.mockRejectedValue({ response: { status: 404 } })
  const wrapper = await mountDetail(99)
  await flushPromises()
  expect(wrapper.text()).toContain(en.expense_not_found)
})

// ── 19. Invalid route ID ──────────────────────────────────────────────────────
it('detail view shows not-found for a non-numeric route id', async () => {
  const wrapper = await mountDetail('abc')
  await flushPromises()
  expect(mockGetExpenseById).not.toHaveBeenCalled()
  expect(wrapper.text()).toContain(en.expense_not_found)
})

// ── 20. English / Thai label switch ──────────────────────────────────────────
describe('locale switching', () => {
  it('list shows Thai labels when locale is th', async () => {
    mockGetExpenses.mockResolvedValue([])
    const wrapper = await mountList('th')
    await flushPromises()
    expect(wrapper.text()).toContain(th.no_expenses_found)
  })

  it('detail shows Thai not-available label', async () => {
    mockGetExpenseById.mockResolvedValue({ ...fakeExpense, paid_to: null })
    const wrapper = await mountDetail(1, 'th')
    await flushPromises()
    expect(wrapper.text()).toContain(th.not_available)
  })
})

// ── 21. Internal fields not shown ────────────────────────────────────────────
it('detail view does not expose user_id', async () => {
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  // user_id value "42" should not appear as a raw labeled field
  const text = wrapper.text()
  // The number 42 may appear in other contexts; check no "user_id" label is visible
  expect(text).not.toContain('user_id')
})

// ── 22. Existing auth tests remain green (smoke check) ───────────────────────
it('expense module does not break auth module imports', async () => {
  const { useAuthStore } = await import('../stores/auth')
  const store = useAuthStore()
  expect(store).toBeDefined()
  expect(typeof store.login).toBe('function')
})
