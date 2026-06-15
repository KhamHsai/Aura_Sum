/**
 * Receipt upload view tests.
 * All API and Gemini calls are mocked — no real network required.
 */
import { it, expect, describe, beforeEach, afterEach, vi } from 'vitest'
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
  showLoadingAlert: vi.fn().mockResolvedValue(undefined),
  closeAlert: vi.fn(),
}))

const mockPush = vi.fn()
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ push: mockPush }) }
})

import * as receiptApi from '../api/receiptApi'
import * as alerts from '../utils/alerts'

const mockUploadReceipt = vi.mocked(receiptApi.uploadReceipt)
const mockExtractReceipt = vi.mocked(receiptApi.extractReceipt)
const mockShowSuccess = vi.mocked(alerts.showSuccessAlert)
const mockShowError = vi.mocked(alerts.showErrorAlert)

// ── URL mocks ─────────────────────────────────────────────────────────────────

const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
const mockRevokeObjectURL = vi.fn()

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeReceipt: Receipt = {
  id: 10,
  user_id: 42,
  expense_id: null,
  original_filename: 'receipt.jpg',
  stored_filename: 'uuid-receipt.jpg',
  mime_type: 'image/jpeg',
  file_size: 102400,
  upload_status: 'uploaded',
  uploaded_at: '2024-06-01T10:00:00',
}

const fakeExpense = { id: 55 }

// ── Helpers ───────────────────────────────────────────────────────────────────

function buildI18n(locale = 'en') {
  return createI18n({ legacy: false, locale, fallbackLocale: 'en', messages: { en, th } })
}

const StubView = defineComponent({ template: '<div />' })

async function mountUpload(locale = 'en') {
  const { default: ReceiptUploadView } = await import('../views/ReceiptUploadView.vue')
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/receipts', name: 'receipts', component: StubView },
      { path: '/receipts/upload', name: 'receipt-upload', component: StubView },
      { path: '/expenses/:id/edit', name: 'expense-edit', component: StubView },
    ],
  })
  router.push('/receipts/upload')
  await router.isReady()
  return mount(ReceiptUploadView, {
    global: {
      plugins: [router, buildI18n(locale)],
      stubs: { AppLayout: { template: '<div><slot /></div>' } },
    },
  })
}

function makeFile(name = 'receipt.jpg', type = 'image/jpeg', size = 1024): File {
  const blob = new Blob(['x'.repeat(size)], { type })
  return new File([blob], name, { type })
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  mockPush.mockClear()
  mockShowSuccess.mockResolvedValue(undefined as never)
  mockShowError.mockResolvedValue(undefined as never)
  Object.defineProperty(URL, 'createObjectURL', { value: mockCreateObjectURL, writable: true, configurable: true })
  Object.defineProperty(URL, 'revokeObjectURL', { value: mockRevokeObjectURL, writable: true, configurable: true })
})

afterEach(() => {
  vi.restoreAllMocks()
})

// ── 1. Upload page shows file input ──────────────────────────────────────────
it('upload page renders a file input', async () => {
  const wrapper = await mountUpload()
  expect(wrapper.find('#ru-file-input').exists()).toBe(true)
})

// ── 2. Upload page shows Upload and Extract button ────────────────────────────
it('upload page shows the Upload and Extract button', async () => {
  const wrapper = await mountUpload()
  expect(wrapper.find('#ru-submit-btn').exists()).toBe(true)
  expect(wrapper.text()).toContain(en.upload_and_extract)
})

// ── 3. No-file validation ─────────────────────────────────────────────────────
it('submit button is disabled when no file is selected', async () => {
  const wrapper = await mountUpload()
  const btn = wrapper.find('#ru-submit-btn')
  expect((btn.element as HTMLButtonElement).disabled).toBe(true)
})

// ── 4. Unsupported type validation ────────────────────────────────────────────
it('shows unsupported file error for disallowed MIME type', async () => {
  const wrapper = await mountUpload()
  const file = makeFile('doc.txt', 'text/plain')
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  expect(wrapper.text()).toContain(en.unsupported_file)
})

