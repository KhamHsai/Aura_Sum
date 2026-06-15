/**
 * LoginView component tests.
 * Tests form submission, error display, and validation.
 */
import { it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import { defineComponent } from 'vue'
import LoginView from '../views/LoginView.vue'
import { useAuthStore } from '../stores/auth'
import en from '../locales/en.json'

vi.mock('../api/authApi', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getCurrentUser: vi.fn(),
}))

const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/dashboard', component: defineComponent({ template: '<div />' }) },
      { path: '/register', component: defineComponent({ template: '<div />' }) },
    ],
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

async function mountLogin() {
  const router = buildRouter()
  await router.push('/login')
  return mount(LoginView, {
    global: { plugins: [router, i18n] },
  })
}

// 8. Login submits valid data.
it('login form submits email and password to the store', async () => {
  const auth = useAuthStore()
  const spy = vi.spyOn(auth, 'login').mockResolvedValue(undefined)

  const wrapper = await mountLogin()
  await wrapper.find('#email').setValue('user@test.com')
  await wrapper.find('#password').setValue('password123')
  await wrapper.find('form').trigger('submit')

  expect(spy).toHaveBeenCalledWith({ email: 'user@test.com', password: 'password123' })
})

// 9. Login shows backend error.
it('login shows error message when auth.error is set', async () => {
  const auth = useAuthStore()
  vi.spyOn(auth, 'login').mockImplementation(async () => {
    auth.error = 'Invalid email or password'
    throw new Error('auth failed')
  })

  const wrapper = await mountLogin()
  await wrapper.find('#email').setValue('bad@test.com')
  await wrapper.find('#password').setValue('wrongpass')
  await wrapper.find('form').trigger('submit')
  await wrapper.vm.$nextTick()

  expect(wrapper.text()).toContain('Invalid email or password')
})

// Required field validation.
it('shows required error when email is empty', async () => {
  const wrapper = await mountLogin()
  await wrapper.find('#password').setValue('password123')
  await wrapper.find('form').trigger('submit')
  await wrapper.vm.$nextTick()

  expect(wrapper.text()).toContain(en.error_required)
})
