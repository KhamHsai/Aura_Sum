/**
 * Small helpers for safe filename parsing and browser blob downloads.
 * No third-party library required — standard browser APIs only.
 */

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
const FALLBACK_FILENAME = 'expenses-export.xlsx'

/**
 * Extract a safe filename from a Content-Disposition header.
 *
 * Supports these common forms:
 *   attachment; filename="expenses.xlsx"
 *   attachment; filename=expenses.xlsx
 *   attachment; filename*=UTF-8''expenses.xlsx
 *
 * Any directory separators, path traversal sequences, or control characters
 * are stripped so the result is always a plain local filename.
 *
 * Returns null when no usable filename is found.
 */
export function getFilenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null

  // Try filename*=UTF-8''<encoded> first (RFC 5987)
  const rfc5987Match = header.match(/filename\*\s*=\s*UTF-8''([^\s;]+)/i)
  if (rfc5987Match) {
    try {
      return sanitizeFilename(decodeURIComponent(rfc5987Match[1]))
    } catch {
      // decodeURIComponent failed — fall through to the next form
    }
  }

  // Try filename="value" (quoted)
  const quotedMatch = header.match(/filename\s*=\s*"([^"]+)"/i)
  if (quotedMatch) {
    return sanitizeFilename(quotedMatch[1])
  }

  // Try filename=value (unquoted)
  const unquotedMatch = header.match(/filename\s*=\s*([^\s;]+)/i)
  if (unquotedMatch) {
    return sanitizeFilename(unquotedMatch[1])
  }

  return null
}

/**
 * Strip directory separators, path traversal, and control characters.
 * Returns the sanitized filename, or null if nothing is left.
 */
function sanitizeFilename(raw: string): string | null {
  // Remove forward and back slashes, dots followed by dots (traversal), and control chars
  // eslint-disable-next-line no-control-regex
  const safe = raw.replace(/[/\\]/g, '').replace(/\.\./g, '').replace(/[\x00-\x1f]/g, '').trim()
  return safe.length > 0 ? safe : null
}

/**
 * Validate that a blob looks like a real Excel file.
 * Accepts the exact XLSX MIME type, generic binary types, and octet-stream.
 * Rejects clearly wrong types (e.g. text/html from an error page).
 */
export function isValidExcelBlob(blob: Blob, contentType: string | null): boolean {
  if (!blob || blob.size === 0) return false
  if (!contentType) return true // no header — assume valid if size > 0
  const type = contentType.split(';')[0].trim().toLowerCase()
  return (
    type === XLSX_MIME ||
    type === 'application/octet-stream' ||
    type === 'application/binary' ||
    type === '' // some servers omit the type
  )
}

/**
 * Trigger a browser file download from a Blob.
 * Creates a temporary object URL and anchor, clicks it, then cleans up.
 * Cleanup runs even when the click throws.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)

  try {
    link.click()
  } finally {
    link.remove()
    URL.revokeObjectURL(url)
  }
}

/**
 * Read a Blob as text and try to parse a safe user-facing message from
 * a FastAPI JSON error body.
 *
 * FastAPI error shapes:
 *   { "detail": "message string" }
 *   { "detail": [{ "loc": [...], "msg": "message", "type": "..." }] }
 *
 * Returns null when the blob is not readable JSON or the message is
 * suspiciously long (> 200 chars) — callers should show a generic fallback.
 */
export async function parseBlobErrorMessage(blob: Blob): Promise<string | null> {
  try {
    // Use FileReader for broad browser and jsdom compatibility.
    // Blob.text() is not available in all jsdom versions.
    const text = await readBlobAsText(blob)
    const json = JSON.parse(text)

    if (typeof json.detail === 'string') {
      const msg = json.detail.trim()
      return msg.length > 0 && msg.length <= 200 ? msg : null
    }

    if (Array.isArray(json.detail) && json.detail.length > 0) {
      const first = json.detail[0]
      if (typeof first?.msg === 'string') {
        const msg = first.msg.trim()
        return msg.length > 0 && msg.length <= 200 ? msg : null
      }
    }
  } catch {
    // Not JSON or unreadable — return null so the caller uses a generic message
  }
  return null
}

export { XLSX_MIME, FALLBACK_FILENAME }

/**
 * Read a Blob as a UTF-8 string using FileReader.
 * Works in all browsers and jsdom environments.
 */
function readBlobAsText(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(reader.error)
    reader.readAsText(blob)
  })
}
