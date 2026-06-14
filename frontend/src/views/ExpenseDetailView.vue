<template>
  <AppLayout>
    <!-- Back link always visible -->
    <RouterLink :to="{ name: 'expenses' }" class="back-link">
      ← {{ t('back_to_expenses') }}
    </RouterLink>

    <!-- Loading -->
    <div v-if="isLoading" class="state-container">
      <p>{{ t('loading') }}</p>
    </div>

    <!-- Not found -->
    <div v-else-if="notFound" class="state-container">
      <div class="alert alert-error" style="display:inline-block; max-width:420px;">
        {{ t('expense_not_found') }}
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-container">
      <div class="alert alert-error" style="display:inline-block; max-width:420px;">
        {{ error }}
      </div>
    </div>

    <!-- Detail -->
    <template v-else-if="expense">
      <!-- Header card -->
      <div class="detail-card">
        <div style="display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:1rem; margin-bottom:1rem;">
          <div>
            <h1 style="font-size:1.5rem; color:#1a1a2e; margin-bottom:0.25rem;">{{ expense.title }}</h1>
            <div style="color:#555; font-size:0.95rem;">
              {{ expense.merchant_name ?? t('not_available') }}
            </div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:1.5rem; font-weight:700; color:#4a6cf7;">
              {{ formatMoney(expense.total_amount, expense.currency) }}
            </div>
            <span
              class="badge"
              :class="expense.is_confirmed ? 'badge-confirmed' : 'badge-draft'"
            >
              {{ expense.is_confirmed ? t('confirmed') : t('draft') }}
            </span>
            <div class="detail-actions">
              <RouterLink
                :to="{ name: 'expense-edit', params: { id: expense.id } }"
                class="btn btn-secondary"
                style="text-decoration:none;"
              >
                {{ t('edit_expense') }}
              </RouterLink>
              <button
                class="btn btn-danger"
                :disabled="isDeleting"
                @click="handleDelete"
              >
                {{ isDeleting ? t('saving') : t('delete_expense') }}
              </button>
            </div>
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-field">
            <label>{{ t('receipt_date') }}</label>
            <span>{{ formatDate(expense.receipt_date) }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('receipt_number') }}</label>
            <span>{{ expense.receipt_number ?? t('not_available') }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('category') }}</label>
            <span>
              {{
                expense.category_id !== null
                  ? `${t('category')} #${expense.category_id}`
                  : t('uncategorized')
              }}
            </span>
          </div>
          <div class="detail-field">
            <label>{{ t('payment_method') }}</label>
            <span>{{ expense.payment_method ?? t('not_available') }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('currency') }}</label>
            <span>{{ expense.currency }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('subtotal') }}</label>
            <span>{{ formatMoney(expense.subtotal, expense.currency) }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('tax') }}</label>
            <span>{{ formatMoney(expense.tax_amount, expense.currency) }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('discount') }}</label>
            <span>{{ formatMoney(expense.discount_amount, expense.currency) }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('notes') }}</label>
            <span>{{ expense.notes ?? t('not_available') }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('created_at') }}</label>
            <span>{{ formatDateTime(expense.created_at) }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('updated_at') }}</label>
            <span>{{ formatDateTime(expense.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Items card -->
      <div class="detail-card">
        <h2>{{ t('expense_items') }}</h2>

        <div v-if="activeItems.length === 0" class="state-container" style="padding:1.5rem 0;">
          <p>{{ t('no_items') }}</p>
        </div>

        <div v-else class="items-table-wrapper">
          <table class="items-table">
            <thead>
              <tr>
                <th>{{ t('original_name') }}</th>
                <th>{{ t('name_en') }}</th>
                <th>{{ t('name_th') }}</th>
                <th>{{ t('quantity') }}</th>
                <th>{{ t('unit') }}</th>
                <th>{{ t('unit_price') }}</th>
                <th>{{ t('discount') }}</th>
                <th>{{ t('total_price') }}</th>
                <th>{{ t('category') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in activeItems" :key="item.id">
                <td>{{ itemDisplayName(item) }}</td>
                <td>{{ item.name_en ?? t('not_available') }}</td>
                <td>{{ item.name_th ?? t('not_available') }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ item.unit ?? t('not_available') }}</td>
                <td>{{ formatMoney(item.unit_price, expense.currency) }}</td>
                <td>{{ formatMoney(item.discount_amount, expense.currency) }}</td>
                <td>{{ formatMoney(item.total_price, expense.currency) }}</td>
                <td>
                  {{
                    item.category_id !== null
                      ? `${t('category')} #${item.category_id}`
                      : t('uncategorized')
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import { getExpenseById, deleteExpense } from '../api/expenseApi'
import { showDeleteConfirmation, showSuccessAlert, showErrorAlert } from '../utils/alerts'
import { formatMoney, formatDate, formatDateTime } from '../utils/formatters'
import type { Expense, ExpenseItem } from '../types/expense'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const expense = ref<Expense | null>(null)
const isLoading = ref(false)
const isDeleting = ref(false)
const error = ref<string | null>(null)
const notFound = ref(false)

const activeItems = computed<ExpenseItem[]>(() => expense.value?.items ?? [])

function itemDisplayName(item: ExpenseItem): string {
  return item.name_en ?? item.name_th ?? item.original_name ?? t('unnamed_item')
}

async function loadExpense(): Promise<void> {
  const rawId = route.params.id
  const id = parseInt(String(rawId), 10)
  if (isNaN(id) || id <= 0) {
    notFound.value = true
    return
  }

  isLoading.value = true
  error.value = null
  notFound.value = false

  try {
    expense.value = await getExpenseById(id)
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      notFound.value = true
    } else {
      error.value = t('unable_to_connect')
    }
  } finally {
    isLoading.value = false
  }
}

async function handleDelete(): Promise<void> {
  if (!expense.value || isDeleting.value) return

  const result = await showDeleteConfirmation({
    title: t('delete_expense_title'),
    text: t('delete_expense_message'),
    confirmButtonText: t('confirm_delete'),
    cancelButtonText: t('cancel'),
  })

  if (!result.isConfirmed) return

  isDeleting.value = true

  try {
    await deleteExpense(expense.value.id)
    await showSuccessAlert(t('expense_deleted'), t('expense_deleted_message'))
    router.push({ name: 'expenses' })
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      await showErrorAlert(t('expense_not_found'))
    } else {
      await showErrorAlert(t('unable_to_delete_expense'), t('something_went_wrong'))
    }
  } finally {
    isDeleting.value = false
  }
}

onMounted(loadExpense)
</script>
