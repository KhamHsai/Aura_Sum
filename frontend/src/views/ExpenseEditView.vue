<template>
  <AppLayout>
    <!-- Loading -->
    <div v-if="isLoading" class="state-container">
      <p>{{ t('loading_expense') }}</p>
    </div>

    <!-- Not found -->
    <div v-else-if="notFound" class="state-container">
      <div class="alert alert-error" style="display:inline-block; max-width:420px;">
        {{ t('expense_not_found') }}
      </div>
    </div>

    <!-- Error loading expense -->
    <div v-else-if="loadError" class="state-container">
      <div class="alert alert-error" style="display:inline-block; max-width:420px;">
        {{ loadError }}
      </div>
    </div>

    <!-- Edit form -->
    <template v-else>
      <div class="page-header">
        <h1>{{ t('edit_expense') }}</h1>
      </div>

      <ExpenseForm
        ref="expenseFormRef"
        :initial-data="initialForm"
        :categories="categories"
        :loading-categories="loadingCategories"
        :is-submitting="isSubmitting"
        :submit-label="isConfirming ? t('confirming') : t('update_expense')"
        :backend-error="backendError"
        @submit="handleSubmit"
        @cancel="router.push({ name: 'expense-detail', params: { id: expenseId } })"
      />

      <!-- Confirm Expense button — only visible for unconfirmed draft expenses -->
      <div v-if="loadedExpense && !loadedExpense.is_confirmed" class="form-actions" style="margin-top:0;">
        <button
          type="button"
          class="btn btn-confirm"
          style="width:auto;"
          :disabled="isSubmitting || isConfirming"
          @click="handleConfirmClick"
        >
          {{ isConfirming ? t('confirming') : t('confirm_expense') }}
        </button>
      </div>
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import ExpenseForm from '../components/ExpenseForm.vue'
import { getCategories } from '../api/categoryApi'
import { getExpenseById, updateExpense, confirmExpense } from '../api/expenseApi'
import { showSuccessAlert, showErrorAlert, showDeleteConfirmation } from '../utils/alerts'
import type { Category } from '../types/category'
import type {
  Expense,
  ExpenseFormData,
  ExpenseUpdateRequest,
  ExpenseItemCreateRequest,
} from '../types/expense'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const categories = ref<Category[]>([])
const loadingCategories = ref(false)
const isLoading = ref(false)
const isSubmitting = ref(false)
const isConfirming = ref(false)
// Tracks whether the next form submit should trigger save+confirm.
const confirmPending = ref(false)
// Holds the loaded expense so we can check is_confirmed after load.
const loadedExpense = ref<Expense | null>(null)
const notFound = ref(false)
const loadError = ref<string | null>(null)
const backendError = ref<string | null>(null)
let expenseId = 0

// Template ref to the ExpenseForm component's root form element
const expenseFormRef = ref<InstanceType<typeof ExpenseForm> | null>(null)

// Reactive initial data for the form — starts empty, filled after load
const initialForm = ref<ExpenseFormData>(emptyForm())

function emptyForm(): ExpenseFormData {
  return {
    category_id: null,
    title: '',
    merchant_name: '',
    receipt_number: '',
    receipt_date: '',
    document_type: '',
    payment_method: '',
    currency: 'THB',
    subtotal: '',
    tax_amount: '',
    discount_amount: '',
    total_amount: '',
    notes: '',
    items: [],
  }
}

// Convert an Expense response into editable form data
function expenseToForm(expense: Expense): ExpenseFormData {
  return {
    category_id: expense.category_id,
    title: expense.title,
    merchant_name: expense.merchant_name ?? '',
    receipt_number: expense.receipt_number ?? '',
    receipt_date: expense.receipt_date,
    document_type: '',
    payment_method: expense.payment_method ?? '',
    currency: expense.currency,
    subtotal: expense.subtotal ?? '',
    tax_amount: expense.tax_amount ?? '',
    discount_amount: expense.discount_amount ?? '',
    total_amount: expense.total_amount,
    notes: expense.notes ?? '',
    items: expense.items.map((item) => ({
      category_id: item.category_id,
      original_name: item.original_name,
      name_en: item.name_en ?? '',
      name_th: item.name_th ?? '',
      quantity: item.quantity,
      unit: item.unit ?? '',
      unit_price: item.unit_price ?? '',
      discount_amount: item.discount_amount,
      total_price: item.total_price,
    })),
  }
}

