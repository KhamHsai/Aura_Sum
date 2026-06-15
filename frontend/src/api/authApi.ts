import apiClient from './axios'
import type { LoginRequest, RegisterRequest, LoginResponse, User } from '../types/auth'

// POST /api/auth/register — returns the created User
export async function registerUser(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>('/auth/register', data)
  return response.data
}

// POST /api/auth/login — returns tokens
export async function loginUser(data: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', data)
  return response.data
}

// GET /api/auth/me — returns the current authenticated user
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>('/auth/me')
  return response.data
}
