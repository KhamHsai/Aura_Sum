/**
 * Receipt API module tests.
 * Verifies correct endpoints, FormData usage, and field names.
 * All HTTP calls are mocked — no real backend required.
 */
import { it, expect, describe, beforeEach, vi } from 'vitest'

// ── Mock the Axios client ──────────────────────────────────────────────────────
vi.mock('../api/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import apiClient from '../api/axios'
import { getReceipts, getReceiptById, uploadReceipt, extractReceipt } from '../api/receiptApi'
import type { Receipt } from '../types/receipt'

const mockGet = vi.mocked(apiClient.get)
const mockPost = vi.mocked(apiClient.post)

const fakeReceipt: Receipt = {
  id: 1,
  user_id: 42,
  expense_id: null,
  original_filename: 'receipt.jpg',
  stored_filename: 'uuid-receipt.jpg',
  mime_type: 'image/jpeg',
  file_size: 102400,
  upload_status: 'uploaded',
  uploaded_at: '2024-06-01T10:00:00',
}

const fakeLinkedReceipt: Receipt = { ...fakeReceipt, id: 2, expense_id: 5 }

beforeEach(() => {
  vi.clearAllMocks()
})

// ── 1. getReceipts calls GET /receipts ────────────────────────────────────────
it('getReceipts calls GET /receipts', async () => {
  mockGet.mockResolvedValue({ data: [fakeReceipt] })
  const result = await getReceipts()
  expect(mockGet).toHaveBeenCalledWith('/receipts')
  expect(result).toHaveLength(1)
  expect(result[0].id).toBe(1)
})

// ── 2. getReceiptById calls GET /receipts/{id} ────────────────────────────────
it('getReceiptById calls GET /receipts/1', async () => {
  mockGet.mockResolvedValue({ data: fakeReceipt })
  const result = await getReceiptById(1)
  expect(mockGet).toHaveBeenCalledWith('/receipts/1')
  expect(result.id).toBe(1)
})

// ── 3. uploadReceipt uses FormData ───────────────────────────────────────────
it('uploadReceipt sends a FormData body', async () => {
  mockPost.mockResolvedValue({ data: fakeReceipt })
  const file = new File(['content'], 'receipt.jpg', { type: 'image/jpeg' })
  await uploadReceipt(file)

  expect(mockPost).toHaveBeenCalledOnce()
  const [, body] = mockPost.mock.calls[0]
  expect(body).toBeInstanceOf(FormData)
})

// ── 4. uploadReceipt appends the correct form field name "file" ──────────────
it('uploadReceipt appends the file under the field name "file"', async () => {
  mockPost.mockResolvedValue({ data: fakeReceipt })
  const file = new File(['content'], 'receipt.jpg', { type: 'image/jpeg' })
  await uploadReceipt(file)

  const [, body] = mockPost.mock.calls[0] as [string, FormData]
  expect(body.get('file')).toBe(file)
})

// ── 5. uploadReceipt sends to /receipts/upload ───────────────────────────────
it('uploadReceipt posts to /receipts/upload', async () => {
  mockPost.mockResolvedValue({ data: fakeReceipt })
  const file = new File(['content'], 'receipt.jpg', { type: 'image/jpeg' })
  await uploadReceipt(file)
  expect(mockPost.mock.calls[0][0]).toBe('/receipts/upload')
})

// ── 6. extractReceipt calls POST /receipts/{id}/extract ──────────────────────
it('extractReceipt calls POST /receipts/1/extract', async () => {
  const fakeExpense = { id: 99 }
  mockPost.mockResolvedValue({ data: fakeExpense })
  const result = await extractReceipt(1)
  expect(mockPost).toHaveBeenCalledWith('/receipts/1/extract')
  expect(result.id).toBe(99)
})

// ── 7. getReceiptById with receipt that has expense_id ───────────────────────
it('getReceiptById returns expense_id correctly', async () => {
  mockGet.mockResolvedValue({ data: fakeLinkedReceipt })
  const result = await getReceiptById(2)
  expect(result.expense_id).toBe(5)
})

// ── 8. getReceipts returns empty array ───────────────────────────────────────
it('getReceipts returns empty array when no receipts', async () => {
  mockGet.mockResolvedValue({ data: [] })
  const result = await getReceipts()
  expect(result).toEqual([])
})

// ── 9. uploadReceipt calls onUploadProgress when provided ────────────────────
it('uploadReceipt calls onUploadProgress with percentage', async () => {
  mockPost.mockImplementation((_url, _data, config) => {
    // Simulate a progress event at 50% — cast to satisfy the AxiosProgressEvent type
    config?.onUploadProgress?.({ loaded: 50, total: 100, bytes: 50, lengthComputable: true } as import('axios').AxiosProgressEvent)
    return Promise.resolve({ data: fakeReceipt })
  })

  const file = new File(['content'], 'receipt.jpg', { type: 'image/jpeg' })
  const progressValues: number[] = []
  await uploadReceipt(file, (p) => progressValues.push(p))

  expect(progressValues).toContain(50)
})

// ── 10. uploadReceipt returns a Receipt ──────────────────────────────────────
it('uploadReceipt returns a Receipt object', async () => {
  mockPost.mockResolvedValue({ data: fakeReceipt })
  const file = new File(['content'], 'receipt.jpg', { type: 'image/jpeg' })
  const result = await uploadReceipt(file)
  expect(result.original_filename).toBe('receipt.jpg')
  expect(result.upload_status).toBe('uploaded')
})

// ── 11. Smoke: receipt types have expected shape ──────────────────────────────
describe('Receipt type shape', () => {
  it('fakeReceipt has all expected ReceiptFileResponse fields', () => {
    const fields: (keyof Receipt)[] = [
      'id', 'user_id', 'expense_id', 'original_filename', 'stored_filename',
      'mime_type', 'file_size', 'upload_status', 'uploaded_at',
    ]
    fields.forEach((f) => expect(fakeReceipt).toHaveProperty(f))
  })
})
