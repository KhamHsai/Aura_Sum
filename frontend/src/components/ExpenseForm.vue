<template>
  <form @submit.prevent="handleSubmit" novalidate>

    <!-- Global backend error -->
    <div v-if="backendError" class="alert alert-error" style="margin-bottom:1.5rem;">
      {{ backendError }}
    </div>

    <!-- ── Main expense fields ─────────────────────────────────────── -->
    <div class="detail-card">
      <h2>{{ t('expense_details') }}</h2>

      <div class="form-grid">

        <!-- Category (required) -->
        <div class="form-group">
          <label for="ef-category">{{ t('category') }} *</label>
          <select
            id="ef-category"
            v-model="form.category_id"
            :class="{ 'input-error': errors.category_id }"
          >
            <option :value="null" disabled>{{ t('select_category') }}</option>
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ locale === 'th' ? (cat.name_th || cat.name_en) : (cat.name_en || cat.name_th) }}
            </option>
          </select>
          <p v-if="errors.category_id" class="field-error">{{ errors.category_id }}</p>
          <p v-if="categories.length === 0 && !loadingCategories" class="field-error">
            {{ t('loading_categories') }}
          </p>
        </div>

        <!-- Title (required) -->
        <div class="form-group">
          <label for="ef-title">{{ t('title') }} *</label>
          <input
            id="ef-title"
            v-model="form.title"
            type="text"
            :class="{ 'input-error': errors.title }"
            :placeholder="t('title')"
          />
          <p v-if="errors.title" class="field-error">{{ errors.title }}</p>
        </div>

        <!-- Merchant Name -->
        <div class="form-group">
          <label for="ef-merchant">{{ t('merchant') }}</label>
          <input
            id="ef-merchant"
            v-model="form.merchant_name"
            type="text"
            :placeholder="t('merchant')"
          />
        </div>

        <!-- Receipt Number -->
        <div class="form-group">
          <label for="ef-receipt-number">{{ t('receipt_number') }}</label>
          <input
            id="ef-receipt-number"
            v-model="form.receipt_number"
            type="text"
            :placeholder="t('receipt_number')"
          />
        </div>

        <!-- Receipt Date -->
        <div class="form-group">
          <label for="ef-receipt-date">{{ t('receipt_date') }}</label>
          <input
            id="ef-receipt-date"
            v-model="form.receipt_date"
            type="date"
          />
        </div>

        <!-- Payment Method -->
        <div class="form-group">
          <label for="ef-payment">{{ t('payment_method') }}</label>
          <input
            id="ef-payment"
            v-model="form.payment_method"
            type="text"
            :placeholder="t('payment_method')"
          />
        </div>

        <!-- Currency (required) -->
        <div class="form-group">
          <label for="ef-currency">{{ t('currency') }} *</label>
          <select
            id="ef-currency"
            v-model="form.currency"
            :class="{ 'input-error': errors.currency }"
          >
            <option value="THB">THB</option>
            <option value="USD">USD</option>
          </select>
          <p v-if="errors.currency" class="field-error">{{ errors.currency }}</p>
        </div>

        <!-- Subtotal -->
        <div class="form-group">
          <label for="ef-subtotal">{{ t('subtotal') }}</label>
          <input
            id="ef-subtotal"
            v-model="form.subtotal"
            type="text"
            inputmode="decimal"
            :class="{ 'input-error': errors.subtotal }"
            placeholder="0.00"
          />
          <p v-if="errors.subtotal" class="field-error">{{ errors.subtotal }}</p>
        </div>

        <!-- Tax Amount -->
        <div class="form-group">
          <label for="ef-tax">{{ t('tax') }}</label>
          <input
            id="ef-tax"
            v-model="form.tax_amount"
            type="text"
            inputmode="decimal"
            :class="{ 'input-error': errors.tax_amount }"
            placeholder="0.00"
          />
          <p v-if="errors.tax_amount" class="field-error">{{ errors.tax_amount }}</p>
        </div>

        <!-- Discount Amount -->
        <div class="form-group">
          <label for="ef-discount">{{ t('discount') }}</label>
          <input
            id="ef-discount"
            v-model="form.discount_amount"
            type="text"
            inputmode="decimal"
            :class="{ 'input-error': errors.discount_amount }"
            placeholder="0.00"
          />
          <p v-if="errors.discount_amount" class="field-error">{{ errors.discount_amount }}</p>
        </div>

        <!-- Total Amount (required) -->
        <div class="form-group">
          <label for="ef-total">{{ t('total') }} *</label>
          <input
            id="ef-total"
            v-model="form.total_amount"
            type="text"
            inputmode="decimal"
            :class="{ 'input-error': errors.total_amount }"
            placeholder="0.00"
          />
          <p v-if="errors.total_amount" class="field-error">{{ errors.total_amount }}</p>
        </div>

      </div>

      <!-- Notes (full width) -->
      <div class="form-group" style="margin-top:0.5rem;">
        <label for="ef-notes">{{ t('notes') }}</label>
        <textarea
          id="ef-notes"
          v-model="form.notes"
          rows="3"
          :placeholder="t('notes')"
          class="form-textarea"
        />
      </div>
    </div>

    <!-- ── Expense items ───────────────────────────────────────────── -->
    <div class="detail-card">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1.25rem;">
        <h2 style="margin:0;">{{ t('expense_items') }}</h2>
        <button type="button" class="btn btn-secondary" style="width:auto;" @click="addItem">
          + {{ t('add_item') }}
        </button>
      </div>

      <p v-if="form.items.length === 0" class="state-container" style="padding:1rem 0; text-align:center; color:#888;">
        {{ t('no_items_added') }}
      </p>

      <!-- Item rows -->
      <div
        v-for="(item, index) in form.items"
        :key="index"
        class="item-row"
      >
        <div class="item-row-header">
          <span class="item-row-label">{{ t('item') }} {{ index + 1 }}</span>
          <button type="button" class="btn-remove-item" @click="removeItem(index)">
            {{ t('remove_item') }}
          </button>
        </div>

        <!-- Item name error -->
        <p v-if="itemErrors[index]?.name" class="field-error" style="margin-bottom:0.5rem;">
          {{ itemErrors[index].name }}
        </p>

        <div class="form-grid">

          <!-- Item Category -->
          <div class="form-group">
            <label>{{ t('category') }}</label>
            <select v-model="item.category_id">
              <option :value="null">{{ t('uncategorized') }}</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ locale === 'th' ? (cat.name_th || cat.name_en) : (cat.name_en || cat.name_th) }}
              </option>
            </select>
          </div>

          <!-- Original Name -->
          <div class="form-group">
            <label>{{ t('original_name') }}</label>
            <input
              v-model="item.original_name"
              type="text"
              :placeholder="t('original_name')"
            />
          </div>

          <!-- English Name -->
          <div class="form-group">
            <label>{{ t('name_en') }}</label>
            <input
              v-model="item.name_en"
              type="text"
              :placeholder="t('name_en')"
            />
          </div>

          <!-- Thai Name -->
          <div class="form-group">
            <label>{{ t('name_th') }}</label>
            <input
              v-model="item.name_th"
              type="text"
              :placeholder="t('name_th')"
            />
          </div>

          <!-- Quantity -->
          <div class="form-group">
            <label>{{ t('quantity') }}</label>
            <input
              v-model="item.quantity"
              type="text"
              inputmode="decimal"
              :class="{ 'input-error': itemErrors[index]?.quantity }"
              placeholder="1"
            />
            <p v-if="itemErrors[index]?.quantity" class="field-error">{{ itemErrors[index].quantity }}</p>
          </div>

          <!-- Unit -->
          <div class="form-group">
            <label>{{ t('unit') }}</label>
            <input
              v-model="item.unit"
              type="text"
              :placeholder="t('unit')"
            />
          </div>

          <!-- Unit Price -->
          <div class="form-group">
            <label>{{ t('unit_price') }}</label>
            <input
              v-model="item.unit_price"
              type="text"
              inputmode="decimal"
              :class="{ 'input-error': itemErrors[index]?.unit_price }"
              placeholder="0.00"
            />
            <p v-if="itemErrors[index]?.unit_price" class="field-error">{{ itemErrors[index].unit_price }}</p>
          </div>

          <!-- Discount -->
          <div class="form-group">
            <label>{{ t('discount') }}</label>
            <input
              v-model="item.discount_amount"
              type="text"
              inputmode="decimal"
              :class="{ 'input-error': itemErrors[index]?.discount_amount }"
              placeholder="0.00"
            />
            <p v-if="itemErrors[index]?.discount_amount" class="field-error">{{ itemErrors[index].discount_amount }}</p>
          </div>

          <!-- Total Price -->
          <div class="form-group">
            <label>{{ t('total_price') }}</label>
            <input
              v-model="item.total_price"
              type="text"
              inputmode="decimal"
              :class="{ 'input-error': itemErrors[index]?.total_price }"
              placeholder="0.00"
            />
            <p v-if="itemErrors[index]?.total_price" class="field-error">{{ itemErrors[index].total_price }}</p>
          </div>

        </div>
      </div>
    </div>

    <!-- ── Actions ────────────────────────────────────────────────── -->
    <div class="form-actions">
      <button
        type="button"
        class="btn btn-secondary"
        style="width:auto;"
        @click="emit('cancel')"
      >
        {{ t('cancel') }}
      </button>
      <button
        type="submit"
        class="btn btn-primary"
        style="width:auto;"
        :disabled="isSubmitting"
      >
        {{ isSubmitting ? t('saving') : submitLabel }}
      </button>
    </div>

  </form>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Category } from '../types/category'
