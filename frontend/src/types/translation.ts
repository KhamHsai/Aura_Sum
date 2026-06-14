/**
 * Translation types — match the real backend schemas exactly.
 *
 * POST /api/expenses/{expense_id}/translate
 *   Request:  { target_language: 'en' | 'th' }
 *   Response: ExpenseTranslationResponse
 *
 * Note: The backend translates title, notes, and item names only.
 * Merchant name is NOT translated by the backend.
 */

export type TranslationLanguage = 'en' | 'th'

/** Request body sent to POST /api/expenses/{id}/translate */
export interface ExpenseTranslationRequest {
  target_language: TranslationLanguage
}

/** One translated item in the translation response */
export interface TranslatedExpenseItem {
  item_id: number
  original_name: string | null
  name_en: string | null
  name_th: string | null
  translated_name: string | null
}

/** Full response from POST /api/expenses/{id}/translate */
export interface ExpenseTranslationResponse {
  expense_id: number
  source_language: TranslationLanguage
  target_language: TranslationLanguage
  translated_title: string | null
  translated_notes: string | null
  items: TranslatedExpenseItem[]
  reused_existing_translation: boolean
}
