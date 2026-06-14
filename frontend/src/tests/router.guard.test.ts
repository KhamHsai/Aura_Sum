/**
 * Router guard tests.
 * Verifies redirect behaviour without a real browser or backend.
 */
import { it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { defineComponent } from 'vue'
import { useAuthStore } from '../stores/auth'

// Lightweight stub components — we only care about routing, not rendering.
const StubView = defineComponent({ template: '<div />' })

// Re-create a minimal router that mirrors the real guard logic.
function buildTestRouter() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'login', component: StubView },
      { path: '/register', name: 'register', component: StubView },
      { path: '/dashboard', name: 'dashboard', component: StubView, meta: { requiresAuth: true } },
    ],
  })

  router.beforeEach((to) => {
    const auth = useAuthStore()
    if (to.meta.requiresAuth && !auth.isAuthenticated) return { name: 'login' }
    if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) return { name: 'dashboard' }
    return true
  })

  return router
}

// Stub getCurrentUser so initializeAuth does not hit the network.
vi.mock('../api/authApi', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getCurrentUser: vi.fn(),
}))

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRouter: () => ({ push: vi.fn() }),
  }
})

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

// 5. Protected route redirects to login when not authenticated.
it('protected route redirects to /login when not authenticated', async () => {
  const router = buildTestRouter()
  await router.push('/dashboard')
  expect(router.currentRoute.value.name).toBe('login')
})

// 6. Authenticated user can reach dashboard.
it('authenticated user reaches /dashboard', async () => {
  const auth = useAuthStore()
  // Manually put the store into an authenticated state.
  auth.token = 'some-token'
  auth.user = {
    id: 1, username: 'u', email: 'u@test.com', full_name: null,
    preferred_language: 'en', role: 'user', is_active: true,
    created_at: '', updated_at: '',
  }

  const router = buildTestRouter()
  await router.push('/dashboard')
  expect(router.currentRoute.value.name).toBe('dashboard')
})

// 7. Authenticated user is redirected away from /login.
it('authenticated user is redirected from /login to /dashboard', async () => {
  const auth = useAuthStore()
  auth.token = 'some-token'
  auth.user = {
    id: 1, username: 'u', email: 'u@test.com', full_name: null,
    preferred_language: 'en', role: 'user', is_active: true,
    created_at: '', updated_at: '',
  }

  const router = buildTestRouter()
  await router.push('/login')
  expect(router.currentRoute.value.name).toBe('dashboard')
})

// Authenticated user is redirected away from /register.
it('authenticated user is redirected from /register to /dashboard', async () => {
  const auth = useAuthStore()
  auth.token = 'some-token'
  auth.user = {
    id: 1, username: 'u', email: 'u@test.com', full_name: null,
    preferred_language: 'en', role: 'user', is_active: true,
    created_at: '', updated_at: '',
  }

  const router = buildTestRouter()
  await router.push('/register')
  expect(router.currentRoute.value.name).toBe('dashboard')
})