import type { ExpenseFormData, ExpenseItemFormData } from '../types/expense'

// ── Props and emits ───────────────────────────────────────────────────────────

interface Props {
  initialData: ExpenseFormData
  categories: Category[]
  loadingCategories: boolean
  isSubmitting: boolean
  submitLabel: string
  backendError: string | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'submit', data: ExpenseFormData): void
  (e: 'cancel'): void
}>()

const { t, locale } = useI18n()

// ── Local form state — a deep copy so we don't mutate the parent's object ─────

const form = reactive<ExpenseFormData>(deepCopy(props.initialData))

// When the parent replaces initialData (e.g. after loading the expense on edit),
// reset the local form to the new values.
watch(
  () => props.initialData,
  (newData) => {
    Object.assign(form, deepCopy(newData))
  },
  { deep: true },
)

function deepCopy(data: ExpenseFormData): ExpenseFormData {
  return {
    ...data,
    items: data.items.map((item) => ({ ...item })),
  }
}

// ── Validation errors ─────────────────────────────────────────────────────────

interface FormErrors {
  category_id?: string
  title?: string
  currency?: string
  subtotal?: string
  tax_amount?: string
  discount_amount?: string
  total_amount?: string
}

interface ItemErrors {
  name?: string
  quantity?: string
  unit_price?: string
  discount_amount?: string
  total_price?: string
}

