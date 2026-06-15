import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/RegisterView.vue'),
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/expenses',
    name: 'expenses',
    component: () => import('../views/ExpenseListView.vue'),
    meta: { requiresAuth: true },
  },
  {
    // /expenses/new must come BEFORE /expenses/:id so "new" is not treated as an ID
    path: '/expenses/new',
    name: 'expense-create',
    component: () => import('../views/ExpenseCreateView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/expenses/:id/edit',
    name: 'expense-edit',
    component: () => import('../views/ExpenseEditView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/expenses/:id',
    name: 'expense-detail',
    component: () => import('../views/ExpenseDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/receipts',
    name: 'receipts',
    component: () => import('../views/ReceiptListView.vue'),
    meta: { requiresAuth: true },
  },
  {
    // /receipts/upload must come BEFORE /receipts/:id so "upload" is not treated as an ID
    path: '/receipts/upload',
    name: 'receipt-upload',
    component: () => import('../views/ReceiptUploadView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/receipts/:id',
    name: 'receipt-detail',
    component: () => import('../views/ReceiptDetailView.vue'),
    meta: { requiresAuth: true },
  },
  {
    // Redirect the root path based on auth state.
    path: '/',
    redirect: () => {
      const auth = useAuthStore()
      return auth.isAuthenticated ? '/dashboard' : '/login'
    },
  },
  {
    // Catch-all: same logic.
    path: '/:pathMatch(.*)*',
    redirect: () => {
      const auth = useAuthStore()
      return auth.isAuthenticated ? '/dashboard' : '/login'
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Global navigation guard.
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // Wait for initializeAuth() to finish on first load before making any decision.
  // This prevents the guard from seeing isAuthenticated=false while the token
  // is still being validated against the backend.
  if (!auth.authReady) {
    await new Promise<void>((resolve) => {
      const stop = auth.$subscribe(() => {
        if (auth.authReady) {
          stop()
          resolve()
        }
      })
    })
  }

  // Protected route without valid auth → send to login.
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login' }
  }

  // Already authenticated user tries to open login or register → send to dashboard.
  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) {
    return { name: 'dashboard' }
  }

  // All other cases: allow.
  return true
})

export default router
