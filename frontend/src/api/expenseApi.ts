import apiClient from './axios'
import type { Expense, ExpenseCreateRequest, ExpenseUpdateRequest } from '../types/expense'

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
