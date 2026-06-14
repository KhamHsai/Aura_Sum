<template>
  <AppLayout>
    <div class="dashboard-card">
      <h2>{{ t('welcome') }}, {{ auth.user?.username }}!</h2>
      <p>{{ auth.user?.email }}</p>
      <p>{{ t('backend_ok') }}</p>
    </div>

    <div class="dashboard-card">
      <h2>{{ t('dashboard') }}</h2>
      <p>{{ t('future_features') }}</p>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../layouts/AppLayout.vue'

const { t } = useI18n()
const auth = useAuthStore()
</script>
