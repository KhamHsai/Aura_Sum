import apiClient from './axios'
import type { Category } from '../types/category'

// GET /api/categories — returns all active categories (auth required)
export async function getCategories(): Promise<Category[]> {
  const response = await apiClient.get<Category[]>('/categories')
  return response.data
}