// ── 5. File size validation ───────────────────────────────────────────────────
it('shows file too large error for oversized file', async () => {
  const wrapper = await mountUpload()
  // 11 MB > 10 MB limit
  const file = makeFile('big.jpg', 'image/jpeg', 11 * 1024 * 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  expect(wrapper.text()).toContain(en.file_too_large)
})

// ── 6. Image preview is created ──────────────────────────────────────────────
it('creates an object URL for an image file', async () => {
  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  expect(mockCreateObjectURL).toHaveBeenCalledWith(file)
})

// ── 7. Object URL is cleaned up on unmount ────────────────────────────────────
it('revokes the object URL when the component is unmounted', async () => {
  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  wrapper.unmount()
  expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
})

// ── 8. PDF does not attempt image preview ────────────────────────────────────
it('does not call createObjectURL for a PDF file', async () => {
  const wrapper = await mountUpload()
  const file = makeFile('doc.pdf', 'application/pdf', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  expect(mockCreateObjectURL).not.toHaveBeenCalled()
})

// ── 9. PDF shows pdf indicator text ──────────────────────────────────────────
it('shows PDF indicator text for a PDF file', async () => {
  const wrapper = await mountUpload()
  const file = makeFile('doc.pdf', 'application/pdf', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  expect(wrapper.text()).toContain(en.pdf_file)
})

// ── 10. Submit button is disabled while busy ─────────────────────────────────
it('submit button is disabled while uploading', async () => {
  // Upload never resolves during this test
  mockUploadReceipt.mockReturnValue(new Promise(() => {}))

  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  const btn = wrapper.find('#ru-submit-btn')
  await btn.trigger('click')
  await flushPromises()

  expect((btn.element as HTMLButtonElement).disabled).toBe(true)
})

// ── 11. Successful upload starts extraction ───────────────────────────────────
it('after successful upload, calls extractReceipt', async () => {
  mockUploadReceipt.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockResolvedValue(fakeExpense)

  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  await wrapper.find('#ru-submit-btn').trigger('click')
  await flushPromises()

  expect(mockExtractReceipt).toHaveBeenCalledWith(fakeReceipt.id)
})

// ── 12. Successful extraction redirects to expense edit ──────────────────────
it('after successful extraction, navigates to expense edit page', async () => {
  mockUploadReceipt.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockResolvedValue(fakeExpense)

  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  await wrapper.find('#ru-submit-btn').trigger('click')
  await flushPromises()

  expect(mockPush).toHaveBeenCalledWith({ name: 'expense-edit', params: { id: 55 } })
})

// ── 13. Upload failure shows error alert ─────────────────────────────────────
it('upload failure shows error alert', async () => {
  mockUploadReceipt.mockRejectedValue(new Error('Network error'))

  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  await wrapper.find('#ru-submit-btn').trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockShowSuccess).not.toHaveBeenCalled()
})

// ── 14. Extraction failure shows error alert ──────────────────────────────────
it('extraction failure shows error alert', async () => {
  mockUploadReceipt.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockRejectedValue(new Error('Extraction error'))

  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  await wrapper.find('#ru-submit-btn').trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledOnce()
  expect(mockPush).not.toHaveBeenCalled()
})

// ── 15. Gemini configuration error maps to safe message ──────────────────────
it('503 extraction error shows gemini not configured message', async () => {
  mockUploadReceipt.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockRejectedValue({ response: { status: 503, data: { detail: 'Gemini API key is not configured' } } })

  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  await wrapper.find('#ru-submit-btn').trigger('click')
  await flushPromises()

  expect(mockShowError).toHaveBeenCalledWith(en.extraction_failed, en.gemini_not_configured)
})

// ── 16. Success shows success alert ──────────────────────────────────────────
it('successful upload and extract shows success alert', async () => {
  mockUploadReceipt.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockResolvedValue(fakeExpense)

  const wrapper = await mountUpload()
  const file = makeFile('receipt.jpg', 'image/jpeg', 1024)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')

  await wrapper.find('#ru-submit-btn').trigger('click')
  await flushPromises()

  expect(mockShowSuccess).toHaveBeenCalledWith(en.receipt_uploaded, en.receipt_uploaded_message)
})

// ── 17. AI quota notice is shown ─────────────────────────────────────────────
it('upload page shows the AI quota notice', async () => {
  const wrapper = await mountUpload()
  expect(wrapper.text()).toContain(en.ai_quota_notice)
})

// ── 18. Thai locale labels ────────────────────────────────────────────────────
describe('locale', () => {
  it('shows Thai upload_and_extract label', async () => {
    const wrapper = await mountUpload('th')
    expect(wrapper.text()).toContain(th.upload_and_extract)
  })

  it('shows Thai ai_quota_notice', async () => {
    const wrapper = await mountUpload('th')
    expect(wrapper.text()).toContain(th.ai_quota_notice)
  })
})

// ── 19. No Gemini call is made in tests ──────────────────────────────────────
it('extractReceipt is only called after upload, never on page mount', async () => {
  mockUploadReceipt.mockResolvedValue(fakeReceipt)
  mockExtractReceipt.mockResolvedValue(fakeExpense)
  await mountUpload()
  await flushPromises()
  // No file selected → no calls at all
  expect(mockExtractReceipt).not.toHaveBeenCalled()
})

// ── 20. Selected file details shown ──────────────────────────────────────────
it('shows selected file name and type after valid selection', async () => {
  const wrapper = await mountUpload()
  const file = makeFile('invoice.png', 'image/png', 2048)
  const input = wrapper.find('#ru-file-input')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  expect(wrapper.text()).toContain('invoice.png')
  expect(wrapper.text()).toContain('image/png')
})
