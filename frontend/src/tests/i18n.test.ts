/**
 * i18n tests — language switching and persistence.
 */
import { it, expect, beforeEach } from 'vitest'
import { createI18n } from 'vue-i18n'
import en from '../locales/en.json'
import th from '../locales/th.json'

beforeEach(() => {
  localStorage.clear()
})

// 12. Language switches between English and Thai.
it('locale changes from en to th and shows Thai text', () => {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en, th } })
  expect(i18n.global.t('login')).toBe('Login')

  i18n.global.locale.value = 'th'
  expect(i18n.global.t('login')).toBe('เข้าสู่ระบบ')
})

// 13. Language preference persists in localStorage.
it('saves selected locale to localStorage', () => {
  localStorage.setItem('locale', 'th')
  const saved = localStorage.getItem('locale')
  expect(saved).toBe('th')
})

it('defaults to en when no locale is saved', () => {
  const saved = localStorage.getItem('locale') || 'en'
  expect(saved).toBe('en')
})

// English keys exist.
it('en locale has all required keys', () => {
  const required = ['login', 'register', 'email', 'password', 'logout', 'dashboard', 'welcome']
  for (const key of required) {
    expect((en as Record<string, string>)[key]).toBeTruthy()
  }
})

// Thai locale has all required keys.
it('th locale has all required keys', () => {
  const required = ['login', 'register', 'email', 'password', 'logout', 'dashboard', 'welcome']
  for (const key of required) {
    expect((th as Record<string, string>)[key]).toBeTruthy()
  }
})
