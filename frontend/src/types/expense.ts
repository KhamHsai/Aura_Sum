// Types that match the actual backend schemas exactly.
// Fields match ExpenseResponse and ExpenseItemResponse from backend/app/schemas/

export interface ExpenseItem {
  id: number
  expense_id: number
  category_id: number | null
  original_name: string
  name_en: string | null
  name_th: string | null
  quantity: string        // Decimal serialized as string by FastAPI
  unit: string | null
  unit_price: string | null
  discount_amount: string
  total_price: string
  created_at: string
  updated_at: string
}

export interface Expense {
  id: number
  user_id: number
  category_id: number | null
  category_name: string | null   // resolved or AI-guessed; present on AI extraction
  paid_to: string | null
  tax_id: string | null
  receipt_number: string | null
  receipt_date: string    // date string: "YYYY-MM-DD"
  receipt_time: string | null
  payment_method: string | null
  currency: string
  subtotal: string | null
  tax_amount: string | null
  discount_amount: string | null
  total_amount: string
  notes: string | null
  is_confirmed: boolean
  created_at: string
  updated_at: string
  items: ExpenseItem[]
}

// ── Write / form request shapes ───────────────────────────────────────────────
// These match ExpenseItemCreate and ExpenseCreate / ExpenseUpdate on the backend.
// Decimal fields are kept as strings to avoid JS floating-point issues.

export interface ExpenseItemFormData {
  category_id: number | null
  original_name: string
  name_en: string
  name_th: string
  display_name: string   // virtual: shows name_en or name_th based on current locale
  quantity: string
  unit: string
  unit_price: string
  discount_amount: string
  total_price: string
}

export interface ExpenseFormData {
  category_id: number | null
  category_name: string    // manual text entry — resolved to category_id on submit
  paid_to: string
  tax_id: string
  receipt_number: string
  receipt_date: string        // "YYYY-MM-DD"
  payment_method: string
  currency: string
  subtotal: string
  tax_amount: string
  discount_amount: string
  total_amount: string
  notes: string
  items: ExpenseItemFormData[]
}

// What is actually sent to POST /api/expenses
export interface ExpenseCreateRequest {
  category_id?: number | null
  paid_to?: string | null
  tax_id?: string | null
  receipt_number?: string | null
  receipt_date: string
  payment_method?: string | null
  currency: string
  subtotal?: string | null
  tax_amount?: string | null
  discount_amount?: string | null
  total_amount: string
  notes?: string | null
  items: ExpenseItemCreateRequest[]
}

// What is actually sent to PUT /api/expenses/{id}
export interface ExpenseUpdateRequest {
  category_id?: number | null
  paid_to?: string | null
  tax_id?: string | null
  receipt_number?: string | null
  receipt_date?: string
  payment_method?: string | null
  currency?: string
  subtotal?: string | null
  tax_amount?: string | null
  discount_amount?: string | null
  total_amount?: string
  notes?: string | null
  items?: ExpenseItemCreateRequest[]
}

// Matches ExpenseItemCreate on the backend
export interface ExpenseItemCreateRequest {
  original_name: string
  name_en: string | null
  name_th: string | null
  quantity: string
  unit: string | null
  unit_price: string | null
  discount_amount: string
  total_price: string
  category_id: number | null
}
