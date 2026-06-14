/**
 * Pure helper functions for the dashboard.
 * All functions are side-effect-free and easy to unit-test.
 */
import type { Expense } from '../types/expense'
import type { Receipt } from '../types/receipt'

/** Number of recent expenses to show on the dashboard. */
export const RECENT_EXPENSE_LIMIT = 5

/** Count expenses where is_confirmed === true. */
export function countConfirmedExpenses(expenses: Expense[]): number {
  return expenses.filter((e) => e.is_confirmed).length
}

/** Count expenses where is_confirmed === false. */
export function countDraftExpenses(expenses: Expense[]): number {
  return expenses.filter((e) => !e.is_confirmed).length
}

/** Count receipts that are linked to an expense. */
export function countLinkedReceipts(receipts: Receipt[]): number {
  return receipts.filter((r) => r.expense_id !== null).length
}

/** Count receipts that are not yet linked to an expense. */
export function countUnlinkedReceipts(receipts: Receipt[]): number {
  return receipts.filter((r) => r.expense_id === null).length
}

/**
 * Group expense total amounts by currency.
 * Returns a map of { currencyCode -> numericTotal }.
 * Amounts are strings from the backend; invalid/NaN values are skipped.
 * Currencies are sorted alphabetically for stable display.
 */
export function groupTotalsByCurrency(expenses: Expense[]): { currency: string; total: number }[] {
  const map: Record<string, number> = {}

  for (const expense of expenses) {
    const amount = Number(expense.total_amount)
    if (isNaN(amount)) continue // skip invalid values safely
    const currency = expense.currency || 'UNKNOWN'
    map[currency] = (map[currency] ?? 0) + amount
  }

  return Object.keys(map)
    .sort() // alphabetical for stable, consistent display
    .map((currency) => ({ currency, total: map[currency] }))
}

/**
 * Return the most recent expenses, sorted by created_at descending.
 * At most `limit` entries are returned (defaults to RECENT_EXPENSE_LIMIT).
 */
export function getRecentExpenses(expenses: Expense[], limit = RECENT_EXPENSE_LIMIT): Expense[] {
  return [...expenses]
    .sort((a, b) => {
      // Sort descending: newer created_at first
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })
    .slice(0, limit)
}
