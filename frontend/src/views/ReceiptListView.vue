<template>
  <AppLayout>
    <!-- Page header -->
    <div class="page-header">
      <h1>{{ t('receipts') }}</h1>
      <RouterLink :to="{ name: 'receipt-upload' }" class="btn btn-primary" style="width:auto; text-decoration:none;">
        {{ t('upload_receipt') }}
      </RouterLink>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="state-container">
      <p>{{ t('loading_receipts') }}</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="state-container">
      <div class="alert alert-error" style="display:inline-block; text-align:left; max-width:420px;">
        {{ error }}
      </div>
      <br />
      <button class="btn btn-secondary" style="margin-top:1rem;" @click="loadReceipts">
        {{ t('retry') }}
      </button>
    </div>

    <!-- Empty -->
    <div v-else-if="receipts.length === 0" class="state-container">
      <p>{{ t('no_receipts_found') }}</p>
      <p class="state-subtitle">{{ t('no_receipts_subtitle') }}</p>
      <RouterLink :to="{ name: 'receipt-upload' }" class="btn btn-primary" style="width:auto; text-decoration:none; display:inline-block; margin-top:1rem;">
        {{ t('upload_receipt') }}
      </RouterLink>
    </div>

    <!-- Receipt list -->
    <div v-else class="receipt-list">
      <div v-for="receipt in receipts" :key="receipt.id" class="receipt-card recent-expense-row">
        <div class="recent-expense-info">
          <div class="recent-expense-icon" style="background: rgba(0, 240, 255, 0.08); color: var(--color-brand-accent);">
            📄
          </div>
          <div class="recent-expense-details">
            <div class="receipt-card-filename" style="margin-bottom:0.2rem;">{{ receipt.original_filename }}</div>
            <div class="receipt-card-meta">
              <span>{{ receipt.mime_type }}</span>
              <span>{{ formatFileSize(receipt.file_size) }}</span>
              <span>{{ formatDateTime(receipt.uploaded_at) }}</span>
              <span
                class="badge"
                :class="statusBadgeClass(receipt.upload_status)"
              >
                {{ t(statusLabel(receipt.upload_status)) }}
              </span>
            </div>
          </div>
        </div>

        <div class="recent-expense-right" style="flex-direction: row; gap: 0.5rem; align-items: center;">
          <RouterLink
            :to="{ name: 'receipt-detail', params: { id: receipt.id } }"
            class="btn btn-secondary"
            style="text-decoration:none; font-size:0.85rem; padding:0.4rem 0.75rem;"
          >
            {{ t('view_receipt') }}
          </RouterLink>
          <RouterLink
            v-if="receipt.expense_id !== null"
            :to="{ name: 'expense-detail', params: { id: receipt.expense_id } }"
            class="btn btn-primary"
            style="text-decoration:none; font-size:0.85rem; padding:0.4rem 0.75rem;"
          >
            {{ t('open_expense') }}
          </RouterLink>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import { getReceipts } from '../api/receiptApi'
import { formatDateTime } from '../utils/formatters'
import type { Receipt } from '../types/receipt'

const { t } = useI18n()

const receipts = ref<Receipt[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)

// Convert bytes to a human-readable size string
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Map upload_status to an i18n key for display
function statusLabel(status: string): string {
  const map: Record<string, string> = {
    uploaded: 'status_uploaded',
    extracted: 'status_extracted',
    processing: 'status_processing',
    failed: 'status_failed',
  }
  return map[status] ?? 'status_uploaded'
}

// Map upload_status to a badge CSS class
function statusBadgeClass(status: string): string {
  const map: Record<string, string> = {
    uploaded: 'badge-draft',
    extracted: 'badge-confirmed',
    processing: 'badge-ai',
    failed: 'badge-failed',
  }
  return map[status] ?? 'badge-draft'
}

async function loadReceipts(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    receipts.value = await getReceipts()
  } catch {
    error.value = t('unable_to_load_receipts')
  } finally {
    isLoading.value = false
  }
}

onMounted(loadReceipts)
</script>

<style scoped>
.receipt-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.receipt-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.07);
  padding: 1.25rem 1.5rem;
}

.receipt-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.receipt-card-filename {
  font-size: 1.02rem;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 0.4rem;
  word-break: break-all;
}

.receipt-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: 0.82rem;
  color: #666;
  align-items: center;
}

.receipt-card-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  align-items: flex-start;
  flex-shrink: 0;
}

.badge-failed {
  background: #fff0f0;
  color: #842029;
}
</style>
