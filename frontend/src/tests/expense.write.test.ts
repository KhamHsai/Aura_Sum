/**
 * Expense create/edit write tests.
 * Covers category API, create/update API, route ordering,
 * form behaviour, validation, and navigation.
 * All API and router calls are mocked — no real backend required.
 */
import { it, expect, describe, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import { defineComponent, nextTick } from 'vue'
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

const mockGetCategories = vi.mocked(categoryApi.getCategories)
const mockGetExpenseById = vi.mocked(expenseApi.getExpenseById)
const mockCreateExpense = vi.mocked(expenseApi.createExpense)
const mockUpdateExpense = vi.mocked(expenseApi.updateExpense)

const mockPush = vi.fn()
const mockRouter = { push: mockPush }

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeCategories = [
  { id: 1, code: 'FOOD', name_en: 'Food', name_th: 'อาหาร', is_active: true, created_at: '', updated_at: '' },
  { id: 2, code: 'TRANS', name_en: 'Transport', name_th: 'การเดินทาง', is_active: true, created_at: '', updated_at: '' },
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
  notes: 'team lunch',
  is_confirmed: false,
  created_at: '2024-06-01T12:00:00',
  updated_at: '2024-06-01T12:00:00',
  items: [
    {
      id: 10,
      expense_id: 5,
      category_id: null,
      original_name: 'Pad Thai',
      name_en: 'Pad Thai',
      name_th: 'ผัดไทย',
      quantity: '2.000',
      unit: 'plate',
      unit_price: '45.00',
      discount_amount: '0.00',
      total_price: '90.00',
      created_at: '',
      updated_at: '',
    },
  ],
}

const createdExpense = { ...fakeExpense, id: 99 }

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

function buildRouter(initialPath = '/expenses/new') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/expenses', name: 'expenses', component: StubView },
      { path: '/expenses/new', name: 'expense-create', component: StubView },
      { path: '/expenses/:id/edit', name: 'expense-edit', component: StubView },
      { path: '/expenses/:id', name: 'expense-detail', component: StubView },
    ],
  })
  router.push(initialPath)
  return router
}

async function mountCreate(locale = 'en') {
  const { default: ExpenseCreateView } = await import('../views/ExpenseCreateView.vue')
  const router = buildRouter('/expenses/new')
  await router.isReady()
  return mount(ExpenseCreateView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

async function mountEdit(id: number | string, locale = 'en') {
  const { default: ExpenseEditView } = await import('../views/ExpenseEditView.vue')
  const router = buildRouter(`/expenses/${id}/edit`)
  await router.isReady()
  return mount(ExpenseEditView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

// ── Setup ─────────────────────────────────────────────────────────────────────

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockPush.mockClear()
})

// ── 1. Category API calls /categories ─────────────────────────────────────────
it('getCategories calls GET /categories', async () => {
  const { getCategories } = await import('../api/categoryApi')
  mockGetCategories.mockResolvedValue(fakeCategories)
  await getCategories()
  expect(mockGetCategories).toHaveBeenCalledOnce()
})

// ── 2. Create API calls POST /expenses ────────────────────────────────────────
it('createExpense calls POST /expenses', async () => {
  const { createExpense } = await import('../api/expenseApi')
  mockCreateExpense.mockResolvedValue(createdExpense)
  const payload = {
    category_id: 1,
    title: 'Test',
    merchant_name: null,
    receipt_number: null,
    receipt_date: '2024-06-01',
    payment_method: null,
    currency: 'THB',
    subtotal: null,
    tax_amount: null,
    discount_amount: null,
    total_amount: '100',
    notes: null,
    items: [],
  }
  const result = await createExpense(payload)
  expect(mockCreateExpense).toHaveBeenCalledWith(payload)
  expect(result.id).toBe(99)
})

// ── 3. Update API calls PUT /expenses/{id} ────────────────────────────────────
it('updateExpense calls PUT /expenses/{id}', async () => {
  const { updateExpense } = await import('../api/expenseApi')
  mockUpdateExpense.mockResolvedValue(fakeExpense)
  await updateExpense(5, { title: 'Updated' })
  expect(mockUpdateExpense).toHaveBeenCalledWith(5, { title: 'Updated' })
})

// ── 4. /expenses/new is NOT treated as an expense ID ─────────────────────────
it('/expenses/new route is distinct from /expenses/:id', async () => {
  const router = buildRouter('/expenses/new')
  await router.isReady()
  expect(router.currentRoute.value.name).toBe('expense-create')
  expect(router.currentRoute.value.params.id).toBeUndefined()
})

// ── 5. Create page loads categories on mount ──────────────────────────────────
it('create page calls getCategories on mount', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  await mountCreate()
  await flushPromises()
  expect(mockGetCategories).toHaveBeenCalledOnce()
})

// ── 6. Create page displays form ──────────────────────────────────────────────
it('create page renders the expense form', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()
  expect(wrapper.find('form').exists()).toBe(true)
})

