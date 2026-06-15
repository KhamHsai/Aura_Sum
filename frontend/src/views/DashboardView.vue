<template>
  <AppLayout>
    <!-- Welcome header -->
    <div class="dashboard-summary-header">
      <div class="dashboard-summary-greeting">Hi, {{ auth.user?.username || 'Guest' }}!</div>
      <div class="dashboard-summary-subtitle">Here is your expense overview.</div>
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
        <p style="font-size:1.3rem; font-weight:700; color:var(--color-text-main);">{{ t('welcome_to_smart_receipt') }}</p>
        <p class="state-subtitle">{{ t('get_started_message') }}</p>
      </div>

      <template v-else>
      <div class="dashboard-top-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem;">
        <!-- Total Expense Gradient Card -->
        <div v-if="currencyTotals.length === 0" class="aura-gradient-card" style="margin-bottom: 0;">
          <div class="gradient-card-label">{{ t('total_expenses') }}</div>
          <div class="gradient-card-value">0.00 THB</div>
          <div class="gradient-card-trend down">
            <span>↓ 0%</span> compared to last month
          </div>
          <!-- Sparkline representation -->
          <div class="sparkline-container">
            <svg class="sparkline-svg" viewBox="0 0 100 30" preserveAspectRatio="none">
              <path d="M0,25 Q15,15 30,22 T60,10 T90,20 T100,5" fill="none" stroke="rgba(255,255,255,0.4)" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
        </div>
        <div
          v-for="entry in currencyTotals"
          :key="entry.currency"
          class="aura-gradient-card"
          style="margin-bottom: 0;"
        >
          <div class="gradient-card-label">{{ t('total_expenses') }}</div>
          <div class="gradient-card-value">{{ formatMoney(entry.total.toFixed(2), entry.currency) }}</div>
          <div class="gradient-card-trend down">
            <span>↓ 5%</span> compared to last month
          </div>
          <!-- Sparkline area chart SVG -->
          <div class="sparkline-container">
            <svg class="sparkline-svg" viewBox="0 0 100 30" preserveAspectRatio="none">
              <path d="M0,25 Q15,15 30,22 T60,12 T90,24 T100,8" fill="none" stroke="rgba(255,255,255,0.8)" stroke-width="2.5" stroke-linecap="round"/>
              <path d="M0,25 Q15,15 30,22 T60,12 T90,24 T100,8 L100,30 L0,30 Z" fill="url(#sparkline-grad)" opacity="0.15"/>
              <defs>
                <linearGradient id="sparkline-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#ffffff"/>
                  <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
        </div>
      </div>
      </template>

      <!-- Quick actions (always visible) -->
      <div class="dashboard-section">
        <h2 class="section-title">{{ t('quick_actions') }}</h2>
        <div class="quick-actions">
          <RouterLink :to="{ name: 'expense-create' }" class="quick-action-btn">
            ➕ {{ t('add_expense') }}
          </RouterLink>
          <RouterLink :to="{ name: 'receipt-upload' }" class="quick-action-btn">
            📤 {{ t('upload_receipt') }}
          </RouterLink>
          <RouterLink :to="{ name: 'expenses' }" class="quick-action-btn">
            🗒️ {{ t('view_expenses') }}
          </RouterLink>
          <RouterLink :to="{ name: 'receipts' }" class="quick-action-btn">
            📄 {{ t('view_receipts') }}
          </RouterLink>
          <button
            class="quick-action-btn"
            :disabled="isExporting"
            @click="handleExport"
          >
            📥 {{ isExporting ? t('exporting') : t('export_excel') }}
          </button>
        </div>
      </div>
      <!-- Recent expenses -->
      <div class="dashboard-section">
        <h2 class="section-title">
          <span>{{ t('recent_expenses') }}</span>
          <RouterLink :to="{ name: 'expenses' }" class="section-action-link" v-if="recentExpenses.length > 0">
            See All
          </RouterLink>
        </h2>
        <div v-if="recentExpenses.length === 0" class="state-subtitle" style="padding:0.5rem 0;">
          {{ t('no_recent_expenses') }}
        </div>
        <div v-else class="recent-expense-list">
          <div
            v-for="expense in recentExpenses"
            :key="expense.id"
            class="recent-expense-row detail-card"
          >
            <div class="recent-expense-info">
              <div class="recent-expense-icon">
                {{ getCategoryEmoji(expense.category_name) }}
              </div>
              <div class="recent-expense-details">
                <div class="recent-expense-title">{{ expense.paid_to ?? t('not_available') }}</div>
                <div class="recent-expense-meta">
                  <span>{{ formatDate(expense.receipt_date) }}</span>
                  <span
                    class="badge"
                    :class="expense.is_confirmed ? 'badge-confirmed' : 'badge-draft'"
                  >
                    {{ expense.is_confirmed ? t('confirmed') : t('draft') }}
                  </span>
                </div>
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

    <!-- Floating Action Button (FAB) -->
    <div class="fab-container">
      <RouterLink :to="{ name: 'expense-create' }" class="fab-btn" title="Add Expense">
        +
      </RouterLink>
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

const currencyTotals = computed(() => groupTotalsByCurrency(expenses.value))
const recentExpenses = computed(() => getRecentExpenses(expenses.value))



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
