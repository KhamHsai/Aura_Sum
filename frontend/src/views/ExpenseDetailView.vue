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
                v-if="!expense.is_confirmed"
                class="btn btn-confirm"
                :disabled="isConfirming"
                @click="handleConfirm"
              >
                {{ isConfirming ? t('confirming') : t('confirm_expense') }}
              </button>
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

      <!-- Translation card -->
      <div class="detail-card translation-section">
        <h2>{{ t('translate_expense') }}</h2>

        <p class="translation-quota-notice">{{ t('ai_translation_quota_notice') }}</p>

        <!-- Language selector and translate button -->
        <div class="translation-controls">
          <label for="target-language-select" class="translation-label">
            {{ t('target_language') }}
          </label>
          <select
            id="target-language-select"
            v-model="targetLanguage"
            class="translation-select"
            :disabled="isTranslating"
            aria-label="target language"
          >
            <option value="en">{{ t('lang_en') }}</option>
            <option value="th">{{ t('lang_th') }}</option>
          </select>

          <button
            class="btn btn-primary"
            :disabled="isTranslating"
            @click="handleTranslate"
          >
            {{ isTranslating ? t('translating') : t('translate') }}
          </button>
        </div>

        <!-- Loading state -->
        <div v-if="isTranslating" class="translation-loading" aria-live="polite">
          <span class="translation-spinner" aria-hidden="true">⏳</span>
          {{ t('translating') }} {{ t('translation_may_take_a_moment') }}
        </div>

        <!-- Translation error -->
        <div v-if="translationError && !isTranslating" class="alert alert-error translation-error">
          {{ translationError }}
        </div>

        <!-- Translation result -->
        <div v-if="translationResult && !isTranslating" class="translation-result">

          <!-- Title comparison -->
          <div class="translation-comparison">
            <div class="translation-original">
              <label>{{ t('original_title') }}</label>
              <span>{{ expense.title }}</span>
            </div>
            <div class="translation-translated">
              <label>{{ t('translated_title') }}</label>
              <span>{{ translationResult.translated_title ?? t('no_translation_available') }}</span>
            </div>
          </div>

          <!-- Notes comparison (only if expense has notes) -->
          <div v-if="expense.notes" class="translation-comparison">
            <div class="translation-original">
              <label>{{ t('original_notes') }}</label>
              <span>{{ expense.notes }}</span>
            </div>
            <div class="translation-translated">
              <label>{{ t('translated_notes') }}</label>
              <span>{{ translationResult.translated_notes ?? t('no_translation_available') }}</span>
            </div>
          </div>

          <!-- Translated items (only if there are items with translations) -->
          <div v-if="translationResult.items.length > 0" class="translation-items">
            <h3 style="font-size:1rem; color:#1a1a2e; margin-bottom:0.75rem;">
              {{ t('expense_items') }}
            </h3>
            <div
              v-for="tItem in translationResult.items"
              :key="tItem.item_id"
              class="translation-item-row"
            >
              <div class="translation-original">
                <label>{{ t('original_name') }}</label>
                <span>{{ tItem.original_name ?? t('no_translation_available') }}</span>
              </div>
              <div class="translation-translated">
                <label>{{ t('translated_name') }}</label>
                <span>{{ tItem.translated_name ?? t('no_translation_available') }}</span>
              </div>
              <div class="translation-name-pair">
                <span class="translation-name-tag">EN</span>
                <span>{{ tItem.name_en ?? t('no_translation_available') }}</span>
                <span class="translation-name-tag">TH</span>
                <span>{{ tItem.name_th ?? t('no_translation_available') }}</span>
              </div>
            </div>
          </div>
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
import { getExpenseById, deleteExpense, confirmExpense, translateExpense } from '../api/expenseApi'
import { showDeleteConfirmation, showSuccessAlert, showErrorAlert } from '../utils/alerts'
import { formatMoney, formatDate, formatDateTime } from '../utils/formatters'
import type { Expense, ExpenseItem } from '../types/expense'
import type { TranslationLanguage, ExpenseTranslationResponse } from '../types/translation'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const expense = ref<Expense | null>(null)
const isLoading = ref(false)
const isDeleting = ref(false)
const isConfirming = ref(false)
const error = ref<string | null>(null)
const notFound = ref(false)

