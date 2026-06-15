<template>
  <AppLayout>
    <!-- Page header -->
    <div class="page-header">
      <h1>{{ t('create_expense') }}</h1>
    </div>

    <!-- Category loading indicator -->
    <div v-if="loadingCategories" class="state-container" style="padding:2rem 0;">
      <p>{{ t('loading_categories') }}</p>
    </div>

    <!-- Form (shown once categories have loaded, or if they failed — user can still fill in) -->
    <ExpenseForm
      :initial-data="initialForm"
      :categories="categories"
      :loading-categories="loadingCategories"
      :is-submitting="isSubmitting"
      :submit-label="t('save_expense')"
      :backend-error="backendError"
      @submit="handleSubmit"
      @cancel="router.push({ name: 'expenses' })"
    />
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppLayout from '../layouts/AppLayout.vue'
import ExpenseForm from '../components/ExpenseForm.vue'
import { getCategories } from '../api/categoryApi'
import { createExpense } from '../api/expenseApi'
import { showSuccessAlert, showErrorAlert } from '../utils/alerts'
import type { Category } from '../types/category'
import type {
  ExpenseFormData,
  ExpenseCreateRequest,
  ExpenseItemCreateRequest,
} from '../types/expense'

const { t } = useI18n()
const router = useRouter()

const categories = ref<Category[]>([])
const loadingCategories = ref(false)
const isSubmitting = ref(false)
const backendError = ref<string | null>(null)

// Empty starting form — defaults that make sense for a new expense
const initialForm: ExpenseFormData = {
  category_id: null,
  category_name: '',
  paid_to: '',
  tax_id: '',
  receipt_number: '',
  receipt_date: todayDateString(),
  payment_method: '',
  currency: 'THB',
  subtotal: '',
  tax_amount: '',
  discount_amount: '',
  total_amount: '',
  notes: '',
  items: [],
}

function todayDateString(): string {
  return new Date().toISOString().slice(0, 10)
}

async function loadCategories(): Promise<void> {
  loadingCategories.value = true
  try {
    categories.value = await getCategories()
  } catch {
    // Non-fatal — user sees an empty dropdown but can still submit
  } finally {
    loadingCategories.value = false
  }
}

// Resolve category_name text → category_id (case-insensitive, partial match)
function resolveCategoryId(name: string): number | null {
  const search = name.trim().toLowerCase()
  if (!search) return null
  // Exact match first
  let found = categories.value.find(
    c => c.name_en.toLowerCase() === search || c.name_th.toLowerCase() === search
  )
  // Partial match fallback
  if (!found) {
    found = categories.value.find(
      c => c.name_en.toLowerCase().includes(search) || search.includes(c.name_en.toLowerCase()) ||
           c.name_th.toLowerCase().includes(search) || search.includes(c.name_th.toLowerCase())
    )
  }
  return found?.id ?? null
}

// Convert the form data to the exact shape the backend expects
function buildRequest(form: ExpenseFormData): ExpenseCreateRequest {
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
    category_id: resolveCategoryId(form.category_name),
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
    // FastAPI 422 validation errors: [{loc, msg, type}]
    return detail.map((d: { msg?: string }) => d.msg ?? '').filter(Boolean).join('; ')
  }

  return t('unable_to_save_expense')
}

async function handleSubmit(form: ExpenseFormData): Promise<void> {
  isSubmitting.value = true
  backendError.value = null

  try {
    const request = buildRequest(form)
    const created = await createExpense(request)
    await showSuccessAlert(t('expense_created'), t('expense_created_message'))
    router.push({ name: 'expense-detail', params: { id: created.id } })
  } catch (err: unknown) {
    const response = (err as { response?: { status?: number } })?.response
    backendError.value = parseBackendError(err)
    // Show a popup for network/server failures (not for frontend or 422 validation errors)
    if (!response || (response.status !== 422 && response.status !== 400)) {
      await showErrorAlert(t('unable_to_save_expense'), t('something_went_wrong'))
    }
  } finally {
    isSubmitting.value = false
  }
}

onMounted(loadCategories)
</script>
