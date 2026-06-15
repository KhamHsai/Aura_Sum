import apiClient from './axios'
import type { Category } from '../types/category'

// GET /api/categories — returns all active categories (auth required)
export async function getCategories(): Promise<Category[]> {
  const response = await apiClient.get<Category[]>('/categories')
  return response.data
}

// POST /api/categories — creates a new category (or returns existing with same name)
export async function createCategory(name: string): Promise<Category> {
  const response = await apiClient.post<Category>('/categories', { name })
  return response.data
}
