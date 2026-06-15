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

        <!-- Category (manual text entry with autocomplete suggestions) -->
        <div class="form-group">
          <label for="ef-category">{{ t('category') }}</label>
          <input
            id="ef-category"
            v-model="form.category_name"
            type="text"
            :placeholder="t('category_placeholder')"
            list="ef-category-suggestions"
            autocomplete="off"
          />
          <datalist id="ef-category-suggestions">
            <option v-for="cat in categories" :key="cat.id"
              :value="locale === 'th' ? (cat.name_th || cat.name_en) : (cat.name_en || cat.name_th)" />
          </datalist>
        </div>

        <!-- Paid To (optional, shown always) -->
        <div class="form-group">
          <label for="ef-paid-to">{{ t('paid_to') }}</label>
          <input
            id="ef-paid-to"
            v-model="form.paid_to"
            type="text"
            :placeholder="t('paid_to')"
          />
        </div>

        <!-- Tax ID — only show if AI filled it or user is editing -->
        <div v-if="form.tax_id || alwaysShowOptional" class="form-group">
          <label for="ef-tax-id">{{ t('tax_id') }}</label>
          <input
            id="ef-tax-id"
            v-model="form.tax_id"
            type="text"
            :placeholder="t('tax_id')"
          />
        </div>

        <!-- Receipt Date (required) -->
        <div class="form-group">
          <label for="ef-receipt-date">{{ t('receipt_date') }} *</label>
          <input
            id="ef-receipt-date"
            v-model="form.receipt_date"
            type="date"
            :class="{ 'input-error': errors.receipt_date }"
          />
          <p v-if="errors.receipt_date" class="field-error">{{ errors.receipt_date }}</p>
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

        <!-- Subtotal — only show if AI filled it or user is editing -->
        <div v-if="form.subtotal || alwaysShowOptional" class="form-group">
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

        <!-- Tax Amount — only show if AI filled it or user is editing -->
        <div v-if="form.tax_amount || alwaysShowOptional" class="form-group">
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

        <!-- Discount — only show if AI filled it or user is editing -->
        <div v-if="form.discount_amount || alwaysShowOptional" class="form-group">
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

      <!-- Notes (full width, always shown) -->
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

      <!-- Show more fields toggle (when optional fields are hidden) -->
      <div v-if="!alwaysShowOptional" style="margin-top:0.75rem;">
        <button type="button" class="btn-text-link" @click="alwaysShowOptional = true">
          + {{ t('show_more_fields') }}
        </button>
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

      <div v-for="(item, index) in form.items" :key="index" class="item-row">
        <div class="item-row-header">
          <span class="item-row-label">{{ t('item') }} {{ index + 1 }}</span>
          <button type="button" class="btn-remove-item" @click="removeItem(index)">
            {{ t('remove_item') }}
          </button>
        </div>

        <div class="form-grid">

          <!-- Item name: shows name in current UI language, falls back to original_name -->
          <div class="form-group">
            <label>{{ t('item_name') }}</label>
            <input
              v-model="item.display_name"
              type="text"
              :placeholder="t('item_name')"
            />
            <p v-if="itemErrors[index]?.name" class="field-error">{{ itemErrors[index].name }}</p>
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

          <!-- Unit (hide if empty) -->
          <div v-if="item.unit || alwaysShowOptional" class="form-group">
            <label>{{ t('unit') }}</label>
            <input v-model="item.unit" type="text" :placeholder="t('unit')" />
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

          <!-- Discount (hide if empty) -->
          <div v-if="item.discount_amount || alwaysShowOptional" class="form-group">
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
    <div class="form-actions" style="margin-top: 2rem; gap: 1.25rem;">
      <button type="button" class="btn btn-secondary" style="width:auto; padding: 0.85rem 1.5rem;" @click="emit('cancel')">
        {{ t('cancel') }}
      </button>
      <div style="flex: 1;"></div>
      <button type="submit" class="btn btn-secondary" style="width:auto; padding: 0.85rem 1.5rem; background: rgba(93, 63, 211, 0.05);" :disabled="isSubmitting">
        {{ isSubmitting ? t('saving') : submitLabel }}
      </button>
      <slot name="extra-actions"></slot>
    </div>

  </form>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Category } from '../types/category'
import type { ExpenseFormData, ExpenseItemFormData } from '../types/expense'

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

// Show extra optional fields (toggled by "show more" link)
const alwaysShowOptional = ref(false)

const form = reactive<ExpenseFormData>(deepCopy(props.initialData))

