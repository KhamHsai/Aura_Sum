// Types that match the actual backend schemas exactly.
// Fields match ReceiptFileResponse from backend/app/schemas/receipt.py
// and ExpenseResponse from backend/app/schemas/expense.py

export interface Receipt {
  id: number
  user_id: number
  expense_id: number | null     // null when not yet linked to an expense
  original_filename: string
  stored_filename: string
  mime_type: string
  file_size: number             // bytes
  upload_status: string         // "uploaded"
  uploaded_at: string           // ISO datetime string
}

// POST /api/receipts/upload returns a Receipt (ReceiptFileResponse)
export type ReceiptUploadResponse = Receipt

// POST /api/receipts/{id}/extract returns ExpenseResponse
// We only need the expense id to redirect — import full Expense from expense.ts if needed
export interface ReceiptExtractionResponse {
  id: number
  [key: string]: unknown        // ExpenseResponse has many more fields; we only need id here
}
