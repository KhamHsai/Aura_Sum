/**
 * Tests for src/utils/download.ts
 * Covers filename parsing, blob validation, blob download, and error parsing.
 * No real file download occurs — URL and DOM APIs are mocked.
 */
import { it, expect, describe, beforeEach, vi } from 'vitest'
import {
  getFilenameFromContentDisposition,
  downloadBlob,
  isValidExcelBlob,
  parseBlobErrorMessage,
  FALLBACK_FILENAME,
  XLSX_MIME,
} from '../utils/download'

// ── Mock URL and DOM APIs ──────────────────────────────────────────────────────

const mockObjectURL = 'blob:http://localhost/fake-object-url'
const mockCreateObjectURL = vi.fn(() => mockObjectURL)
const mockRevokeObjectURL = vi.fn()
const mockClick = vi.fn()
const mockAppendChild = vi.fn()
const mockRemoveChild = vi.fn()

// Store the created anchor for inspection
let createdAnchor: { href: string; download: string; click: () => void; remove: () => void } | null = null

beforeEach(() => {
  vi.clearAllMocks()
  createdAnchor = null

  // jsdom does not implement createObjectURL / revokeObjectURL
  Object.defineProperty(URL, 'createObjectURL', { value: mockCreateObjectURL, writable: true })
  Object.defineProperty(URL, 'revokeObjectURL', { value: mockRevokeObjectURL, writable: true })

  // Intercept createElement('a') to capture the anchor without touching the DOM
  vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
    if (tag === 'a') {
      createdAnchor = { href: '', download: '', click: mockClick, remove: mockRemoveChild as unknown as () => void }
      return createdAnchor as unknown as HTMLElement
    }
    return document.createElement(tag)
  })

  vi.spyOn(document.body, 'appendChild').mockImplementation(mockAppendChild as unknown as typeof document.body.appendChild)
})

// ── getFilenameFromContentDisposition ─────────────────────────────────────────

describe('getFilenameFromContentDisposition', () => {
  // 6. Quoted filename is parsed
  it('parses a quoted filename', () => {
    expect(getFilenameFromContentDisposition('attachment; filename="expenses.xlsx"')).toBe('expenses.xlsx')
  })

  // 7. Unquoted filename is parsed
  it('parses an unquoted filename', () => {
    expect(getFilenameFromContentDisposition('attachment; filename=expenses.xlsx')).toBe('expenses.xlsx')
  })

  // 8. UTF-8 RFC 5987 filename format is parsed
  it('parses a UTF-8 RFC 5987 filename', () => {
    expect(
      getFilenameFromContentDisposition("attachment; filename*=UTF-8''smart_receipt_expenses_2024-01-15.xlsx"),
    ).toBe('smart_receipt_expenses_2024-01-15.xlsx')
  })

  // 9. Missing filename returns null (caller uses fallback)
  it('returns null when no filename is present', () => {
    expect(getFilenameFromContentDisposition('attachment')).toBeNull()
  })

  it('returns null for a null header', () => {
    expect(getFilenameFromContentDisposition(null)).toBeNull()
  })

  it('returns null for an empty header', () => {
    expect(getFilenameFromContentDisposition('')).toBeNull()
  })

  // 10. Unsafe path characters are removed
  it('strips forward slashes from the filename', () => {
    const result = getFilenameFromContentDisposition('attachment; filename="../../etc/passwd.xlsx"')
    expect(result).not.toContain('/')
    expect(result).not.toContain('..')
  })

  it('strips backslashes from the filename', () => {
    const result = getFilenameFromContentDisposition('attachment; filename="..\\evil.xlsx"')
    expect(result).not.toContain('\\')
  })

  it('strips path traversal sequences', () => {
    const result = getFilenameFromContentDisposition('attachment; filename="../secret.xlsx"')
    expect(result).not.toContain('..')
  })

  it('returns the backend-provided filename for a real Content-Disposition header', () => {
    const header = 'attachment; filename="smart_receipt_expenses_2024-06-14.xlsx"'
    expect(getFilenameFromContentDisposition(header)).toBe('smart_receipt_expenses_2024-06-14.xlsx')
  })
})

// ── FALLBACK_FILENAME ─────────────────────────────────────────────────────────

it('FALLBACK_FILENAME is a safe xlsx filename', () => {
  expect(FALLBACK_FILENAME).toBe('expenses-export.xlsx')
})

// ── isValidExcelBlob ───────────────────────────────────────────────────────────

