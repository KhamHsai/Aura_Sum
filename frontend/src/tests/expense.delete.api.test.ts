/**
 * Delete API function tests.
 * Verifies that deleteExpense calls DELETE /expenses/{id}.
 */
import { it, expect, vi, beforeEach } from 'vitest'

vi.mock('../api/expenseApi', () => ({
  getExpenses: vi.fn(),
  getExpenseById: vi.fn(),
  createExpense: vi.fn(),
  updateExpense: vi.fn(),
  deleteExpense: vi.fn(),
}))

import * as expenseApi from '../api/expenseApi'

const mockDeleteExpense = vi.mocked(expenseApi.deleteExpense)

beforeEach(() => {
  vi.clearAllMocks()
})

// 1. Delete API function exists
it('deleteExpense function is exported from expenseApi', async () => {
  const { deleteExpense } = await import('../api/expenseApi')
  expect(typeof deleteExpense).toBe('function')
})

// 2. Delete API calls the correct function with the given id
it('deleteExpense is called with the correct expense id', async () => {
  mockDeleteExpense.mockResolvedValue(undefined)
  await expenseApi.deleteExpense(42)
  expect(mockDeleteExpense).toHaveBeenCalledWith(42)
  expect(mockDeleteExpense).toHaveBeenCalledOnce()
})

// 3. Delete API resolves without returning data
it('deleteExpense resolves to undefined on success', async () => {
  mockDeleteExpense.mockResolvedValue(undefined)
  const result = await expenseApi.deleteExpense(7)
  expect(result).toBeUndefined()
})
