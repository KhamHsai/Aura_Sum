/**
 * Tests for the exportExpenses() API function in expenseApi.ts
 * Verifies API contract: endpoint, responseType, headers returned.
 * The Axios client is mocked — no real network calls are made.
 */
import { it, expect, vi, beforeEach, describe } from 'vitest'
import { XLSX_MIME } from '../utils/download'

// ── Mock the Axios client ─────────────────────────────────────────────────────
// Note: vi.mock factories are hoisted to top-of-file, so variables declared
// after them in the source are not yet initialised. Define the mock fn inline.

vi.mock('../api/axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

// ── Import after mocks are in place ──────────────────────────────────────────

import { exportExpenses } from '../api/expenseApi'
import apiClient from '../api/axios'

const mockGet = vi.mocked(apiClient.get)

// ── Fixtures ──────────────────────────────────────────────────────────────────

const fakeBlob = new Blob(['xlsx-binary-data'], { type: XLSX_MIME })
const fakeContentDisposition = 'attachment; filename="smart_receipt_expenses_2024-06-14.xlsx"'

function makeSuccessResponse(overrides: Record<string, unknown> = {}) {
  return {
    data: fakeBlob,
    headers: {
      'content-disposition': fakeContentDisposition,
      'content-type': XLSX_MIME,
    },
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

// ── Tests ─────────────────────────────────────────────────────────────────────

// 1. Export API calls GET /expenses/export
it('exportExpenses calls GET /expenses/export', async () => {
  mockGet.mockResolvedValue(makeSuccessResponse())
  await exportExpenses()
  expect(mockGet).toHaveBeenCalledOnce()
  expect(mockGet.mock.calls[0][0]).toBe('/expenses/export')
})

// 2. Export API uses responseType: 'blob'
it('exportExpenses passes responseType blob to Axios', async () => {
  mockGet.mockResolvedValue(makeSuccessResponse())
  await exportExpenses()
  const config = mockGet.mock.calls[0][1]
  expect(config).toMatchObject({ responseType: 'blob' })
})

// 3. Export API uses the existing Axios client (mockGet is the client's .get)
it('exportExpenses uses the shared apiClient instance', async () => {
  mockGet.mockResolvedValue(makeSuccessResponse())
  await exportExpenses()
  expect(mockGet).toHaveBeenCalledOnce()
})

// 4. Content-Disposition header is returned in the result
it('exportExpenses returns the content-disposition header', async () => {
  mockGet.mockResolvedValue(makeSuccessResponse())
  const result = await exportExpenses()
  expect(result.contentDisposition).toBe(fakeContentDisposition)
})

// 5. Content-Type header is returned in the result
it('exportExpenses returns the content-type header', async () => {
  mockGet.mockResolvedValue(makeSuccessResponse())
  const result = await exportExpenses()
  expect(result.contentType).toBe(XLSX_MIME)
})

// Blob is returned in the result
it('exportExpenses returns the blob from the response', async () => {
  mockGet.mockResolvedValue(makeSuccessResponse())
  const result = await exportExpenses()
  expect(result.blob).toBe(fakeBlob)
})

// Null header fallback — missing Content-Disposition returns null
it('exportExpenses returns null contentDisposition when header is missing', async () => {
  mockGet.mockResolvedValue({
    data: fakeBlob,
    headers: { 'content-type': XLSX_MIME },
  })
  const result = await exportExpenses()
  expect(result.contentDisposition).toBeNull()
})

// Null header fallback — missing Content-Type returns null
it('exportExpenses returns null contentType when header is missing', async () => {
  mockGet.mockResolvedValue({
    data: fakeBlob,
    headers: { 'content-disposition': fakeContentDisposition },
  })
  const result = await exportExpenses()
  expect(result.contentType).toBeNull()
})

// API error propagates to caller
it('exportExpenses rejects when the Axios call fails', async () => {
  mockGet.mockRejectedValue(new Error('Network Error'))
  await expect(exportExpenses()).rejects.toThrow('Network Error')
})

describe('result shape', () => {
  it('result has blob, contentDisposition, and contentType fields', async () => {
    mockGet.mockResolvedValue(makeSuccessResponse())
    const result = await exportExpenses()
    expect(result).toHaveProperty('blob')
    expect(result).toHaveProperty('contentDisposition')
    expect(result).toHaveProperty('contentType')
  })
})
