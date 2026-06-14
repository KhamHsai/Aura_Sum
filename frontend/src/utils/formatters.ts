/**
 * Small shared formatting helpers used by expense views.
 * All functions handle null/undefined safely and never return NaN.
 */

// Format a money value with two decimal places and the currency code.
// Input may be a decimal string from the backend (e.g. "1234.50") or null.
export function formatMoney(amount: string | null | undefined, currency: string): string {
  if (amount === null || amount === undefined) return 'N/A'
  const num = parseFloat(amount)
  if (isNaN(num)) return 'N/A'
  return `${num.toFixed(2)} ${currency}`
}

// Format an ISO date string "YYYY-MM-DD" to a more readable form.
export function formatDate(value: string | null | undefined): string {
  if (!value) return 'N/A'
  // Use en-CA locale for consistent YYYY-MM-DD parsing — avoid timezone shifts.
  const [year, month, day] = value.split('-')
  if (!year || !month || !day) return value
  return `${year}-${month}-${day}`
}

// Format an ISO datetime string to a readable local date-time.
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return 'N/A'
  const d = new Date(value)
  if (isNaN(d.getTime())) return value
  return d.toLocaleString()
}