// Translation state — kept local to this view
const targetLanguage = ref<TranslationLanguage>(locale.value === 'th' ? 'th' : 'en')
const isTranslating = ref(false)
const translationResult = ref<ExpenseTranslationResponse | null>(null)
const translationError = ref<string | null>(null)

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

/** Map backend error status codes to safe user-facing messages. */
function getTranslationErrorMessage(err: unknown): string {
  const status = (err as { response?: { status?: number } })?.response?.status
  if (status === 503) return t('gemini_not_configured_translation')
  if (status === 429) return t('gemini_quota_exceeded_translation')
  if (status === 422) return t('unsupported_language')
  if (status === 404) return t('expense_not_found')
  return t('translation_service_unavailable')
}

async function handleTranslate(): Promise<void> {
  if (!expense.value || isTranslating.value) return

  isTranslating.value = true
  translationError.value = null

  try {
    const result = await translateExpense(expense.value.id, targetLanguage.value)
    translationResult.value = result
    await showSuccessAlert(t('translation_completed'), t('translation_completed_message'))
  } catch (err: unknown) {
    translationError.value = getTranslationErrorMessage(err)
    await showErrorAlert(t('unable_to_translate_expense'), translationError.value)
  } finally {
    isTranslating.value = false
  }
}

async function handleConfirm(): Promise<void> {
  if (!expense.value || isConfirming.value) return

  const result = await showDeleteConfirmation({
    title: t('confirm_expense_title'),
    text: t('confirm_expense_message'),
    confirmButtonText: t('confirm_expense'),
    cancelButtonText: t('cancel'),
  })

  if (!result.isConfirmed) return

  isConfirming.value = true

  try {
    const updated = await confirmExpense(expense.value.id)
    expense.value = updated
    await showSuccessAlert(t('expense_confirmed'), t('expense_confirmed_message'))
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number; data?: { detail?: string } } })?.response?.status
    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    if (status === 409) {
      const msg = typeof detail === 'string' ? detail : t('already_confirmed')
      await showErrorAlert(t('unable_to_confirm_expense'), msg)
    } else if (status === 422) {
      const msg = typeof detail === 'string' ? detail : t('incomplete_expense')
      await showErrorAlert(t('unable_to_confirm_expense'), msg)
    } else if (status === 404) {
      await showErrorAlert(t('expense_not_found'))
    } else {
      await showErrorAlert(t('unable_to_confirm_expense'), t('please_review_and_try_again'))
    }
  } finally {
    isConfirming.value = false
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

<style scoped>
/* Translation section */
.translation-section {
  margin-top: 1.5rem;
}

.translation-quota-notice {
  font-size: 0.85rem;
  color: #888;
  margin-bottom: 1rem;
}

.translation-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.translation-label {
  font-weight: 500;
  color: #333;
  white-space: nowrap;
}

.translation-select {
  padding: 0.4rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 0.95rem;
  background: #fff;
  cursor: pointer;
}

.translation-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.translation-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #555;
  font-size: 0.95rem;
  padding: 0.75rem 0;
}

.translation-spinner {
  font-size: 1.1rem;
}

.translation-error {
  margin-top: 0.5rem;
}

.translation-result {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Original / translated comparison grid */
.translation-comparison {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  padding: 0.75rem;
  background: #f8f9ff;
  border-radius: 8px;
  border: 1px solid #e0e4f8;
}

.translation-original label,
.translation-translated label {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #777;
  margin-bottom: 0.25rem;
}

.translation-original span {
  color: #1a1a2e;
  font-size: 0.95rem;
}

.translation-translated span {
  color: #4a6cf7;
  font-size: 0.95rem;
}

/* Item translation rows */
.translation-items {
  border-top: 1px solid #e0e4f8;
  padding-top: 0.75rem;
}

.translation-item-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #f8f9ff;
  border-radius: 8px;
  border: 1px solid #e0e4f8;
  margin-bottom: 0.5rem;
}

.translation-name-pair {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.85rem;
  color: #555;
}

.translation-name-tag {
  background: #e0e4f8;
  color: #4a6cf7;
  font-weight: 700;
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}

/* Responsive */
@media (max-width: 600px) {
  .translation-comparison,
  .translation-item-row {
    grid-template-columns: 1fr;
  }
}
</style>
