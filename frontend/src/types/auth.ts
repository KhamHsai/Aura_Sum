// Types that match the actual backend schemas exactly.

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  preferred_language: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  full_name?: string
  preferred_language?: 'en' | 'th'
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}
