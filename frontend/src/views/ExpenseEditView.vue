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
        :initial-data="initialForm"
        :categories="categories"
        :loading-categories="loadingCategories"
        :is-submitting="isSubmitting"
        :submit-label="t('update_expense')"
        :backend-error="backendError"
        @submit="handleSubmit"
        @cancel="router.push({ name: 'expense-detail', params: { id: expenseId } })"
      />
    </template>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import ExpenseForm from '../components/ExpenseForm.vue'
import { getCategories, createCategory } from '../api/categoryApi'
import { getExpenseById, updateExpense } from '../api/expenseApi'
import { showSuccessAlert, showErrorAlert } from '../utils/alerts'
import type { Category } from '../types/category'
import type {
  Expense,
  ExpenseFormData,
  ExpenseUpdateRequest,
  ExpenseItemCreateRequest,
} from '../types/expense'

const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()

const categories = ref<Category[]>([])
const loadingCategories = ref(false)
const isLoading = ref(false)
const isSubmitting = ref(false)
const notFound = ref(false)
const loadError = ref<string | null>(null)
const backendError = ref<string | null>(null)
let expenseId = 0

// Reactive initial data for the form — starts empty, filled after load
const initialForm = ref<ExpenseFormData>(emptyForm())

function emptyForm(): ExpenseFormData {
  return {
    category_id: null,
    category_name: '',
    paid_to: '',
    tax_id: '',
    receipt_number: '',
    receipt_date: '',
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

function expenseToForm(expense: Expense): ExpenseFormData {
  return {
    category_id: expense.category_id,
    category_name: expense.category_name ?? '',    paid_to: expense.paid_to ?? '',
    tax_id: expense.tax_id ?? '',
    receipt_number: expense.receipt_number ?? '',
    receipt_date: expense.receipt_date,
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
      // display_name shows the correct language — TH receipt stays Thai by default
      display_name: locale.value === 'th'
        ? (item.name_th ?? item.original_name ?? item.name_en ?? '')
        : (item.name_en ?? item.original_name ?? item.name_th ?? ''),
      quantity: item.quantity,
      unit: item.unit ?? '',
      unit_price: item.unit_price ?? '',
      discount_amount: item.discount_amount,
      total_price: item.total_price,
    })),
  }
}

/**
 * Resolve category_name to an id.
 * 1. Exact match (case-insensitive) against loaded categories → use existing id.
 * 2. No match → create a new category on the backend and use the returned id.
 * 3. Empty string → null (no category).
 */
async function resolveCategoryId(name: string): Promise<number | null> {
  const search = name.trim().toLowerCase()
  if (!search) return null

  const found = categories.value.find(
    c => c.name_en.toLowerCase() === search || c.name_th.toLowerCase() === search
  )
  if (found) return found.id

  const created = await createCategory(name.trim())
  if (!categories.value.find(c => c.id === created.id)) {
    categories.value.push(created)
  }
  return created.id
}

// Build the PUT request payload — always include all items (full replacement)
async function buildRequest(form: ExpenseFormData): Promise<ExpenseUpdateRequest> {
  const items: ExpenseItemCreateRequest[] = form.items.map((item) => ({
    original_name: item.original_name.trim() || item.name_th.trim() || item.display_name.trim() || item.name_en.trim(),
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
    category_id: await resolveCategoryId(form.category_name),
    paid_to: form.paid_to.trim() || null,
    tax_id: form.tax_id.trim() || null,
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
async function handleSubmit(form: ExpenseFormData): Promise<void> {
  isSubmitting.value = true
  backendError.value = null

  try {
    const request = await buildRequest(form)
    await updateExpense(expenseId, request)
    await showSuccessAlert(t('expense_updated'), t('expense_updated_message'))
    router.push({ name: 'expenses' })
  } catch (err: unknown) {
    const response = (err as { response?: { status?: number } })?.response
    backendError.value = parseBackendError(err)
    if (!response || (response.status !== 422 && response.status !== 400)) {
      await showErrorAlert(t('unable_to_save_expense'), t('something_went_wrong'))
    }
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadData)
</script>
