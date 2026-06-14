/**
 * Unit tests for src/utils/dashboard.ts
 * All functions are pure — no mocks needed.
 */
import { it, expect, describe } from 'vitest'
import {
  countConfirmedExpenses,
  countDraftExpenses,
  countLinkedReceipts,
  countUnlinkedReceipts,
  groupTotalsByCurrency,
  getRecentExpenses,
  RECENT_EXPENSE_LIMIT,
} from '../utils/dashboard'
import type { Expense } from '../types/expense'
import type { Receipt } from '../types/receipt'

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeExpense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: 1,
    user_id: 1,
    category_id: null,
    title: 'Test Expense',
    merchant_name: null,
    receipt_number: null,
    receipt_date: '2024-01-01',
    payment_method: null,
    currency: 'THB',
    subtotal: null,
    tax_amount: null,
    discount_amount: null,
    total_amount: '100.00',
    notes: null,
    is_confirmed: false,
    created_at: '2024-01-01T00:00:00',
    updated_at: '2024-01-01T00:00:00',
    items: [],
    ...overrides,
  }
}

function makeReceipt(overrides: Partial<Receipt> = {}): Receipt {
  return {
    id: 1,
    user_id: 1,
    expense_id: null,
    original_filename: 'receipt.jpg',
    stored_filename: 'stored.jpg',
    mime_type: 'image/jpeg',
    file_size: 1024,
    upload_status: 'uploaded',
    uploaded_at: '2024-01-01T00:00:00',
    ...overrides,
  }
}

// ── countConfirmedExpenses ────────────────────────────────────────────────────

describe('countConfirmedExpenses', () => {
  it('returns 0 for empty array', () => {
    expect(countConfirmedExpenses([])).toBe(0)
  })

  it('counts only confirmed expenses', () => {
    const expenses = [
      makeExpense({ id: 1, is_confirmed: true }),
      makeExpense({ id: 2, is_confirmed: false }),
      makeExpense({ id: 3, is_confirmed: true }),
    ]
    expect(countConfirmedExpenses(expenses)).toBe(2)
  })

  it('returns 0 when all are drafts', () => {
    const expenses = [
      makeExpense({ id: 1, is_confirmed: false }),
      makeExpense({ id: 2, is_confirmed: false }),
    ]
    expect(countConfirmedExpenses(expenses)).toBe(0)
  })
})

// ── countDraftExpenses ────────────────────────────────────────────────────────

describe('countDraftExpenses', () => {
  it('returns 0 for empty array', () => {
    expect(countDraftExpenses([])).toBe(0)
  })

  it('counts only draft (unconfirmed) expenses', () => {
    const expenses = [
      makeExpense({ id: 1, is_confirmed: false }),
      makeExpense({ id: 2, is_confirmed: true }),
      makeExpense({ id: 3, is_confirmed: false }),
    ]
    expect(countDraftExpenses(expenses)).toBe(2)
  })
})

// ── countLinkedReceipts ───────────────────────────────────────────────────────

describe('countLinkedReceipts', () => {
  it('returns 0 for empty array', () => {
    expect(countLinkedReceipts([])).toBe(0)
  })

  it('counts only receipts with a non-null expense_id', () => {
    const receipts = [
      makeReceipt({ id: 1, expense_id: 5 }),
      makeReceipt({ id: 2, expense_id: null }),
      makeReceipt({ id: 3, expense_id: 10 }),
    ]
    expect(countLinkedReceipts(receipts)).toBe(2)
  })
})

// ── countUnlinkedReceipts ─────────────────────────────────────────────────────

describe('countUnlinkedReceipts', () => {
  it('returns 0 for empty array', () => {
    expect(countUnlinkedReceipts([])).toBe(0)
  })

  it('counts only receipts with expense_id === null', () => {
    const receipts = [
      makeReceipt({ id: 1, expense_id: null }),
      makeReceipt({ id: 2, expense_id: 5 }),
      makeReceipt({ id: 3, expense_id: null }),
    ]
    expect(countUnlinkedReceipts(receipts)).toBe(2)
  })
})