describe('isValidExcelBlob', () => {
  it('accepts a blob with the exact xlsx MIME type', () => {
    const blob = new Blob(['data'], { type: XLSX_MIME })
    expect(isValidExcelBlob(blob, XLSX_MIME)).toBe(true)
  })

  it('accepts a blob with octet-stream content type', () => {
    const blob = new Blob(['data'], { type: 'application/octet-stream' })
    expect(isValidExcelBlob(blob, 'application/octet-stream')).toBe(true)
  })

  it('accepts a blob when content type is null (no header)', () => {
    const blob = new Blob(['data'])
    expect(isValidExcelBlob(blob, null)).toBe(true)
  })

  it('rejects an empty blob', () => {
    const blob = new Blob([])
    expect(isValidExcelBlob(blob, XLSX_MIME)).toBe(false)
  })

  it('rejects a blob with a clearly wrong content type', () => {
    const blob = new Blob(['<html>error</html>'], { type: 'text/html' })
    expect(isValidExcelBlob(blob, 'text/html')).toBe(false)
  })

  it('accepts a blob with application/binary content type', () => {
    const blob = new Blob(['data'], { type: 'application/binary' })
    expect(isValidExcelBlob(blob, 'application/binary')).toBe(true)
  })
})

// ── downloadBlob ──────────────────────────────────────────────────────────────

describe('downloadBlob', () => {
  const fakeBlob = new Blob(['xlsx data'], { type: XLSX_MIME })

  // 11. Blob download creates an object URL
  it('creates an object URL from the blob', () => {
    downloadBlob(fakeBlob, 'expenses.xlsx')
    expect(mockCreateObjectURL).toHaveBeenCalledWith(fakeBlob)
  })

  // 12. Temporary anchor is created
  it('creates a temporary anchor element', () => {
    downloadBlob(fakeBlob, 'expenses.xlsx')
    expect(document.createElement).toHaveBeenCalledWith('a')
  })

  // 13. Anchor receives correct download filename
  it('sets the correct download filename on the anchor', () => {
    downloadBlob(fakeBlob, 'my-file.xlsx')
    expect(createdAnchor?.download).toBe('my-file.xlsx')
  })

  it('sets the object URL as the href on the anchor', () => {
    downloadBlob(fakeBlob, 'expenses.xlsx')
    expect(createdAnchor?.href).toBe(mockObjectURL)
  })

  // 14. Anchor click is triggered
  it('clicks the anchor to trigger the download', () => {
    downloadBlob(fakeBlob, 'expenses.xlsx')
    expect(mockClick).toHaveBeenCalledOnce()
  })

  // 15. Temporary anchor is removed
  it('removes the temporary anchor after clicking', () => {
    downloadBlob(fakeBlob, 'expenses.xlsx')
    expect(mockRemoveChild).toHaveBeenCalledOnce()
  })

  // 16. Object URL is revoked
  it('revokes the object URL after download', () => {
    downloadBlob(fakeBlob, 'expenses.xlsx')
    expect(mockRevokeObjectURL).toHaveBeenCalledWith(mockObjectURL)
  })

  // 17. Cleanup occurs even if click throws
  it('still revokes the URL and removes anchor when click throws', () => {
    mockClick.mockImplementationOnce(() => { throw new Error('click failed') })

    expect(() => downloadBlob(fakeBlob, 'expenses.xlsx')).toThrow('click failed')

    // Cleanup must still have run
    expect(mockRevokeObjectURL).toHaveBeenCalledWith(mockObjectURL)
    expect(mockRemoveChild).toHaveBeenCalledOnce()
  })
})

// ── parseBlobErrorMessage ─────────────────────────────────────────────────────

describe('parseBlobErrorMessage', () => {
  // 26. Backend JSON error Blob is parsed safely
  it('extracts a string detail message from a FastAPI JSON error blob', async () => {
    const blob = new Blob([JSON.stringify({ detail: 'No expenses available for export' })], { type: 'application/json' })
    const msg = await parseBlobErrorMessage(blob)
    expect(msg).toBe('No expenses available for export')
  })

  // 27. FastAPI array error is parsed safely
  it('extracts the first msg from a FastAPI validation error array', async () => {
    const blob = new Blob(
      [JSON.stringify({ detail: [{ loc: ['body'], msg: 'field required', type: 'missing' }] })],
      { type: 'application/json' },
    )
    const msg = await parseBlobErrorMessage(blob)
    expect(msg).toBe('field required')
  })

  // 28. Invalid JSON blob uses generic message (returns null)
  it('returns null for a non-JSON blob', async () => {
    const blob = new Blob(['not json at all'])
    const msg = await parseBlobErrorMessage(blob)
    expect(msg).toBeNull()
  })

  it('returns null when detail is an empty string', async () => {
    const blob = new Blob([JSON.stringify({ detail: '' })])
    const msg = await parseBlobErrorMessage(blob)
    expect(msg).toBeNull()
  })

  it('returns null when the detail message exceeds 200 characters', async () => {
    const longMessage = 'x'.repeat(201)
    const blob = new Blob([JSON.stringify({ detail: longMessage })])
    const msg = await parseBlobErrorMessage(blob)
    expect(msg).toBeNull()
  })

  it('returns null for an empty blob', async () => {
    const blob = new Blob([''])
    const msg = await parseBlobErrorMessage(blob)
    expect(msg).toBeNull()
  })
})
