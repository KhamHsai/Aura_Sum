import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { loginUser, registerUser, getCurrentUser } from '../api/authApi'
import { TOKEN_KEY } from '../api/axios'
import type { User, LoginRequest, RegisterRequest } from '../types/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  // Becomes true once initializeAuth() has finished (success or failure).
  // The router guard waits for this before making auth decisions.
  const authReady = ref(false)

  const isAuthenticated = computed(() => token.value !== null && user.value !== null)

  // Read the token from localStorage and fetch the current user.
  // Called once at app startup. Clears auth data if the token is invalid.
  async function initializeAuth(): Promise<void> {
    const saved = localStorage.getItem(TOKEN_KEY)
    if (!saved) {
      authReady.value = true
      return
    }

    token.value = saved
    try {
      user.value = await getCurrentUser()
    } catch {
      // Token is expired or invalid — clear everything.
      clearAuth()
    } finally {
      authReady.value = true
    }
  }

  // Register a new user, then redirect to login.
  async function register(data: RegisterRequest): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      await registerUser(data)
      const router = useRouter()
      router.push('/login')
    } catch (err: unknown) {
      error.value = extractErrorMessage(err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Log in, save the token, and load the current user.
  async function login(data: LoginRequest): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      const response = await loginUser(data)
      token.value = response.access_token
      localStorage.setItem(TOKEN_KEY, response.access_token)
      user.value = await getCurrentUser()
    } catch (err: unknown) {
      clearAuth()
      error.value = extractErrorMessage(err)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  // Refresh the user object from the backend (useful after profile updates).
  async function loadCurrentUser(): Promise<void> {
    try {
      user.value = await getCurrentUser()
    } catch {
      clearAuth()
    }
  }

  // Log out: wipe state, remove token, go to login.
  function logout(): void {
    clearAuth()
    const router = useRouter()
    router.push('/login')
  }

  // ── helpers ──────────────────────────────────────────────────────────────

  function clearAuth(): void {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  function extractErrorMessage(err: unknown): string {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosErr = err as { response?: { data?: { detail?: string | { msg: string }[] } } }
      const detail = axiosErr.response?.data?.detail
      if (typeof detail === 'string') return detail
      if (Array.isArray(detail) && detail.length > 0) {
        return detail.map((d) => d.msg).join(', ')
      }
    }
    return 'An unexpected error occurred. Please try again.'
  }

  return {
    token,
    user,
    isLoading,
    error,
    isAuthenticated,
    authReady,
    initializeAuth,
    register,
    login,
    loadCurrentUser,
    logout,
  }
})
