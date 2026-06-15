<template>
  <AppLayout>
    <div class="page-header">
      <h1>{{ t('expenses') }}</h1>
      <div class="page-header-actions">
        <RouterLink :to="{ name: 'expense-create' }" class="btn btn-primary" style="width:auto; text-decoration:none;">
          {{ t('add_expense') }}
        </RouterLink>
        <button
          class="btn btn-secondary"
          :disabled="isExporting"
          style="width:auto;"
          @click="handleExport"
        >
          {{ isExporting ? t('exporting') : t('export_excel') }}
        </button>
      </div>
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
            <div class="expense-card-title">{{ expense.paid_to ?? t('not_available') }}</div>
            <div class="expense-card-merchant">
              {{ formatDate(expense.receipt_date) }}
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
import { getExpenses, exportExpenses } from '../api/expenseApi'
import { formatMoney, formatDate } from '../utils/formatters'
import {
  getFilenameFromContentDisposition,
  downloadBlob,
  isValidExcelBlob,
  parseBlobErrorMessage,
  FALLBACK_FILENAME,
} from '../utils/download'
import { showSuccessAlert, showErrorAlert } from '../utils/alerts'
import type { Expense } from '../types/expense'

const { t } = useI18n()

const expenses = ref<Expense[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const isExporting = ref(false)

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

async function handleExport(): Promise<void> {
  // Prevent duplicate clicks while a download is in progress
  if (isExporting.value) return

  isExporting.value = true
  try {
    const result = await exportExpenses()

    // Validate the blob before triggering a download
    if (!isValidExcelBlob(result.blob, result.contentType)) {
      await showErrorAlert(t('unable_to_export_expenses'), t('invalid_export_file'))
      return
    }

    // Resolve filename from Content-Disposition header, fall back to a safe default
    const filename =
      getFilenameFromContentDisposition(result.contentDisposition) ?? FALLBACK_FILENAME

    downloadBlob(result.blob, filename)
    await showSuccessAlert(t('export_completed'), t('export_completed_message'))
  } catch (err: unknown) {
    // Backend JSON errors arrive as a Blob when responseType is 'blob'
    let userMessage = t('export_failed_message')

    const axiosError = err as { response?: { data?: unknown } }
    if (axiosError?.response?.data instanceof Blob) {
      const parsed = await parseBlobErrorMessage(axiosError.response.data)
      if (parsed) {
        userMessage = parsed
      }
    }

    await showErrorAlert(t('unable_to_export_expenses'), userMessage)
  } finally {
    isExporting.value = false
  }
}

onMounted(loadExpenses)
</script>
