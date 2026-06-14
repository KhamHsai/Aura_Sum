<template>
  <AppLayout>
    <div class="page-header">
      <h1>{{ t('expenses') }}</h1>
      <RouterLink :to="{ name: 'expense-create' }" class="btn btn-primary" style="width:auto; text-decoration:none;">
        {{ t('add_expense') }}
      </RouterLink>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="state-container">
      <p>{{ t('loading_expenses') }}</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-container">
      <div class="alert alert-error" style="display:inline-block; text-align:left; max-width:420px;">
        {{ error }}
      </div>
      <br />
      <button class="btn btn-secondary" style="margin-top:1rem;" @click="loadExpenses">
        {{ t('retry') }}
      </button>
    </div>

    <!-- Empty -->
    <div v-else-if="expenses.length === 0" class="state-container">
      <p>{{ t('no_expenses_found') }}</p>
      <p class="state-subtitle">{{ t('no_expenses_subtitle') }}</p>
    </div>

    <!-- List -->
    <div v-else class="expense-list">
      <RouterLink
        v-for="expense in expenses"
        :key="expense.id"
        :to="{ name: 'expense-detail', params: { id: expense.id } }"
        class="expense-card"
      >
        <div class="expense-card-top">
          <div>
            <div class="expense-card-title">{{ expense.title }}</div>
            <div class="expense-card-merchant">
              {{ expense.merchant_name ?? t('not_available') }}
            </div>
          </div>
          <div class="expense-card-amount">
            {{ formatMoney(expense.total_amount, expense.currency) }}
          </div>
        </div>

        <div class="expense-card-meta">
          <!-- Date -->
          <span>{{ formatDate(expense.receipt_date) }}</span>

          <!-- Category -->
          <span>
            {{
              expense.category_id !== null
                ? `${t('category')} #${expense.category_id}`
                : t('uncategorized')
            }}
          </span>

          <!-- Status badge -->
          <span
            class="badge"
            :class="expense.is_confirmed ? 'badge-confirmed' : 'badge-draft'"
          >
            {{ expense.is_confirmed ? t('confirmed') : t('draft') }}
          </span>
        </div>
      </RouterLink>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import { getExpenses } from '../api/expenseApi'
import { formatMoney, formatDate } from '../utils/formatters'
import type { Expense } from '../types/expense'

const { t } = useI18n()

const expenses = ref<Expense[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)

async function loadExpenses(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    expenses.value = await getExpenses()
  } catch {
    error.value = t('unable_to_load_expenses')
  } finally {
    isLoading.value = false
  }
}

onMounted(loadExpenses)
</script>
