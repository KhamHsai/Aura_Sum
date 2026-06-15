/**
 * Unit tests for the translateExpense API function.
 * Verifies it calls the correct endpoint with the correct body using the existing Axios client.
 * No real Gemini requests are made.
 */
import { it, expect, describe, vi, beforeEach } from 'vitest'

const { mockPost } = vi.hoisted(() => {
  return { mockPost: vi.fn() }
})

vi.mock('../api/axios', () => ({
  default: { post: mockPost },
}))

import { translateExpense } from '../api/expenseApi'

const fakeTranslationResponse = {
  expense_id: 5,
  source_language: 'th' as const,
  target_language: 'en' as const,
  translated_notes: 'Paid in full',
  items: [
    {
      item_id: 10,
      original_name: 'ข้าวผัด',
      name_en: 'Fried Rice',
      name_th: 'ข้าวผัด',
      translated_name: 'Fried Rice',
    },
  ],
  reused_existing_translation: false,
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('translateExpense', () => {
  // 1. Calls POST /expenses/{id}/translate
  it('calls POST /expenses/{id}/translate with correct path', async () => {
    mockPost.mockResolvedValue({ data: fakeTranslationResponse })
    await translateExpense(5, 'en')
    expect(mockPost).toHaveBeenCalledWith('/expenses/5/translate', { target_language: 'en' })
  })

  // 2. English target sends target_language: "en"
  it('sends target_language "en" in the request body', async () => {
    mockPost.mockResolvedValue({ data: fakeTranslationResponse })
    await translateExpense(5, 'en')
    expect(mockPost.mock.calls[0][1]).toEqual({ target_language: 'en' })
  })

  // 3. Thai target sends target_language: "th"
  it('sends target_language "th" in the request body', async () => {
    const thaiResponse = { ...fakeTranslationResponse, target_language: 'th' as const }
    mockPost.mockResolvedValue({ data: thaiResponse })
    await translateExpense(5, 'th')
    expect(mockPost.mock.calls[0][1]).toEqual({ target_language: 'th' })
  })

  // 4. Uses the existing Axios client
  it('uses the existing Axios client (not raw fetch)', async () => {
    mockPost.mockResolvedValue({ data: fakeTranslationResponse })
    await translateExpense(5, 'en')
    expect(mockPost).toHaveBeenCalledOnce()
  })

  // 5. Returns the typed translation response
  it('returns the translation response from response.data', async () => {
    mockPost.mockResolvedValue({ data: fakeTranslationResponse })
    const result = await translateExpense(5, 'en')
    expect(result.expense_id).toBe(5)
    expect(result.translated_notes).toBe('Paid in full')
    expect(result.items).toHaveLength(1)
    expect(result.items[0].item_id).toBe(10)
  })

  // 6. Uses the provided expense ID in the URL
  it('uses the provided expense ID in the URL', async () => {
    mockPost.mockResolvedValue({ data: { ...fakeTranslationResponse, expense_id: 99 } })
    await translateExpense(99, 'en')
    expect(mockPost).toHaveBeenCalledWith('/expenses/99/translate', { target_language: 'en' })
  })

  // 7. Propagates API errors
  it('propagates API errors', async () => {
    mockPost.mockRejectedValue({ response: { status: 503 } })
    await expect(translateExpense(5, 'en')).rejects.toMatchObject({ response: { status: 503 } })
  })

  // 8. Handles response with empty items array
  it('returns response with empty items array when expense has no items', async () => {
    const noItems = { ...fakeTranslationResponse, items: [] }
    mockPost.mockResolvedValue({ data: noItems })
    const result = await translateExpense(5, 'en')
    expect(result.items).toHaveLength(0)
  })

  // 9. Handles reused_existing_translation flag
  it('returns reused_existing_translation when backend reuses saved translation', async () => {
    const reused = { ...fakeTranslationResponse, reused_existing_translation: true }
    mockPost.mockResolvedValue({ data: reused })
    const result = await translateExpense(5, 'en')
    expect(result.reused_existing_translation).toBe(true)
  })
})
