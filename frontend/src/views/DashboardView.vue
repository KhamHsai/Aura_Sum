<template>
  <AppLayout>
    <!-- Welcome header -->
    <div class="page-header">
      <h1>{{ t('welcome') }}, {{ auth.user?.username }}!</h1>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="state-container">
      <p>{{ t('loading_dashboard') }}</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-container">
      <div class="alert alert-error" style="display:inline-block; text-align:left; max-width:420px;">
        {{ t('unable_to_load_dashboard') }}
      </div>
      <br />
      <button class="btn btn-secondary" style="margin-top:1rem;" @click="loadDashboard">
        {{ t('retry') }}
      </button>
    </div>

    <!-- Dashboard content -->
    <template v-else>

      <!-- Empty state -->
      <div v-if="expenses.length === 0 && receipts.length === 0" class="state-container">
        <p style="font-size:1.1rem; font-weight:600;">{{ t('welcome_to_smart_receipt') }}</p>
        <p class="state-subtitle">{{ t('get_started_message') }}</p>
      </div>

      <!-- Summary cards -->
      <template v-else>
        <h2 class="section-title">{{ t('dashboard_summary') }}</h2>
        <div class="summary-grid">
          <div class="summary-card">
            <div class="summary-card-value">{{ expenses.length }}</div>
            <div class="summary-card-label">{{ t('total_expenses') }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-card-value summary-value-confirmed">{{ confirmedCount }}</div>
            <div class="summary-card-label">{{ t('confirmed_expenses') }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-card-value summary-value-draft">{{ draftCount }}</div>
            <div class="summary-card-label">{{ t('draft_expenses') }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-card-value">{{ receipts.length }}</div>
            <div class="summary-card-label">{{ t('total_receipts') }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-card-value summary-value-linked">{{ linkedReceiptsCount }}</div>
            <div class="summary-card-label">{{ t('linked_receipts') }}</div>
          </div>
          <div class="summary-card">
            <div class="summary-card-value summary-value-unlinked">{{ unlinkedReceiptsCount }}</div>
            <div class="summary-card-label">{{ t('unlinked_receipts') }}</div>
          </div>
        </div>
      </template>

      <!-- Spending by currency -->
      <div class="dashboard-section">
        <h2 class="section-title">{{ t('spending_by_currency') }}</h2>
        <div v-if="currencyTotals.length === 0" class="state-subtitle" style="padding:0.5rem 0;">
          {{ t('no_spending_data') }}
        </div>
        <div v-else class="currency-list">
          <div
            v-for="entry in currencyTotals"
            :key="entry.currency"
            class="currency-row"
          >
            <span class="currency-code">{{ entry.currency }}</span>
            <span class="currency-total">{{ formatMoney(entry.total.toFixed(2), entry.currency) }}</span>
          </div>
        </div>
      </div>

      <!-- Recent expenses -->
      <div class="dashboard-section">
        <h2 class="section-title">{{ t('recent_expenses') }}</h2>
        <div v-if="recentExpenses.length === 0" class="state-subtitle" style="padding:0.5rem 0;">
          {{ t('no_recent_expenses') }}
        </div>
        <div v-else class="recent-expense-list">
          <div
            v-for="expense in recentExpenses"
            :key="expense.id"
            class="recent-expense-row"
          >
            <div class="recent-expense-info">
              <div class="recent-expense-title">{{ expense.title }}</div>
              <div class="recent-expense-meta">
                <span>{{ expense.merchant_name ?? t('not_available') }}</span>
                <span>{{ formatDate(expense.receipt_date) }}</span>
                <span
                  class="badge"
                  :class="expense.is_confirmed ? 'badge-confirmed' : 'badge-draft'"
                >
                  {{ expense.is_confirmed ? t('confirmed') : t('draft') }}
                </span>
              </div>
            </div>
            <div class="recent-expense-right">
              <div class="recent-expense-amount">
                {{ formatMoney(expense.total_amount, expense.currency) }}
              </div>
              <RouterLink
                :to="{ name: 'expense-detail', params: { id: expense.id } }"
                class="recent-expense-link"
              >
                {{ t('view_details') }}
              </RouterLink>
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- Quick actions (always visible) -->
    <div class="dashboard-section">
      <h2 class="section-title">{{ t('quick_actions') }}</h2>
      <div class="quick-actions">
        <RouterLink :to="{ name: 'expense-create' }" class="btn btn-primary quick-action-btn">
          {{ t('add_expense') }}
        </RouterLink>
        <RouterLink :to="{ name: 'receipt-upload' }" class="btn btn-secondary quick-action-btn">
          {{ t('upload_receipt') }}
        </RouterLink>
        <RouterLink :to="{ name: 'expenses' }" class="btn btn-secondary quick-action-btn">
          {{ t('view_expenses') }}
        </RouterLink>
        <RouterLink :to="{ name: 'receipts' }" class="btn btn-secondary quick-action-btn">
          {{ t('view_receipts') }}
        </RouterLink>
        <button
          class="btn btn-secondary quick-action-btn"
          :disabled="isExporting"
          @click="handleExport"
        >
          {{ isExporting ? t('exporting') : t('export_excel') }}
        </button>
      </div>
    </div>

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import { useAuthStore } from '../stores/auth'
import { getExpenses, exportExpenses } from '../api/expenseApi'
import { getReceipts } from '../api/receiptApi'
import { formatMoney, formatDate } from '../utils/formatters'
import {
  getFilenameFromContentDisposition,
  downloadBlob,
  isValidExcelBlob,
  parseBlobErrorMessage,
  FALLBACK_FILENAME,
} from '../utils/download'
import { showSuccessAlert, showErrorAlert } from '../utils/alerts'
import {
  countConfirmedExpenses,
  countDraftExpenses,
  countLinkedReceipts,
  countUnlinkedReceipts,
  groupTotalsByCurrency,
  getRecentExpenses,
} from '../utils/dashboard'
import type { Expense } from '../types/expense'
import type { Receipt } from '../types/receipt'

const { t } = useI18n()
const auth = useAuthStore()

// ── State ─────────────────────────────────────────────────────────────────────
const expenses = ref<Expense[]>([])
const receipts = ref<Receipt[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)
const isExporting = ref(false)

// ── Computed summaries ────────────────────────────────────────────────────────
const confirmedCount = computed(() => countConfirmedExpenses(expenses.value))
const draftCount = computed(() => countDraftExpenses(expenses.value))
const linkedReceiptsCount = computed(() => countLinkedReceipts(receipts.value))
const unlinkedReceiptsCount = computed(() => countUnlinkedReceipts(receipts.value))
const currencyTotals = computed(() => groupTotalsByCurrency(expenses.value))
const recentExpenses = computed(() => getRecentExpenses(expenses.value))

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadDashboard(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    const [expenseData, receiptData] = await Promise.all([getExpenses(), getReceipts()])
    expenses.value = expenseData
    receipts.value = receiptData
  } catch {
    error.value = t('unable_to_load_dashboard')
  } finally {
    isLoading.value = false
  }
}

// ── Export ────────────────────────────────────────────────────────────────────
async function handleExport(): Promise<void> {
  if (isExporting.value) return

  isExporting.value = true
  try {
    const result = await exportExpenses()

    if (!isValidExcelBlob(result.blob, result.contentType)) {
      await showErrorAlert(t('unable_to_export_expenses'), t('invalid_export_file'))
      return
    }

    const filename =
      getFilenameFromContentDisposition(result.contentDisposition) ?? FALLBACK_FILENAME

    downloadBlob(result.blob, filename)
    await showSuccessAlert(t('export_completed'), t('export_completed_message'))
  } catch (err: unknown) {
    let userMessage = t('export_failed_message')
    const axiosError = err as { response?: { data?: unknown } }
    if (axiosError?.response?.data instanceof Blob) {
      const parsed = await parseBlobErrorMessage(axiosError.response.data)
      if (parsed) userMessage = parsed
    }
    await showErrorAlert(t('unable_to_export_expenses'), userMessage)
  } finally {
    isExporting.value = false
  }
}

onMounted(loadDashboard)
</script>