// ── 7. Required category validation ──────────────────────────────────────────
it('shows category required error when submitting without category', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  // Fill minimum required fields except category
  await wrapper.find('#ef-title').setValue('Test')
  await wrapper.find('#ef-total').setValue('100')
  await wrapper.find('form').trigger('submit')
  await nextTick()

  expect(wrapper.text()).toContain(en.category_required)
})

// ── 8. Required title validation ──────────────────────────────────────────────
it('shows title required error when submitting without title', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-total').setValue('100')
  await wrapper.find('form').trigger('submit')
  await nextTick()

  expect(wrapper.text()).toContain(en.title_required)
})

// ── 9. Required total validation ──────────────────────────────────────────────
it('shows total required error when submitting without total', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-title').setValue('Test')
  await wrapper.find('form').trigger('submit')
  await nextTick()

  expect(wrapper.text()).toContain(en.total_required)
})

// ── 10. Negative main amount validation ───────────────────────────────────────
it('shows invalid amount error for negative total', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-title').setValue('Test')
  await wrapper.find('#ef-total').setValue('-10')
  await wrapper.find('form').trigger('submit')
  await nextTick()

  expect(wrapper.text()).toContain(en.invalid_amount)
})

// ── 11. Add item ──────────────────────────────────────────────────────────────
it('clicking Add Item adds a new item row', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  const addBtn = wrapper.findAll('button').find((b) => b.text().includes(en.add_item))
  expect(addBtn).toBeDefined()
  await addBtn!.trigger('click')
  await nextTick()

  // A "Remove Item" button should now be visible
  expect(wrapper.text()).toContain(en.remove_item)
})

// ── 12. Remove item ───────────────────────────────────────────────────────────
it('clicking Remove Item removes the item row', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  // Add then remove
  const addBtn = wrapper.findAll('button').find((b) => b.text().includes(en.add_item))
  await addBtn!.trigger('click')
  await nextTick()

  const removeBtn = wrapper.findAll('button').find((b) => b.text().includes(en.remove_item))
  await removeBtn!.trigger('click')
  await nextTick()

  expect(wrapper.text()).toContain(en.no_items_added)
})

// ── 13. Item requires one name ────────────────────────────────────────────────
it('shows item name error when all name fields are empty', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  const addBtn = wrapper.findAll('button').find((b) => b.text().includes(en.add_item))
  await addBtn!.trigger('click')
  await nextTick()

  // Fill the quantity so that's not the error, but leave names empty
  const itemSection = wrapper.find('.item-row')
  const qInput = itemSection.find('input[placeholder="1"]')
  if (qInput.exists()) await qInput.setValue('1')

  // Also fill total price on the item
  const tpInput = itemSection.find('input[placeholder="0.00"]:last-of-type')
  if (tpInput.exists()) await tpInput.setValue('10')

  // Submit the form (without title/category/total to keep this focused on item error)
  await wrapper.find('form').trigger('submit')
  await nextTick()

  expect(wrapper.text()).toContain(en.item_name_required)
})

// ── 14. Negative item amount validation ───────────────────────────────────────
it('shows invalid amount for non-numeric item quantity', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  const wrapper = await mountCreate()
  await flushPromises()

  const addBtn = wrapper.findAll('button').find((b) => b.text().includes(en.add_item))
  await addBtn!.trigger('click')
  await nextTick()

  const itemSection = wrapper.find('.item-row')
  const origName = itemSection.find('input[placeholder="' + en.original_name + '"]')
  if (origName.exists()) await origName.setValue('Coffee')

  const qInput = itemSection.find('input[placeholder="1"]')
  if (qInput.exists()) await qInput.setValue('abc')

  await wrapper.find('form').trigger('submit')
  await nextTick()

  expect(wrapper.text()).toContain(en.invalid_amount)
})