// ── groupTotalsByCurrency ─────────────────────────────────────────────────────

describe('groupTotalsByCurrency', () => {
  it('returns empty array for no expenses', () => {
    expect(groupTotalsByCurrency([])).toEqual([])
  })

  it('groups totals by currency', () => {
    const expenses = [
      makeExpense({ id: 1, currency: 'THB', total_amount: '500.00' }),
      makeExpense({ id: 2, currency: 'THB', total_amount: '200.00' }),
      makeExpense({ id: 3, currency: 'USD', total_amount: '50.00' }),
    ]
    const result = groupTotalsByCurrency(expenses)
    expect(result).toHaveLength(2)
    const thb = result.find((r) => r.currency === 'THB')
    const usd = result.find((r) => r.currency === 'USD')
    expect(thb?.total).toBe(700)
    expect(usd?.total).toBe(50)
  })

  it('does not combine THB and USD into one total', () => {
    const expenses = [
      makeExpense({ id: 1, currency: 'THB', total_amount: '1000.00' }),
      makeExpense({ id: 2, currency: 'USD', total_amount: '100.00' }),
    ]
    const result = groupTotalsByCurrency(expenses)
    expect(result).toHaveLength(2)
    expect(result.every((r) => r.currency === 'THB' || r.currency === 'USD')).toBe(true)
  })

  it('skips expenses with invalid amount safely', () => {
    const expenses = [
      makeExpense({ id: 1, currency: 'THB', total_amount: 'not-a-number' }),
      makeExpense({ id: 2, currency: 'THB', total_amount: '300.00' }),
    ]
    const result = groupTotalsByCurrency(expenses)
    expect(result).toHaveLength(1)
    expect(result[0].total).toBe(300)
  })

  it('sorts currency codes alphabetically for stable display', () => {
    const expenses = [
      makeExpense({ id: 1, currency: 'USD', total_amount: '10.00' }),
      makeExpense({ id: 2, currency: 'EUR', total_amount: '20.00' }),
      makeExpense({ id: 3, currency: 'THB', total_amount: '30.00' }),
    ]
    const result = groupTotalsByCurrency(expenses)
    const codes = result.map((r) => r.currency)
    expect(codes).toEqual(['EUR', 'THB', 'USD'])
  })
})

// ── getRecentExpenses ─────────────────────────────────────────────────────────

describe('getRecentExpenses', () => {
  it('returns empty array for no expenses', () => {
    expect(getRecentExpenses([])).toEqual([])
  })

  it('sorts expenses by created_at descending', () => {
    const expenses = [
      makeExpense({ id: 1, created_at: '2024-01-01T00:00:00' }),
      makeExpense({ id: 2, created_at: '2024-03-15T00:00:00' }),
      makeExpense({ id: 3, created_at: '2024-02-10T00:00:00' }),
    ]
    const result = getRecentExpenses(expenses)
    expect(result[0].id).toBe(2) // March is most recent
    expect(result[1].id).toBe(3) // February
    expect(result[2].id).toBe(1) // January
  })

  it('returns at most RECENT_EXPENSE_LIMIT items by default', () => {
    const expenses = Array.from({ length: 10 }, (_, i) =>
      makeExpense({ id: i + 1, created_at: `2024-01-${String(i + 1).padStart(2, '0')}T00:00:00` }),
    )
    expect(getRecentExpenses(expenses)).toHaveLength(RECENT_EXPENSE_LIMIT)
  })

  it('respects a custom limit', () => {
    const expenses = Array.from({ length: 10 }, (_, i) =>
      makeExpense({ id: i + 1, created_at: `2024-01-${String(i + 1).padStart(2, '0')}T00:00:00` }),
    )
    expect(getRecentExpenses(expenses, 3)).toHaveLength(3)
  })

  it('does not mutate the original array', () => {
    const expenses = [
      makeExpense({ id: 1, created_at: '2024-01-01T00:00:00' }),
      makeExpense({ id: 2, created_at: '2024-03-15T00:00:00' }),
    ]
    const original = [...expenses]
    getRecentExpenses(expenses)
    expect(expenses[0].id).toBe(original[0].id)
  })
})