// ── Live-language item name logic ─────────────────────────────────────────────
// Each item has name_th (original Thai), name_en (English translation, may be empty),
// and original_name (raw text from receipt).
//
// display_name is the visible input:
//   - locale=th  → show name_th  (the original, never overwrite)
//   - locale=en  → show name_en if we have it, else show original_name as placeholder
//
// Cache rules:
//   - name_th is the source of truth for Thai receipts — never overwrite it on locale switch
//   - name_en is the English translation cache — only write to it when locale=en and user edits
//   - Switching locale back to TH always restores the cached name_th

// Flag to suppress the watch callback during programmatic locale-switch syncs
let _syncingLocale = false

function getDisplayName(item: ExpenseItemFormData): string {
  if (locale.value === 'th') {
    return item.name_th || item.original_name || item.name_en
  }
  // EN: if we have a cached English name use it, otherwise show the original (Thai) as fallback
  return item.name_en || item.original_name || item.name_th
}

function syncDisplayNames(): void {
  _syncingLocale = true
  for (const item of form.items) {
    item.display_name = getDisplayName(item)
  }
  // Allow the watch to settle before clearing the flag
  setTimeout(() => { _syncingLocale = false }, 0)
}

// When locale changes, refresh display_name from cache — no AI call, no data loss
watch(() => locale.value, () => syncDisplayNames())

// When display_name is edited by the user, write back to the correct language slot
watch(
  () => form.items.map(i => i.display_name),
  (newNames, oldNames) => {
    if (_syncingLocale) return  // ignore programmatic syncs
    for (let i = 0; i < form.items.length; i++) {
      const item = form.items[i]
      const newName = newNames[i] ?? ''
      const oldName = oldNames?.[i] ?? ''
      if (newName === oldName) continue  // nothing changed for this item

      if (locale.value === 'th') {
        // User editing in Thai — update Thai cache and original
        item.name_th = newName
        if (!item.original_name) item.original_name = newName
      } else {
        // User editing in English — only update English cache
        item.name_en = newName
        if (!item.original_name) item.original_name = newName
      }
    }
  },
)

watch(
  () => props.initialData,
  (newData) => {
    Object.assign(form, deepCopy(newData))
    syncDisplayNames()
    // If AI filled optional fields, show them automatically
    if (newData.tax_id || newData.subtotal || newData.tax_amount ||
        newData.discount_amount || newData.category_name) {
      alwaysShowOptional.value = true
    }
  },
  { deep: true },
)

function deepCopy(data: ExpenseFormData): ExpenseFormData {
  const copy = {
    ...data,
    items: data.items.map((item) => ({
      ...item,
      // Set display_name based on current locale — TH receipts show name_th by default
      display_name: locale.value === 'th'
        ? (item.name_th || item.original_name || item.name_en)
        : (item.name_en || item.original_name || item.name_th),
    })),
  }
  return copy
}

// ── Validation ────────────────────────────────────────────────────────────────

interface FormErrors {
  receipt_date?: string
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

function isNonNegativeDecimal(value: string): boolean {
  const trimmed = value.trim()
  if (trimmed === '') return true
  return /^\d+(\.\d+)?$/.test(trimmed) && parseFloat(trimmed) >= 0
}

function isPositiveDecimal(value: string): boolean {
  const trimmed = value.trim()
  if (trimmed === '') return false
  return /^\d+(\.\d+)?$/.test(trimmed) && parseFloat(trimmed) > 0
}

function validate(): boolean {
  Object.keys(errors).forEach((k) => delete (errors as Record<string, unknown>)[k])
  itemErrors.splice(0, itemErrors.length)

  let valid = true

  if (!form.receipt_date) {
    errors.receipt_date = t('error_required')
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

  for (let i = 0; i < form.items.length; i++) {
    const item = form.items[i]
    const itemErr: ItemErrors = {}
    let itemValid = true

    // display_name is the visible field; also check underlying name fields
    const hasName = (item.display_name || '').trim() ||
      item.original_name.trim() || item.name_en.trim() || item.name_th.trim()
    if (!hasName) {
      itemErr.name = t('item_name_required')
      itemValid = false
    }

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

// ── Items ─────────────────────────────────────────────────────────────────────

function makeEmptyItem(): ExpenseItemFormData {
  return {
    category_id: null,
    original_name: '',
    name_en: '',
    name_th: '',
    display_name: '',
    quantity: '',
    unit: '',
    unit_price: '',
    discount_amount: '',
    total_price: '',
  }
}

function addItem(): void { form.items.push(makeEmptyItem()) }
function removeItem(index: number): void {
  form.items.splice(index, 1)
  itemErrors.splice(index, 1)
}

// ── Submit ────────────────────────────────────────────────────────────────────

function handleSubmit(): void {
  if (!validate()) return
  emit('submit', deepCopy(form))
}

defineExpose({ submitForm: handleSubmit })
</script>

<style scoped>
.btn-text-link {
  background: none;
  border: none;
  color: #4a6cf7;
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}
.btn-text-link:hover { color: #2a4cd7; }
</style>