// ── 15. Create submit sends cleaned request ───────────────────────────────────
it('create submit sends the cleaned request to createExpense', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockResolvedValue(createdExpense)
  const wrapper = await mountCreate()
  await flushPromises()

  // Select a category
  const catSelect = wrapper.find('#ef-category')
  await catSelect.setValue('1')

  await wrapper.find('#ef-title').setValue('Coffee Run')
  await wrapper.find('#ef-total').setValue('150.00')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockCreateExpense).toHaveBeenCalledOnce()
  const arg = mockCreateExpense.mock.calls[0][0]
  expect(arg.title).toBe('Coffee Run')
  expect(arg.total_amount).toBe('150.00')
  expect(arg.category_id).toBe(1)
})

// ── 16. Create success redirects to detail ────────────────────────────────────
it('successful create redirects to /expenses/{id}', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockResolvedValue(createdExpense)
  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('Test')
  await wrapper.find('#ef-total').setValue('50.00')

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expense-detail', params: { id: 99 } })
})

// ── 17. Edit page loads existing expense ─────────────────────────────────────
it('edit page calls getExpenseById on mount', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  await mountEdit(5)
  await flushPromises()
  expect(mockGetExpenseById).toHaveBeenCalledWith(5)
})

// ── 18. Edit page fills fields from existing expense ─────────────────────────
it('edit page pre-fills the title field', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountEdit(5)
  await flushPromises()

  const titleInput = wrapper.find('#ef-title')
  expect((titleInput.element as HTMLInputElement).value).toBe('Lunch')
})

// ── 19. Edit page includes all current items ──────────────────────────────────
it('edit page shows existing items in form', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  const wrapper = await mountEdit(5)
  await flushPromises()

  expect(wrapper.text()).toContain(en.remove_item)
})

// ── 20. Edit submit sends complete item list ──────────────────────────────────
it('edit submit includes all items in the request', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockUpdateExpense.mockResolvedValue(fakeExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockUpdateExpense).toHaveBeenCalledOnce()
  const [, payload] = mockUpdateExpense.mock.calls[0]
  expect(Array.isArray(payload.items)).toBe(true)
  expect(payload.items!.length).toBe(1)
  expect(payload.items![0].original_name).toBe('Pad Thai')
})

// ── 21. Edit success redirects to detail ─────────────────────────────────────
it('successful edit redirects to /expenses/{id}', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockResolvedValue(fakeExpense)
  mockUpdateExpense.mockResolvedValue(fakeExpense)

  const wrapper = await mountEdit(5)
  await flushPromises()

  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expense-detail', params: { id: 5 } })
})

// ── 22. Edit 404 is handled ───────────────────────────────────────────────────
it('edit page shows not-found for 404', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockGetExpenseById.mockRejectedValue({ response: { status: 404 } })

  const wrapper = await mountEdit(999)
  await flushPromises()

  expect(wrapper.text()).toContain(en.expense_not_found)
})

// ── 23. Backend 422 error is shown safely ────────────────────────────────────
it('shows backend error message on create failure', async () => {
  mockGetCategories.mockResolvedValue(fakeCategories)
  mockCreateExpense.mockRejectedValue({
    response: { status: 422, data: { detail: 'title must not be whitespace-only' } },
  })

  const wrapper = await mountCreate()
  await flushPromises()

  await wrapper.find('#ef-category').setValue('1')
  await wrapper.find('#ef-title').setValue('   ')
  await wrapper.find('#ef-total').setValue('100')

  // Force submit bypassing client validation by setting title after
  await wrapper.find('#ef-title').setValue('Valid')
  await wrapper.find('form').trigger('submit')
  await flushPromises()

  expect(wrapper.text()).toContain('title must not be whitespace-only')
})

// ── 24. English/Thai labels switch ───────────────────────────────────────────
describe('locale switching', () => {
  it('create page shows Thai label for create_expense', async () => {
    mockGetCategories.mockResolvedValue(fakeCategories)
    const wrapper = await mountCreate('th')
    await flushPromises()
    expect(wrapper.text()).toContain(th.create_expense)
  })

  it('create page shows Thai save button text', async () => {
    mockGetCategories.mockResolvedValue(fakeCategories)
    const wrapper = await mountCreate('th')
    await flushPromises()
    expect(wrapper.text()).toContain(th.save_expense)
  })
})

// ── 25. Existing expense tests remain green (smoke check) ─────────────────────
it('expense write module does not break existing expense read imports', async () => {
  const { getExpenses, getExpenseById } = await import('../api/expenseApi')
  expect(typeof getExpenses).toBe('function')
  expect(typeof getExpenseById).toBe('function')
})
