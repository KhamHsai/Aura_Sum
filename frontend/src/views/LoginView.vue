<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>{{ t('login') }}</h1>

      <!-- Backend error -->
      <div v-if="auth.error" class="alert alert-error" role="alert">
        {{ auth.error }}
      </div>

      <form @submit.prevent="handleSubmit" novalidate>
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
            autocomplete="current-password"
            required
          />
          <p v-if="errors.password" class="field-error">{{ errors.password }}</p>
        </div>

        <button type="submit" class="btn btn-primary" :disabled="auth.isLoading">
          {{ auth.isLoading ? t('loading') : t('login') }}
        </button>
      </form>

      <p class="auth-link">
        {{ t('no_account') }}
        <RouterLink to="/register">{{ t('register') }}</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const form = reactive({ email: '', password: '' })
const errors = ref<{ email?: string; password?: string }>({})

function validate(): boolean {
  errors.value = {}
  if (!form.email) {
    errors.value.email = t('error_required')
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    errors.value.email = t('error_email')
  }
  if (!form.password) {
    errors.value.password = t('error_required')
  }
  return Object.keys(errors.value).length === 0
}

async function handleSubmit(): Promise<void> {
  if (!validate()) return
  auth.error = null
  try {
    await auth.login({ email: form.email, password: form.password })
    router.push('/dashboard')
  } catch {
    // error is already set on auth.error by the store
  }
}
</script>
