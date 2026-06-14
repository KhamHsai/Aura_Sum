<template>
  <AppLayout>
    <!-- Back link always visible -->
    <RouterLink :to="{ name: 'receipts' }" class="back-link">
      ← {{ t('back_to_receipts') }}
    </RouterLink>

    <!-- Loading -->
    <div v-if="isLoading" class="state-container">
      <p>{{ t('loading') }}</p>
    </div>

    <!-- Not found -->
    <div v-else-if="notFound" class="state-container">
      <div class="alert alert-error" style="display:inline-block; max-width:420px;">
        {{ t('receipt_not_found') }}
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-container">
      <div class="alert alert-error" style="display:inline-block; max-width:420px;">
        {{ error }}
      </div>
    </div>

    <!-- Detail -->
    <template v-else-if="receipt">
      <div class="detail-card">
        <!-- Header -->
        <div style="display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:1rem; margin-bottom:1.25rem;">
          <div>
            <h1 style="font-size:1.4rem; color:#1a1a2e; margin-bottom:0.25rem;">{{ t('receipt_details') }}</h1>
            <div style="color:#555; font-size:0.95rem; word-break:break-all;">{{ receipt.original_filename }}</div>
          </div>
          <div class="detail-actions">
            <!-- Extract button when not yet linked to an expense -->
            <button
              v-if="receipt.expense_id === null"
              class="btn btn-primary"
              style="width:auto;"
              :disabled="isExtracting"
              @click="handleExtract"
            >
              {{ isExtracting ? t('saving') : t('extract_receipt') }}
            </button>

            <!-- Open Expense button when already linked -->
            <RouterLink
              v-else
              :to="{ name: 'expense-detail', params: { id: receipt.expense_id } }"
              class="btn btn-secondary"
              style="text-decoration:none;"
            >
              {{ t('open_expense') }}
            </RouterLink>
          </div>
        </div>

        <!-- Extraction state indicator -->
        <div v-if="isExtracting" class="upload-status-inline">
          <p>{{ t('analyzing_receipt') }}</p>
          <p style="font-size:0.85rem; color:#888;">{{ t('analysis_may_take_a_moment') }}</p>
        </div>

        <!-- Metadata grid -->
        <div class="detail-grid">
          <div class="detail-field">
            <label>{{ t('file_name') }}</label>
            <span style="word-break:break-all;">{{ receipt.original_filename }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('file_type') }}</label>
            <span>{{ receipt.mime_type }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('file_size') }}</label>
            <span>{{ formatFileSize(receipt.file_size) }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('upload_date') }}</label>
            <span>{{ formatDateTime(receipt.uploaded_at) }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('extraction_status') }}</label>
            <span>
              <span class="badge" :class="statusBadgeClass(receipt.upload_status)">
                {{ t(statusLabel(receipt.upload_status)) }}
              </span>
            </span>
          </div>
          <div class="detail-field">
            <label>{{ t('linked_expense') }}</label>
            <span v-if="receipt.expense_id !== null">
              <RouterLink
                :to="{ name: 'expense-detail', params: { id: receipt.expense_id } }"
                style="color:#4a6cf7; text-decoration:none; font-weight:600;"
              >
                {{ t('open_expense') }} #{{ receipt.expense_id }}
              </RouterLink>
            </span>
            <span v-else>{{ t('not_extracted') }}</span>
          </div>
        </div>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import { getReceiptById, extractReceipt } from '../api/receiptApi'
import { showSuccessAlert, showErrorAlert } from '../utils/alerts'
import { formatDateTime } from '../utils/formatters'
import type { Receipt } from '../types/receipt'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const receipt = ref<Receipt | null>(null)
const isLoading = ref(false)
const isExtracting = ref(false)
const error = ref<string | null>(null)
const notFound = ref(false)

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    uploaded: 'status_uploaded',
    extracted: 'status_extracted',
    processing: 'status_processing',
    failed: 'status_failed',
  }
  return map[status] ?? 'status_uploaded'
}

function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    uploaded: 'badge-draft',
    extracted: 'badge-confirmed',
    processing: 'badge-ai',
    failed: 'badge-failed',
  }
  return map[status] ?? 'badge-draft'
}

function mapGeminiError(err: unknown): string {
  const response = (err as { response?: { data?: { detail?: unknown }; status?: number } })?.response
  const status = response?.status

  if (status === 503) return t('gemini_not_configured')
  if (status === 429) return t('gemini_quota_exceeded')
  if (status === 409) return t('receipt_already_extracted')

  const rawDetail = response?.data?.detail
  if (typeof rawDetail === 'string' && rawDetail.length <= 200) return rawDetail

  return t('something_went_wrong')
}

// ── Load receipt ──────────────────────────────────────────────────────────────

async function loadReceipt(): Promise<void> {
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
    receipt.value = await getReceiptById(id)
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

// ── Extract from detail page ──────────────────────────────────────────────────

async function handleExtract(): Promise<void> {
  if (!receipt.value || isExtracting.value) return

  isExtracting.value = true

  try {
    const expense = await extractReceipt(receipt.value.id)
    await showSuccessAlert(t('extraction_completed'), t('extraction_completed_message'))
    router.push({ name: 'expense-edit', params: { id: expense.id } })
  } catch (err: unknown) {
    const message = mapGeminiError(err)
    await showErrorAlert(t('extraction_failed'), message)
  } finally {
    isExtracting.value = false
  }
}

onMounted(loadReceipt)
</script>

<style scoped>
.upload-status-inline {
  padding: 0.75rem 1rem;
  background: #f5f6fa;
  border-radius: 8px;
  border: 1px solid #e1e4ed;
  margin-bottom: 1.25rem;
}

.badge-failed {
  background: #fff0f0;
  color: #842029;
}
</style>
