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
        class="expense-card recent-expense-row"
        style="cursor:pointer; position:relative; text-decoration:none; color:inherit; display:flex;"
      >
        <div class="recent-expense-info">
          <div class="recent-expense-icon">
            {{ getCategoryEmoji(expense.category_name) }}
          </div>
          <div class="recent-expense-details">
            <div class="recent-expense-title">{{ expense.paid_to ?? t('not_available') }}</div>
            <div class="recent-expense-meta">
              <span>{{ formatDate(expense.receipt_date) }}</span>
              <span>
                {{
                  expense.category_name
                    ? expense.category_name
                    : t('uncategorized')
                }}
              </span>
            </div>
          </div>
        </div>
        <div class="recent-expense-right" style="position:relative; display:flex; align-items:center; gap:0.5rem;">
          <div class="recent-expense-amount">
            {{ formatMoney(expense.total_amount, expense.currency) }}
          </div>
          
          <div class="row-actions">
            <button class="action-btn edit-btn" @click.prevent.stop="goToEdit(expense.id)" :title="t('edit_expense')">
              {{ t('edit') }}
            </button>
            <button class="action-btn delete-btn" @click.prevent.stop="handleDelete(expense.id)" :title="t('delete_expense')">
              {{ t('delete') }}
            </button>
          </div>
        </div>
      </RouterLink>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import { getExpenses, exportExpenses, deleteExpense } from '../api/expenseApi'
import { formatMoney, formatDate } from '../utils/formatters'
import {
  getFilenameFromContentDisposition,
  downloadBlob,
  isValidExcelBlob,
  parseBlobErrorMessage,
  FALLBACK_FILENAME,
} from '../utils/download'
import { showSuccessAlert, showErrorAlert, showDeleteConfirmation } from '../utils/alerts'
import type { Expense } from '../types/expense'

const { t } = useI18n()
const router = useRouter()

const expenses = ref<Expense[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const isExporting = ref(false)
const isDeleting = ref(false)

function goToEdit(id: number) {
  router.push({ name: 'expense-edit', params: { id } })
}

async function handleDelete(id: number): Promise<void> {
  const result = await showDeleteConfirmation({
    title: t('delete_expense_title'),
    text: t('delete_expense_message'),
    confirmButtonText: t('confirm_delete'),
    cancelButtonText: t('cancel'),
  })

  if (!result.isConfirmed) return

  isDeleting.value = true
  try {
    await deleteExpense(id)
    await showSuccessAlert(t('expense_deleted'), t('expense_deleted_message'))
    expenses.value = expenses.value.filter(e => e.id !== id)
  } catch (err: unknown) {
    await showErrorAlert(t('unable_to_delete_expense'), t('something_went_wrong'))
  } finally {
    isDeleting.value = false
  }
}

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

function getCategoryEmoji(categoryName: string | null): string {
  if (!categoryName) return '📦'
  const name = categoryName.toLowerCase()
  if (name.includes('food') || name.includes('dining') || name.includes('eat') || name.includes('restaurant') || name.includes('อาหาร')) return '🍔'
  if (name.includes('shopping') || name.includes('buy') || name.includes('store') || name.includes('ช้อปปิ้ง')) return '🛍️'
  if (name.includes('utility') || name.includes('electricity') || name.includes('water') || name.includes('bills') || name.includes('สาธารณูปโภค')) return '🔌'
  if (name.includes('transport') || name.includes('travel') || name.includes('taxi') || name.includes('car') || name.includes('เดินทาง')) return '🚗'
  if (name.includes('grocer') || name.includes('supermarket') || name.includes('ของชำ')) return '🛒'
  return '📝'
}

onMounted(loadExpenses)
</script>

<style scoped>
.expense-card.recent-expense-row {
  display: flex !important;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem !important;
  margin-bottom: 1rem !important;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease-in-out;
}

.expense-card.recent-expense-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(93, 63, 211, 0.08);
  border-color: rgba(93, 63, 211, 0.2);
}

.recent-expense-info {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.recent-expense-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  background-color: var(--color-bg-alt, #f8f9fe);
  border-radius: 50%;
  flex-shrink: 0;
}

.recent-expense-details {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.recent-expense-title {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-text-main);
}

.recent-expense-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.75rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.recent-expense-right {
  display: flex;
  align-items: center;
  gap: 1.5rem !important;
}

.recent-expense-amount {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-text-main);
  white-space: nowrap;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  background: var(--color-bg-alt, #f3f4f6);
  color: var(--color-text-main, #1f2937);
  white-space: nowrap;
}

.edit-btn {
  border-color: rgba(93, 63, 211, 0.15);
  color: #5d3fd3;
  background-color: rgba(93, 63, 211, 0.05);
}

.edit-btn:hover {
  background-color: #5d3fd3;
  color: white;
  border-color: #5d3fd3;
}

.delete-btn {
  border-color: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  background-color: rgba(239, 68, 68, 0.05);
}

.delete-btn:hover {
  background-color: #ef4444;
  color: white;
  border-color: #ef4444;
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}
</style>