// Build the PUT request payload — always include all items (full replacement)
function buildRequest(form: ExpenseFormData): ExpenseUpdateRequest {
  const items: ExpenseItemCreateRequest[] = form.items.map((item) => ({
    original_name: item.original_name.trim() || item.name_en.trim() || item.name_th.trim(),
    name_en: item.name_en.trim() || null,
    name_th: item.name_th.trim() || null,
    quantity: item.quantity.trim(),
    unit: item.unit.trim() || null,
    unit_price: item.unit_price.trim() || null,
    discount_amount: item.discount_amount.trim() || '0',
    total_price: item.total_price.trim() || '0',
    category_id: item.category_id,
  }))

  return {
    category_id: form.category_id,
    title: form.title.trim(),
    merchant_name: form.merchant_name.trim() || null,
    receipt_number: form.receipt_number.trim() || null,
    receipt_date: form.receipt_date,
    payment_method: form.payment_method.trim() || null,
    currency: form.currency.trim(),
    subtotal: form.subtotal.trim() || null,
    tax_amount: form.tax_amount.trim() || null,
    discount_amount: form.discount_amount.trim() || null,
    total_amount: form.total_amount.trim(),
    notes: form.notes.trim() || null,
    items,
  }
}

function parseBackendError(err: unknown): string {
  const response = (err as { response?: { data?: { detail?: unknown }; status?: number } })?.response
  if (!response) return t('unable_to_save_expense')

  const detail = response.data?.detail
  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    return detail.map((d: { msg?: string }) => d.msg ?? '').filter(Boolean).join('; ')
  }

  return t('unable_to_save_expense')
}

async function loadData(): Promise<void> {
  // Validate route param
  const rawId = route.params.id
  const parsed = parseInt(String(rawId), 10)
  if (isNaN(parsed) || parsed <= 0) {
    notFound.value = true
    return
  }
  expenseId = parsed

  isLoading.value = true
  loadError.value = null

  try {
    const [cats, expense] = await Promise.all([
      getCategories().catch(() => [] as Category[]),
      getExpenseById(expenseId),
    ])
    categories.value = cats
    initialForm.value = expenseToForm(expense)
    loadedExpense.value = expense
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 404) {
      notFound.value = true
    } else {
      loadError.value = t('unable_to_connect')
    }
  } finally {
    isLoading.value = false
    loadingCategories.value = false
  }
}

// Called by ExpenseForm when it validates successfully and emits 'submit'.
// When confirmPending is true, save first then confirm.
async function handleSubmit(form: ExpenseFormData): Promise<void> {
  const shouldConfirm = confirmPending.value
  confirmPending.value = false

  isSubmitting.value = true
  backendError.value = null

  if (shouldConfirm) {
    isConfirming.value = true
  }

  try {
    const request = buildRequest(form)
    await updateExpense(expenseId, request)

    if (!shouldConfirm) {
      // Normal save — show success and go to detail
      await showSuccessAlert(t('expense_updated'), t('expense_updated_message'))
      router.push({ name: 'expense-detail', params: { id: expenseId } })
      return
    }

    // Save succeeded — now confirm
    try {
      await confirmExpense(expenseId)
      await showSuccessAlert(t('expense_confirmed'), t('expense_confirmed_message'))
      router.push({ name: 'expense-detail', params: { id: expenseId } })
    } catch (confirmErr: unknown) {
      // Save succeeded but confirm failed — stay on page and show error
      const status = (confirmErr as { response?: { status?: number; data?: { detail?: string } } })?.response?.status
      const detail = (confirmErr as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      if (status === 409) {
        const msg = typeof detail === 'string' ? detail : t('already_confirmed')
        await showErrorAlert(t('unable_to_confirm_expense'), msg)
      } else if (status === 422) {
        const msg = typeof detail === 'string' ? detail : t('incomplete_expense')
        await showErrorAlert(t('unable_to_confirm_expense'), msg)
      } else {
        await showErrorAlert(t('unable_to_confirm_expense'), t('please_review_and_try_again'))
      }
    }
  } catch (err: unknown) {
    const response = (err as { response?: { status?: number } })?.response
    backendError.value = parseBackendError(err)
    if (!response || (response.status !== 422 && response.status !== 400)) {
      await showErrorAlert(t('unable_to_save_expense'), t('something_went_wrong'))
    }
  } finally {
    isSubmitting.value = false
    isConfirming.value = false
  }
}

// Called by the "Confirm Expense" button below the form.
// Shows SweetAlert2 dialog first, then sets confirmPending and programmatically
// submits the form to trigger its own validation before saving+confirming.
async function handleConfirmClick(): Promise<void> {
  if (isSubmitting.value || isConfirming.value) return

  const result = await showDeleteConfirmation({
    title: t('confirm_expense_title'),
    text: t('confirm_expense_message'),
    confirmButtonText: t('confirm_expense'),
    cancelButtonText: t('cancel'),
  })

  if (!result.isConfirmed) return

  // Flag the next handleSubmit call to also confirm after saving
  confirmPending.value = true

  // Trigger the form's own validation + submit via its exposed submitForm method
  if (expenseFormRef.value) {
    expenseFormRef.value.submitForm()
  } else {
    // Fallback — should not happen in normal usage
    confirmPending.value = false
  }
}

onMounted(loadData)
</script>
