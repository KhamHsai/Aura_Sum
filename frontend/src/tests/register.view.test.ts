/**
 * RegisterView component tests.
 */
import { it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import { defineComponent } from 'vue'
import RegisterView from '../views/RegisterView.vue'
import * as authApi from '../api/authApi'
import en from '../locales/en.json'

vi.mock('../api/authApi', () => ({
  loginUser: vi.fn(),
  registerUser: vi.fn(),
  getCurrentUser: vi.fn(),
}))

const mockRegister = vi.mocked(authApi.registerUser)

const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })

function buildRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/register', component: RegisterView },
      { path: '/login', component: defineComponent({ template: '<div />' }) },
    ],
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

async function mountRegister() {
  const router = buildRouter()
  await router.push('/register')
  return mount(RegisterView, {
    global: { plugins: [router, i18n] },
  })
}

// 10. Registration validates matching passwords.
it('shows error when passwords do not match', async () => {
  const wrapper = await mountRegister()
  await wrapper.find('#username').setValue('myuser')
  await wrapper.find('#email').setValue('user@test.com')
  await wrapper.find('#password').setValue('password123')
  await wrapper.find('#confirm_password').setValue('different!')
  await wrapper.find('form').trigger('submit')
  await wrapper.vm.$nextTick()

  expect(wrapper.text()).toContain(en.error_password_match)
})

// 11. Registration calls API with correct data.
it('calls registerUser with form data when all fields are valid', async () => {
  const fakeUser = {
    id: 1, username: 'myuser', email: 'user@test.com', full_name: null,
    preferred_language: 'en', role: 'user', is_active: true,
    created_at: '', updated_at: '',
  }
  mockRegister.mockResolvedValue(fakeUser)

  const wrapper = await mountRegister()
  await wrapper.find('#username').setValue('myuser')
  await wrapper.find('#email').setValue('user@test.com')
  await wrapper.find('#password').setValue('password123')
  await wrapper.find('#confirm_password').setValue('password123')
  await wrapper.find('form').trigger('submit')

  expect(mockRegister).toHaveBeenCalledWith(
    expect.objectContaining({ username: 'myuser', email: 'user@test.com', password: 'password123' })
  )
})

// Password too short.
it('shows error when password is less than 8 characters', async () => {
  const wrapper = await mountRegister()
  await wrapper.find('#username').setValue('myuser')
  await wrapper.find('#email').setValue('user@test.com')
  await wrapper.find('#password').setValue('short')
  await wrapper.find('#confirm_password').setValue('short')
  await wrapper.find('form').trigger('submit')
  await wrapper.vm.$nextTick()

  expect(wrapper.text()).toContain(en.error_password_min)
})
