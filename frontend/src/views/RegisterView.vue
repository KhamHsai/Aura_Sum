<template>
  <div class="auth-page">
    <!-- Language switcher at top right -->
    <div class="auth-lang-switcher">
      <button 
        type="button" 
        class="lang-switch-btn" 
        :class="{ active: locale === 'en' }" 
        @click="changeLang('en')"
      >
        English
      </button>
      <span style="color: rgba(98, 93, 136, 0.3); font-size: 0.85rem;">/</span>
      <button 
        type="button" 
        class="lang-switch-btn" 
        :class="{ active: locale === 'th' }" 
        @click="changeLang('th')"
      >
        ไทย
      </button>
    </div>

    <div class="auth-card" style="max-width: 460px;">
      <!-- Aura branding header -->
      <div class="auth-header-logo">
        <div class="app-logo-symbol">A</div>
        <h2>Smart Receipt</h2>
      </div>

      <!-- Success message -->
      <div v-if="successMessage" class="alert alert-success" role="status">
        {{ successMessage }}
      </div>

      <!-- Backend error -->
      <div v-if="auth.error" class="alert alert-error" role="alert">
        {{ auth.error }}
      </div>

      <form @submit.prevent="handleSubmit" novalidate>
        <!-- Username -->
        <div class="form-group">
          <label for="username">{{ t('username') }}</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            :placeholder="t('username_placeholder')"
            autocomplete="username"
            required
          />
          <p v-if="errors.username" class="field-error">{{ errors.username }}</p>
        </div>

        <!-- Email -->
        <div class="form-group">
          <label for="email">{{ t('email') }}</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            :placeholder="t('email_placeholder')"
            autocomplete="email"
            required
          />
          <p v-if="errors.email" class="field-error">{{ errors.email }}</p>
        </div>



        <!-- Password -->
        <div class="form-group">
          <label for="password">{{ t('password') }}</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            :placeholder="t('password_placeholder')"
            autocomplete="new-password"
            required
          />
          <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
        </div>

        <!-- Confirm password -->
        <div class="form-group">
          <label for="confirm_password">{{ t('confirm_password') }}</label>
          <input
            id="confirm_password"
            v-model="form.confirmPassword"
            type="password"
            autocomplete="new-password"
            required
          />
          <p v-if="errors.confirmPassword" class="field-error">{{ errors.confirmPassword }}</p>
        </div>

        <button type="submit" class="btn btn-primary" style="width:100%;" :disabled="auth.isLoading">
          {{ auth.isLoading ? t('loading') : t('register') }}
        </button>
      </form>

      <p class="auth-link">
        {{ t('have_account') }}
        <RouterLink to="/login">{{ t('login') }}</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import { registerUser } from '../api/authApi'

const { t, locale } = useI18n()
const auth = useAuthStore()
const router = useRouter()

function changeLang(lang: 'en' | 'th'): void {
  locale.value = lang
  localStorage.setItem('locale', lang)
}

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const errors = ref<{
  username?: string
  email?: string
  password?: string
  confirmPassword?: string
}>({})

const successMessage = ref<string | null>(null)

function validate(): boolean {
  errors.value = {}

  if (!form.username) {
    errors.value.username = t('error_required')
  } else if (form.username.trim().length < 3) {
    errors.value.username = t('error_username_min')
  }

  if (!form.email) {
    errors.value.email = t('error_required')
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.value.email = t('error_email')
  }

  if (!form.password) {
    errors.value.password = t('error_required')
  } else if (form.password.length < 8) {
    errors.value.password = t('error_password_min')
  }

  if (!form.confirmPassword) {
    errors.value.confirmPassword = t('error_required')
  } else if (form.password !== form.confirmPassword) {
    errors.value.confirmPassword = t('error_password_match')
  }

  return Object.keys(errors.value).length === 0
}

async function handleSubmit(): Promise<void> {
  successMessage.value = null
  auth.error = null

  if (!validate()) return

  auth.isLoading = true
  try {
    await registerUser({
      username: form.username.trim(),
      email: form.email.trim().toLowerCase(),
      password: form.password,
    })
    successMessage.value = t('register_success')
    setTimeout(() => router.push('/login'), 1500)
  } catch (err: unknown) {
    auth.error = extractErrorMessage(err)
  } finally {
    auth.isLoading = false
  }
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
  return t('error_required')
}
</script>
