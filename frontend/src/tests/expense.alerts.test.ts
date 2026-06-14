/**
 * Create and Edit success/failure alert tests.
 * Verifies that SweetAlert2 is shown after a successful save
 * and that frontend validation failures do NOT show a popup.
 */
import { it, expect, beforeEach, vi } from 'vitest'
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
const mockCreateExpense = vi.mocked(expenseApi.createExpense)
const mockUpdateExpense = vi.mocked(expenseApi.updateExpense)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)

const mockPush = vi.fn()
const mockRouter = { push: mockPush }

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeCategories = [
  { id: 1, code: 'FOOD', name_en: 'Food', name_th: 'อาหาร', is_active: true, created_at: '', updated_at: '' },
]

const fakeExpense = {
  id: 5,
  user_id: 1,
  category_id: 1,
  title: 'Lunch',
  merchant_name: 'Noodle Shop',
  receipt_number: 'R-100',
  receipt_date: '2024-06-01',
  payment_method: 'Cash',
  currency: 'THB',
  subtotal: '90.00',
  tax_amount: '6.30',
  discount_amount: '0.00',
  total_amount: '96.30',
  notes: '',
  is_confirmed: false,
  created_at: '2024-06-01T12:00:00',
  updated_at: '2024-06-01T12:00:00',
  items: [],
}

const createdExpense = { ...fakeExpense, id: 99 }

// ── Helpers ────────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountCreate(locale = 'en') {
  const { default: ExpenseCreateView } = await import('../views/ExpenseCreateView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/expenses', name: 'expenses', component: StubView },
      { path: '/expenses/new', name: 'expense-create', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
    ],
  })
  router.push('/expenses/new')
  await router.isReady()
  return mount(ExpenseCreateView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

async function mountEdit(id: number, locale = 'en') {
  const { default: ExpenseEditView } = await import('../views/ExpenseEditView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/expenses/:id/edit', name: 'expense-edit', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
    ],
  })
  router.push(`/expenses/${id}/edit`)
  await router.isReady()
  return mount(ExpenseEditView, {
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
})

// ── 1. Create success shows success alert ─────────────────────────────────
it('create success shows success alert', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockResolvedValue(createdExpense)

  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('Coffee')
  await wrapper.find('#ef-total').setValue('100')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledOnce()
})

// ── 2. Create success navigates after alert ────────────────────────────────
it('create success navigates to detail page after alert', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockResolvedValue(createdExpense)

  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('Coffee')
  await wrapper.find('#ef-total').setValue('100')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expense-detail', params: { id: 99 } })
})

// ── 3. Edit success shows success alert ───────────────────────────────────
it('edit success shows success alert', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockUpdateExpense.mockResolvedValue(fakeExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledOnce()
})

// ── 4. Edit success navigates after alert ─────────────────────────────────
it('edit success navigates to detail page after alert', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockUpdateExpense.mockResolvedValue(fakeExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expense-detail', params: { id: 5 } })
})

// ── 5. Frontend validation failure does NOT show SweetAlert2 ──────────────
it('frontend validation failure does not call showSuccessAlert or showErrorAlert', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)

  const wrapper = await mountCreate()
  await flushPromises()

  // Submit with nothing filled in → frontend validation error, no API call
  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockCreateExpense).not.toHaveBeenCalled()
  expect(mockShowSuccess).not.toHaveBeenCalled()
  expect(mockShowError).not.toHaveBeenCalled()
})

// ── 6. Network failure shows error alert ──────────────────────────────────
it('create network failure shows error alert', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  // No response object → network/server error
  mockCreateExpense.mockRejectedValue(new Error('Network Error'))

  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('Coffee')
  await wrapper.find('#ef-total').setValue('100')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockShowSuccess).not.toHaveBeenCalled()
})

// ── 7. Backend 422 does NOT trigger a popup ───────────────────────────────
it('create 422 backend error shows inline error but not a popup', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockRejectedValue({
    response: { status: 422, data: { detail: 'title is invalid' } },
  })

  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('Bad')
  await wrapper.find('#ef-total').setValue('50')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockShowError).not.toHaveBeenCalled()
  expect(mockShowSuccess).not.toHaveBeenCalled()
})

// ── 8. Success alert title uses i18n expense_created key ──────────────────
it('create success alert uses expense_created i18n key as title', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockResolvedValue(createdExpense)

  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('Coffee')
  await wrapper.find('#ef-total').setValue('100')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledWith(en.expense_created, en.expense_created_message)
})

// ── 9. Edit success alert title uses i18n expense_updated key ─────────────
it('edit success alert uses expense_updated i18n key as title', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockUpdateExpense.mockResolvedValue(fakeExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledWith(en.expense_updated, en.expense_updated_message)
})

// ── 10. Thai locale — success alert receives Thai title ───────────────────
it('create success alert in Thai locale uses Thai expense_created text', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockResolvedValue(createdExpense)

  const wrapper = await mountCreate('th')
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('Coffee')
  await wrapper.find('#ef-total').setValue('100')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledWith(th.expense_created, th.expense_created_message)
})
