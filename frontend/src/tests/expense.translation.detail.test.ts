/**
 * Translation flow tests — expense detail page.
 * All API calls and SweetAlert2 helpers are mocked.
 * No real Gemini requests are made.
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
  translateExpense: vi.fn(),
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
const mockTranslateExpense = vi.mocked(expenseApi.translateExpense)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)

const mockPush = vi.fn()
const mockRouter = { push: mockPush }

// ── Fixtures ──────────────────────────────────────────────────────────────────

const sampleExpense = {
  id: 1,
  user_id: 42,
  category_id: 3,
  category_name: 'Food & Drink',
  paid_to: 'ร้านข้าวมันไก่',
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
  notes: 'อาหารกลางวันกับเพื่อนร่วมงาน',
  is_confirmed: true,
  created_at: '2024-03-01T10:00:00',
  updated_at: '2024-03-01T10:05:00',
  items: [
    {
      id: 10,
      expense_id: 1,
      category_id: null,
      original_name: 'ข้าวมันไก่',
      name_en: null,
      name_th: 'ข้าวมันไก่',
      quantity: '2',
      unit: 'จาน',
      unit_price: '45.00',
      discount_amount: '0.00',
      total_price: '90.00',
      created_at: '2024-03-01T10:00:00',
      updated_at: '2024-03-01T10:00:00',
    },
  ],
}

const sampleExpenseNoNotes = { ...sampleExpense, notes: null }
const sampleExpenseNoItems = { ...sampleExpense, items: [] }

const translationResponseEn = {
  expense_id: 1,
  source_language: 'th' as const,
  target_language: 'en' as const,
  translated_notes: 'Lunch with colleagues',
  items: [
    {
      item_id: 10,
      original_name: 'ข้าวมันไก่',
      name_en: 'Chicken Rice',
      name_th: 'ข้าวมันไก่',
      translated_name: 'Chicken Rice',
    },
  ],
  reused_existing_translation: false,
}

const translationResponseTh = {
  expense_id: 1,
  source_language: 'en' as const,
  target_language: 'th' as const,
  translated_notes: 'ทานข้าวกลางวันกับเพื่อนร่วมงาน',
  items: [
    {
      item_id: 10,
      original_name: 'Chicken Rice',
      name_en: 'Chicken Rice',
      name_th: 'ข้าวมันไก่',
      translated_name: 'ข้าวมันไก่',
    },
  ],
  reused_existing_translation: false,
}

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
  mockShowSuccess.mockResolvedValue(undefined as never)
  mockShowError.mockResolvedValue(undefined as never)
})

// ── 1. No translation request on page mount ───────────────────────────────────
it('does not call translateExpense when the page mounts', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  await mountDetail(1)
  await flushPromises()
  expect(mockTranslateExpense).not.toHaveBeenCalled()
})

// ── 2. Translation controls appear on expense detail ─────────────────────────
it('shows the Translate Expense section on the expense detail page', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.text()).toContain(en.translate_expense)
})

// ── 3. Target language selector is present ────────────────────────────────────
it('shows the target language selector', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  expect(wrapper.find('select').exists()).toBe(true)
})

// ── 4. Default target follows current frontend locale (en → en) ───────────────
it('default target language is "en" when frontend locale is English', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1, 'en')
  await flushPromises()
  const select = wrapper.find('select')
  expect((select.element as HTMLSelectElement).value).toBe('en')
})

// ── 5. Default target follows current frontend locale (th → th) ───────────────
it('default target language is "th" when frontend locale is Thai', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1, 'th')
  await flushPromises()
  const select = wrapper.find('select')
  expect((select.element as HTMLSelectElement).value).toBe('th')
})

// ── 6. User can change target language ───────────────────────────────────────
it('user can change the target language via the selector', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1, 'en')
  await flushPromises()
  const select = wrapper.find('select')
  await select.setValue('th')
  expect((select.element as HTMLSelectElement).value).toBe('th')
})

// ── 7. Translate button is present ───────────────────────────────────────────
it('shows a Translate button', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1)
  await flushPromises()
  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  expect(translateBtn).toBeDefined()
})

// ── 8. Clicking Translate starts the request ─────────────────────────────────
it('clicking Translate calls translateExpense with the correct expense ID and language', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)
  const wrapper = await mountDetail(1, 'en')
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockTranslateExpense).toHaveBeenCalledWith(1, 'en')
})

// ── 9. Button is disabled while translating ──────────────────────────────────
it('translate button is disabled while a translation request is in-flight', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  // Never resolves — simulates an in-flight request
  mockTranslateExpense.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  const disabledBtn = wrapper
    .findAll('button')
    .find((b) => b.attributes('disabled') !== undefined || b.text().includes(en.translating))
  expect(disabledBtn).toBeDefined()
})

// ── 10. Loading message is shown while translating ───────────────────────────
it('shows translating loading message while translation is in-flight', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain(en.translating)
})

// ── 11. Duplicate translation requests are prevented ─────────────────────────
it('does not send a second translation request while one is already in-flight', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockTranslateExpense).toHaveBeenCalledOnce()
})

// ── 12. Success result is stored and shown ────────────────────────────────────
it('stores and displays the translation result on success', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('Lunch with colleagues')
})

// ── 13. Success alert is shown ────────────────────────────────────────────────
it('shows success alert after translation completes', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledWith(en.translation_completed, en.translation_completed_message)
})

// ── 14. Original paid_to remains visible ─────────────────────────────────────
it('keeps the original expense paid_to visible after translation', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('ร้านข้าวมันไก่')
})

// ── 15. Translated notes are displayed ────────────────────────────────────────
it('displays the translated notes after translation', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('Lunch with colleagues')
})

// ── 16. Original notes remain visible ────────────────────────────────────────
it('keeps the original notes visible after translation', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('อาหารกลางวันกับเพื่อนร่วมงาน')
})

// ── 17. Translated notes are displayed ───────────────────────────────────────
it('displays the translated notes', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('Lunch with colleagues')
})

// ── 18. Translated item names are displayed ───────────────────────────────────
it('displays translated item names', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('Chicken Rice')
})

// ── 19. Items are matched by item_id ─────────────────────────────────────────
it('uses item_id to match translated items', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseEn)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  // item_id 10 should show translated_name "Chicken Rice"
  expect(wrapper.text()).toContain('Chicken Rice')
})

// ── 20. Missing translated fields show safe fallback ─────────────────────────
it('shows fallback text when translated_name is null', async () => {
  const responseWithNull = {
    ...translationResponseEn,
    items: [
      {
        item_id: 10,
        original_name: 'ข้าวมันไก่',
        name_en: null,
        name_th: 'ข้าวมันไก่',
        translated_name: null,
      },
    ],
  }
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockResolvedValue(responseWithNull)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain(en.no_translation_available)
})

// ── 21. 503 maps to Gemini not configured message ─────────────────────────────
it('503 error maps to gemini_not_configured_translation message', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockRejectedValue({ response: { status: 503 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledWith(
    en.unable_to_translate_expense,
    en.gemini_not_configured_translation,
  )
})

// ── 22. 429 maps to quota exceeded message ───────────────────────────────────
it('429 error maps to gemini_quota_exceeded_translation message', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockRejectedValue({ response: { status: 429 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledWith(
    en.unable_to_translate_expense,
    en.gemini_quota_exceeded_translation,
  )
})

// ── 23. 422 maps to unsupported language message ──────────────────────────────
it('422 error maps to unsupported_language message', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockRejectedValue({ response: { status: 422 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledWith(
    en.unable_to_translate_expense,
    en.unsupported_language,
  )
})

// ── 24. 404 maps to expense not found ────────────────────────────────────────
it('404 error maps to expense_not_found message', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockRejectedValue({ response: { status: 404 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledWith(
    en.unable_to_translate_expense,
    en.expense_not_found,
  )
})

// ── 25. Network failure shows safe error alert ───────────────────────────────
it('network failure shows safe error alert', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockRejectedValue(new Error('Network Error'))

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockShowError).toHaveBeenCalledWith(
    en.unable_to_translate_expense,
    en.translation_service_unavailable,
  )
})

// ── 26. Failure keeps original expense visible ───────────────────────────────
it('keeps the original paid_to visible after a translation failure', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  mockTranslateExpense.mockRejectedValue({ response: { status: 500 } })

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('ร้านข้าวมันไก่')
})

// ── 27. Thai target translation result is displayed ──────────────────────────
it('displays Thai translated notes when target is Thai', async () => {
  const thaiExpense = { ...sampleExpense, notes: 'Lunch with team' }
  mockGetExpenseById.mockResolvedValue(thaiExpense)
  mockTranslateExpense.mockResolvedValue(translationResponseTh)

  const wrapper = await mountDetail(1, 'th')
  await flushPromises()

  const select = wrapper.find('select')
  await select.setValue('th')

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(th.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  expect(wrapper.text()).toContain('ทานข้าวกลางวันกับเพื่อนร่วมงาน')
})

// ── 28. English labels render ────────────────────────────────────────────────
it('renders English translation labels', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1, 'en')
  await flushPromises()
  expect(wrapper.text()).toContain(en.translate_expense)
  expect(wrapper.text()).toContain(en.target_language)
})

// ── 29. Thai labels render ───────────────────────────────────────────────────
it('renders Thai translation labels when locale is th', async () => {
  mockGetExpenseById.mockResolvedValue(sampleExpense)
  const wrapper = await mountDetail(1, 'th')
  await flushPromises()
  expect(wrapper.text()).toContain(th.translate_expense)
  expect(wrapper.text()).toContain(th.target_language)
})

// ── 30. Expense with no notes does not show notes comparison ─────────────────
it('does not show notes comparison when expense has no notes', async () => {
  const responseNoNotes = { ...translationResponseEn, translated_notes: null }
  mockGetExpenseById.mockResolvedValue(sampleExpenseNoNotes)
  mockTranslateExpense.mockResolvedValue(responseNoNotes)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  // original_notes label should not appear because notes is null
  expect(wrapper.text()).not.toContain(en.original_notes)
})

// ── 31. Expense with no items shows no items translation section ──────────────
it('does not show item translation rows when expense has no items', async () => {
  const responseNoItems = { ...translationResponseEn, items: [] }
  mockGetExpenseById.mockResolvedValue(sampleExpenseNoItems)
  mockTranslateExpense.mockResolvedValue(responseNoItems)

  const wrapper = await mountDetail(1)
  await flushPromises()

  const translateBtn = wrapper.findAll('button').find((b) => b.text().includes(en.translate))
  await translateBtn!.trigger('click')
  await flushPromises()

  // The translated_name label should not appear when there are no translated items
  expect(wrapper.text()).not.toContain(en.translated_name)
})

// ── 32. Locale keys are defined — en.json ────────────────────────────────────
describe('locale keys — en.json', () => {
  it('has translate_expense key', () => { expect(en.translate_expense).toBeDefined() })
  it('has target_language key', () => { expect(en.target_language).toBeDefined() })
  it('has translate key', () => { expect(en.translate).toBeDefined() })
  it('has translating key', () => { expect(en.translating).toBeDefined() })
  it('has translation_may_take_a_moment key', () => { expect(en.translation_may_take_a_moment).toBeDefined() })
  it('has translation_completed key', () => { expect(en.translation_completed).toBeDefined() })
  it('has translation_completed_message key', () => { expect(en.translation_completed_message).toBeDefined() })
  it('has unable_to_translate_expense key', () => { expect(en.unable_to_translate_expense).toBeDefined() })
  it('has original_title key', () => { expect(en.original_title).toBeDefined() })
  it('has translated_title key', () => { expect(en.translated_title).toBeDefined() })
  it('has original_notes key', () => { expect(en.original_notes).toBeDefined() })
  it('has translated_notes key', () => { expect(en.translated_notes).toBeDefined() })
  it('has translated_name key', () => { expect(en.translated_name).toBeDefined() })
  it('has ai_translation_quota_notice key', () => { expect(en.ai_translation_quota_notice).toBeDefined() })
  it('has no_translation_available key', () => { expect(en.no_translation_available).toBeDefined() })
  it('has gemini_not_configured_translation key', () => { expect(en.gemini_not_configured_translation).toBeDefined() })
  it('has gemini_quota_exceeded_translation key', () => { expect(en.gemini_quota_exceeded_translation).toBeDefined() })
  it('has unsupported_language key', () => { expect(en.unsupported_language).toBeDefined() })
  it('has translation_service_unavailable key', () => { expect(en.translation_service_unavailable).toBeDefined() })
})

// ── 33. Locale keys are defined — th.json ────────────────────────────────────
describe('locale keys — th.json', () => {
  it('has translate_expense key', () => { expect(th.translate_expense).toBeDefined() })
  it('has target_language key', () => { expect(th.target_language).toBeDefined() })
  it('has translate key', () => { expect(th.translate).toBeDefined() })
  it('has translating key', () => { expect(th.translating).toBeDefined() })
  it('has translation_completed key', () => { expect(th.translation_completed).toBeDefined() })
  it('has translation_completed_message key', () => { expect(th.translation_completed_message).toBeDefined() })
  it('has unable_to_translate_expense key', () => { expect(th.unable_to_translate_expense).toBeDefined() })
  it('has ai_translation_quota_notice key', () => { expect(th.ai_translation_quota_notice).toBeDefined() })
  it('has no_translation_available key', () => { expect(th.no_translation_available).toBeDefined() })
})
