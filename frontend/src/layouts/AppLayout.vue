<template>
  <div>
    <!-- Top navigation bar -->
    <nav class="navbar">
      <div class="navbar-left">
        <RouterLink class="navbar-brand" to="/dashboard">{{ t('app_name') }}</RouterLink>
        <RouterLink class="nav-link" to="/dashboard" active-class="nav-link-active">
          {{ t('dashboard') }}
        </RouterLink>
        <RouterLink class="nav-link" to="/expenses" active-class="nav-link-active">
          {{ t('expenses') }}
        </RouterLink>
        <RouterLink class="nav-link" to="/receipts" active-class="nav-link-active">
          {{ t('receipts') }}
        </RouterLink>
      </div>

      <div class="navbar-right">
        <!-- Current user email -->
        <span v-if="auth.user" class="navbar-user">{{ auth.user.email }}</span>

        <!-- Language switcher -->
        <select class="lang-select" :value="locale" @change="changeLanguage" :aria-label="t('language')">
          <option value="en">EN</option>
          <option value="th">TH</option>
        </select>

        <!-- Logout button -->
        <button class="btn btn-secondary" @click="auth.logout()">
          {{ t('logout') }}
        </button>
      </div>
    </nav>

    <!-- Page content -->
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()

function changeLanguage(event: Event): void {
  const select = event.target as HTMLSelectElement
  locale.value = select.value
  localStorage.setItem('locale', select.value)
}
</script>
