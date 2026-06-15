import apiClient from './axios'
import type { Receipt, ReceiptExtractionResponse } from '../types/receipt'

// GET /api/receipts — all non-deleted receipts for the authenticated user
export async function getReceipts(): Promise<Receipt[]> {
  const response = await apiClient.get<Receipt[]>('/receipts')
  return response.data
}

// GET /api/receipts/{id} — single receipt owned by the current user
export async function getReceiptById(receiptId: number): Promise<Receipt> {
  const response = await apiClient.get<Receipt>(`/receipts/${receiptId}`)
  return response.data
}

// POST /api/receipts/upload — multipart/form-data upload
// The backend expects a form field named "file".
// onUploadProgress is optional; pass it to get 0–100% progress updates.
export async function uploadReceipt(
  file: File,
  onUploadProgress?: (percent: number) => void,
): Promise<Receipt> {
  const formData = new FormData()
  formData.append('file', file)

  // Delete the instance-level 'application/json' default so axios can auto-set
  // 'multipart/form-data; boundary=...' correctly when it detects FormData.
  const response = await apiClient.post<Receipt>('/receipts/upload', formData, {
    headers: {
      'Content-Type': undefined,
    },
    onUploadProgress: onUploadProgress
      ? (progressEvent) => {
          if (progressEvent.total && progressEvent.total > 0) {
            const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onUploadProgress(percent)
          }
        }
      : undefined,
  })

  return response.data
}

// POST /api/receipts/{id}/extract — run Gemini extraction, create draft expense
// Returns a full ExpenseResponse; we primarily need expense.id for the redirect.
export async function extractReceipt(receiptId: number): Promise<ReceiptExtractionResponse> {
  const response = await apiClient.post<ReceiptExtractionResponse>(
    `/receipts/${receiptId}/extract`,
  )
  return response.data
}
