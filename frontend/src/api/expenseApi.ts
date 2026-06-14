import apiClient from './axios'
import type { Expense, ExpenseCreateRequest, ExpenseUpdateRequest } from '../types/expense'
import type { TranslationLanguage, ExpenseTranslationResponse } from '../types/translation'

// GET /api/expenses — returns all expenses for the authenticated user (newest first)
export async function getExpenses(): Promise<Expense[]> {
  const response = await apiClient.get<Expense[]>('/expenses')
  return response.data
}

// GET /api/expenses/{id} — returns a single expense with its items
export async function getExpenseById(expenseId: number): Promise<Expense> {
  const response = await apiClient.get<Expense>(`/expenses/${expenseId}`)
  return response.data
}

// POST /api/expenses — create a new manual expense
export async function createExpense(data: ExpenseCreateRequest): Promise<Expense> {
  const response = await apiClient.post<Expense>('/expenses', data)
  return response.data
}

// PUT /api/expenses/{id} — update an existing expense
export async function updateExpense(expenseId: number, data: ExpenseUpdateRequest): Promise<Expense> {
  const response = await apiClient.put<Expense>(`/expenses/${expenseId}`, data)
  return response.data
}

// DELETE /api/expenses/{id} — soft-delete an expense; returns { message: string }
export async function deleteExpense(expenseId: number): Promise<void> {
  await apiClient.delete(`/expenses/${expenseId}`)
}

// POST /api/expenses/{id}/confirm — confirm an AI-extracted draft expense after review
// No request body required. Returns the updated Expense with is_confirmed: true.
export async function confirmExpense(expenseId: number): Promise<Expense> {
  const response = await apiClient.post<Expense>(`/expenses/${expenseId}/confirm`)
  return response.data
}

// POST /api/expenses/{id}/translate — translate dynamic expense text between English and Thai.
// Translates title, notes, and item names. Merchant name is not translated by the backend.
export async function translateExpense(
  expenseId: number,
  targetLanguage: TranslationLanguage,
): Promise<ExpenseTranslationResponse> {
  const response = await apiClient.post<ExpenseTranslationResponse>(
    `/expenses/${expenseId}/translate`,
    { target_language: targetLanguage },
  )
  return response.data
}

// ── Excel Export ──────────────────────────────────────────────────────────────

export interface ExpenseExportResult {
  blob: Blob
  contentDisposition: string | null
  contentType: string | null
}

// GET /api/expenses/export — download all active expenses as an Excel file.
// Uses responseType: 'blob' so Axios returns raw binary data.
export async function exportExpenses(): Promise<ExpenseExportResult> {
  const response = await apiClient.get('/expenses/export', {
    responseType: 'blob',
  })
  return {
    blob: response.data as Blob,
    contentDisposition: (response.headers['content-disposition'] as string) ?? null,
    contentType: (response.headers['content-type'] as string) ?? null,
  }
}
