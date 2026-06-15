// Matches CategoryResponse from backend/app/schemas/category.py

export interface Category {
  id: number
  code: string
  name_en: string
  name_th: string
  is_active: boolean
  created_at: string
  updated_at: string
}