const errors = reactive<FormErrors>({})
const itemErrors = reactive<ItemErrors[]>([])

// ── Decimal helpers ───────────────────────────────────────────────────────────

// Returns true if the string is a valid non-negative decimal (or empty).
function isNonNegativeDecimal(value: string): boolean {
  const trimmed = value.trim()
  if (trimmed === '') return true
  return /^\d+(\.\d+)?$/.test(trimmed) && parseFloat(trimmed) >= 0
}

// Returns true if the string is a valid positive decimal (> 0).
function isPositiveDecimal(value: string): boolean {
  const trimmed = value.trim()
  if (trimmed === '') return false
  return /^\d+(\.\d+)?$/.test(trimmed) && parseFloat(trimmed) > 0
}

// ── Validate ──────────────────────────────────────────────────────────────────

function validate(): boolean {
  // Clear previous errors
  Object.keys(errors).forEach((k) => delete (errors as Record<string, unknown>)[k])
  itemErrors.splice(0, itemErrors.length)

  let valid = true

  // Main fields
  if (!form.category_id) {
    errors.category_id = t('category_required')
    valid = false
  }

  if (!form.title.trim()) {
    errors.title = t('title_required')
    valid = false
  }

  if (!form.currency.trim()) {
    errors.currency = t('currency_required')
    valid = false
  }

  if (!form.total_amount.trim()) {
    errors.total_amount = t('total_required')
    valid = false
  } else if (!isNonNegativeDecimal(form.total_amount)) {
    errors.total_amount = t('invalid_amount')
    valid = false
  }

  if (form.subtotal.trim() && !isNonNegativeDecimal(form.subtotal)) {
    errors.subtotal = t('invalid_amount')
    valid = false
  }

  if (form.tax_amount.trim() && !isNonNegativeDecimal(form.tax_amount)) {
    errors.tax_amount = t('invalid_amount')
    valid = false
  }

  if (form.discount_amount.trim() && !isNonNegativeDecimal(form.discount_amount)) {
    errors.discount_amount = t('invalid_amount')
    valid = false
  }

  // Item fields
  for (let i = 0; i < form.items.length; i++) {
    const item = form.items[i]
    const itemErr: ItemErrors = {}
    let itemValid = true

    // At least one name required
    const hasName =
      item.original_name.trim() || item.name_en.trim() || item.name_th.trim()
    if (!hasName) {
      itemErr.name = t('item_name_required')
      itemValid = false
    }

    // Quantity must be a positive number
    if (!isPositiveDecimal(item.quantity)) {
      itemErr.quantity = t('invalid_amount')
      itemValid = false
    }

    if (item.unit_price.trim() && !isNonNegativeDecimal(item.unit_price)) {
      itemErr.unit_price = t('invalid_amount')
      itemValid = false
    }

    if (item.discount_amount.trim() && !isNonNegativeDecimal(item.discount_amount)) {
      itemErr.discount_amount = t('invalid_amount')
      itemValid = false
    }

    if (item.total_price.trim() && !isNonNegativeDecimal(item.total_price)) {
      itemErr.total_price = t('invalid_amount')
      itemValid = false
    }

    itemErrors.push(itemErr)
    if (!itemValid) valid = false
  }

  return valid
}

// ── Item management ───────────────────────────────────────────────────────────

function makeEmptyItem(): ExpenseItemFormData {
  return {
    category_id: null,
    original_name: '',
    name_en: '',
    name_th: '',
    quantity: '',
    unit: '',
    unit_price: '',
    discount_amount: '',
    total_price: '',
  }
}

function addItem(): void {
  form.items.push(makeEmptyItem())
}

function removeItem(index: number): void {
  form.items.splice(index, 1)
  itemErrors.splice(index, 1)
}

// ── Submit ────────────────────────────────────────────────────────────────────

function handleSubmit(): void {
  if (!validate()) return
  // Emit a plain copy — the parent builds the actual API request
  emit('submit', deepCopy(form))
}
</script>
