/**
 * Unit tests for the confirmExpense API function.
 * Verifies it calls the correct endpoint using the existing Axios client.
 */
import { it, expect, describe, vi, beforeEach } from 'vitest'

// vi.hoisted ensures mockPost is initialized before vi.mock is hoisted
const { mockPost } = vi.hoisted(() => {
  return { mockPost: vi.fn() }
})

vi.mock('../api/axios', () => ({
  default: { post: mockPost },
}))

import { confirmExpense } from '../api/expenseApi'

const fakeConfirmedExpense = {
  id: 7,
  user_id: 1,
  category_id: 2,
  title: 'Cafe Receipt',
  merchant_name: 'Blue Bottle',
  receipt_number: null,
  receipt_date: '2024-06-01',
  payment_method: 'Cash',
  currency: 'THB',
  subtotal: '90.91',
  tax_amount: '6.36',
  discount_amount: '0.00',
  total_amount: '100.00',
  notes: null,
  is_confirmed: true,
  created_at: '2024-06-01T09:00:00',
  updated_at: '2024-06-01T09:05:00',
  items: [],
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('confirmExpense', () => {
  // 1. Calls POST /expenses/{id}/confirm
  it('calls POST /expenses/{id}/confirm with correct path', async () => {
    mockPost.mockResolvedValue({ data: fakeConfirmedExpense })
    await confirmExpense(7)
    expect(mockPost).toHaveBeenCalledWith('/expenses/7/confirm')
  })

  // 2. Uses the existing Axios client (mockPost was called, not a raw fetch)
  it('uses the existing Axios client', async () => {
    mockPost.mockResolvedValue({ data: fakeConfirmedExpense })
    await confirmExpense(7)
    expect(mockPost).toHaveBeenCalledOnce()
  })

  // 3. Returns the confirmed expense from the response data
  it('returns the updated expense with is_confirmed true', async () => {
    mockPost.mockResolvedValue({ data: fakeConfirmedExpense })
    const result = await confirmExpense(7)
    expect(result.is_confirmed).toBe(true)
    expect(result.id).toBe(7)
  })

  // 4. No request body is sent (POST with only the URL)
  it('does not send a request body', async () => {
    mockPost.mockResolvedValue({ data: fakeConfirmedExpense })
    await confirmExpense(7)
    // post was called with only one argument (the URL)
    expect(mockPost.mock.calls[0].length).toBe(1)
  })

  // 5. Propagates errors from the API
  it('propagates API errors', async () => {
    mockPost.mockRejectedValue({ response: { status: 409 } })
    await expect(confirmExpense(7)).rejects.toMatchObject({ response: { status: 409 } })
  })

  // 6. Works with different expense IDs
  it('uses the provided expense ID in the URL', async () => {
    mockPost.mockResolvedValue({ data: { ...fakeConfirmedExpense, id: 42 } })
    await confirmExpense(42)
    expect(mockPost).toHaveBeenCalledWith('/expenses/42/confirm')
  })
})
