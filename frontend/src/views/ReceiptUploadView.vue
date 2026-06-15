<template>
  <AppLayout>
    <!-- Back link -->
    <RouterLink :to="{ name: 'receipts' }" class="back-link">
      ← {{ t('back_to_receipts') }}
    </RouterLink>

    <div class="page-header" style="justify-content: center; margin-bottom: 2rem;">
      <h1 style="text-align: center;">{{ t('upload_receipt') }}</h1>
    </div>

    <div class="upload-card detail-card">
      <!-- AI quota notice -->
      <p class="quota-notice">{{ t('ai_quota_notice') }}</p>

      <!-- File input -->
      <div class="form-group">
        <label for="ru-file-input">{{ t('select_file') }}</label>
        <input
          id="ru-file-input"
          ref="fileInputRef"
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.pdf"
          class="file-input"
          :disabled="isBusy"
          @change="handleFileChange"
        />
        <p class="field-hint">{{ t('allowed_file_types') }}</p>
        <p v-if="validationError" class="field-error">{{ validationError }}</p>
      </div>

      <!-- Selected file preview -->
      <div v-if="selectedFile" class="selected-file-section">
        <h3 class="selected-file-heading">{{ t('selected_file') }}</h3>

        <!-- Image preview -->
        <div v-if="previewUrl && isImageFile" class="image-preview-wrapper">
          <img :src="previewUrl" :alt="selectedFile.name" class="image-preview" />
        </div>

        <!-- PDF indicator -->
        <div v-else-if="isPdfFile" class="pdf-indicator">
          <span class="pdf-icon" aria-hidden="true">📄</span>
          <span>{{ t('pdf_file') }}</span>
        </div>

        <!-- File metadata -->
        <div class="selected-file-meta detail-grid" style="margin-top:0.75rem;">
          <div class="detail-field">
            <label>{{ t('file_name') }}</label>
            <span>{{ selectedFile.name }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('file_type') }}</label>
            <span>{{ selectedFile.type }}</span>
          </div>
          <div class="detail-field">
            <label>{{ t('file_size') }}</label>
            <span>{{ formatFileSize(selectedFile.size) }}</span>
          </div>
        </div>
      </div>

      <!-- Upload progress / status text -->
      <div v-if="uploadState !== 'idle'" class="upload-status-section">
        <div v-if="uploadState === 'uploading'">
          <p class="upload-status-text">
            <span v-if="uploadProgress > 0">{{ t('upload_progress') }}: {{ uploadProgress }}%</span>
            <span v-else>{{ t('uploading_receipt') }}</span>
          </p>
          <div class="progress-bar-track" role="progressbar" :aria-valuenow="uploadProgress" aria-valuemin="0" aria-valuemax="100">
            <div class="progress-bar-fill" :style="{ width: `${uploadProgress}%` }"></div>
          </div>
        </div>

        <div v-else-if="uploadState === 'extracting'">
          <p class="upload-status-text">{{ t('analyzing_receipt') }}</p>
          <p class="upload-status-sub">{{ t('analysis_may_take_a_moment') }}</p>
        </div>
      </div>

      <!-- Submit button -->
      <div class="form-actions" style="margin-bottom:0;">
        <RouterLink :to="{ name: 'receipts' }" class="btn btn-secondary" style="text-decoration:none;">
          {{ t('cancel') }}
        </RouterLink>
        <button
          id="ru-submit-btn"
          class="btn btn-primary"
          style="width:auto;"
          :disabled="isBusy || !selectedFile"
          @click="handleUploadAndExtract"
        >
          {{ isBusy ? t('saving') : t('upload_and_extract') }}
        </button>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import { uploadReceipt, extractReceipt } from '../api/receiptApi'
import { showSuccessAlert, showErrorAlert, showLoadingAlert, closeAlert } from '../utils/alerts'

const { t } = useI18n()
const router = useRouter()

// ── State ─────────────────────────────────────────────────────────────────────

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const previewUrl = ref<string | null>(null)
const validationError = ref<string | null>(null)
const uploadState = ref<'idle' | 'uploading' | 'extracting' | 'success' | 'error'>('idle')
const uploadProgress = ref(0)

// ── Computed ──────────────────────────────────────────────────────────────────

const isBusy = computed(() => uploadState.value === 'uploading' || uploadState.value === 'extracting')

const isImageFile = computed(() => {
  if (!selectedFile.value) return false
  return selectedFile.value.type.startsWith('image/')
})

const isPdfFile = computed(() => {
  if (!selectedFile.value) return false
  return selectedFile.value.type === 'application/pdf'
})

// ── Constants ─────────────────────────────────────────────────────────────────

const ALLOWED_MIME_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/pdf',
])

const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  // 10 MB — matches backend MAX_RECEIPT_FILE_SIZE_MB

// ── File helpers ──────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function revokePreview(): void {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = null
  }
}

// ── File selection and validation ─────────────────────────────────────────────

function handleFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0] ?? null

  // Clear previous preview
  revokePreview()
  validationError.value = null
  selectedFile.value = null

  if (!file) return

  // Validate type
  if (!ALLOWED_MIME_TYPES.has(file.type)) {
    validationError.value = t('unsupported_file')
    return
  }

  // Validate size
  if (file.size > MAX_FILE_SIZE_BYTES) {
    validationError.value = t('file_too_large')
    return
  }

  // Validate not empty
  if (file.size === 0) {
    validationError.value = t('invalid_file')
    return
  }

  selectedFile.value = file

  // Create object URL preview for images
  if (file.type.startsWith('image/')) {
    previewUrl.value = URL.createObjectURL(file)
  }
}

// ── Upload + extract flow ─────────────────────────────────────────────────────

async function handleUploadAndExtract(): Promise<void> {
  if (!selectedFile.value || isBusy.value) return

  // Clear any previous validation error
  validationError.value = null
  uploadProgress.value = 0
  uploadState.value = 'uploading'
  
  showLoadingAlert(t('uploading_receipt'), t('analysis_may_take_a_moment'))

  let receipt
  try {
    receipt = await uploadReceipt(selectedFile.value, (percent) => {
      uploadProgress.value = percent
    })
  } catch (err: unknown) {
    uploadState.value = 'error'
    closeAlert()
    const detail = extractErrorDetail(err)
    await showErrorAlert(t('upload_failed'), detail)
    uploadState.value = 'idle'
    return
  }

  // Upload succeeded — now extract
  uploadState.value = 'extracting'

  let expense
  try {
    expense = await extractReceipt(receipt.id)
  } catch (err: unknown) {
    uploadState.value = 'error'
    closeAlert()
    const detail = mapGeminiError(err)
    await showErrorAlert(t('extraction_failed'), detail)
    uploadState.value = 'idle'
    return
  }

  uploadState.value = 'success'
  closeAlert()

  await showSuccessAlert(t('receipt_uploaded'), t('receipt_uploaded_message'))

  // Navigate to the draft expense edit page
  router.push({ name: 'expense-edit', params: { id: expense.id } })
}

// ── Error helpers ─────────────────────────────────────────────────────────────

function extractErrorDetail(err: unknown): string {
  const response = (err as { response?: { data?: { detail?: unknown }; status?: number } })?.response
  if (!response) return t('something_went_wrong')

  const detail = response.data?.detail
  if (typeof detail === 'string') return sanitizeErrorMessage(detail)

  return t('something_went_wrong')
}

function mapGeminiError(err: unknown): string {
  const response = (err as { response?: { data?: { detail?: unknown }; status?: number } })?.response
  const status = response?.status
  const rawDetail = response?.data?.detail

  // Never expose raw Gemini details, API keys, or stack traces
  if (status === 503) return t('gemini_not_configured')
  if (status === 429) return t('gemini_quota_exceeded')
  if (status === 409) return t('receipt_already_extracted')

  if (typeof rawDetail === 'string') {
    return sanitizeErrorMessage(rawDetail)
  }

  return t('something_went_wrong')
}

// Strip any content that looks like an API key, path, or stack trace
function sanitizeErrorMessage(message: string): string {
  // If the message is long (likely a stack trace or raw error), use generic fallback
  if (message.length > 200) return t('something_went_wrong')
  return message
}

// ── Cleanup ───────────────────────────────────────────────────────────────────

onUnmounted(revokePreview)
</script>

<style scoped>
.upload-card {
  max-width: 640px;
  margin: 0 auto;
}

.quota-notice {
  font-size: 0.85rem;
  color: #888;
  margin-bottom: 1.25rem;
  padding: 0.6rem 0.85rem;
  background: #f5f6fa;
  border-radius: 6px;
  border-left: 3px solid #4a6cf7;
}

.file-input {
  display: block;
  width: 100%;
  padding: 0.5rem 0;
  font-size: 0.95rem;
  color: #1a1a2e;
  cursor: pointer;
}

.file-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.field-hint {
  font-size: 0.8rem;
  color: #888;
  margin-top: 0.3rem;
}

.selected-file-section {
  margin-top: 1.25rem;
  padding-top: 1.25rem;
  border-top: 1px solid #f0f0f0;
}

.selected-file-heading {
  font-size: 1rem;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 0.75rem;
}

.image-preview-wrapper {
  margin-bottom: 0.75rem;
  border: 1px solid #e1e4ed;
  border-radius: 8px;
  overflow: hidden;
  max-width: 100%;
  background: #f5f6fa;
  display: flex;
  justify-content: center;
}

.image-preview {
  max-width: 100%;
  max-height: 300px;
  object-fit: contain;
  display: block;
}

.pdf-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background: #f5f6fa;
  border: 1px solid #e1e4ed;
  border-radius: 8px;
  font-size: 0.95rem;
  color: #555;
  margin-bottom: 0.75rem;
}

.pdf-icon {
  font-size: 2rem;
}

.upload-status-section {
  margin-top: 1.25rem;
  padding: 1rem;
  background: #f5f6fa;
  border-radius: 8px;
  border: 1px solid #e1e4ed;
}

.upload-status-text {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 0.5rem;
}

.upload-status-sub {
  font-size: 0.85rem;
  color: #888;
}

.progress-bar-track {
  width: 100%;
  height: 8px;
  background: #e1e4ed;
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: #4a6cf7;
  border-radius: 4px;
  transition: width 0.2s ease;
}
</style>
