# Smart Receipt Project — Step 22: Manual Expense Create and Edit UI

## Goal

Build Vue frontend pages for creating and editing manual expenses.

Create routes:

```text
/expenses/new
/expenses/:id/edit
```

Connect to these backend endpoints:

```text
GET  /api/categories
POST /api/expenses
GET  /api/expenses/{expense_id}
PUT  /api/expenses/{expense_id}
```

Expected flows:

```text
Expenses
→ Add Expense
→ Fill form
→ Save
→ Open expense detail
```

```text
Expense Detail
→ Edit
→ Update fields and items
→ Save
→ Return to expense detail
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain.

Use clear names and straightforward logic.

Avoid unnecessary abstractions, complex form frameworks, generic CRUD builders, and overengineering.

---

## Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list and detail pages
- Expense API read functions
- English/Thai fixed frontend labels
- 48 frontend tests passing
- Clean production build
- Complete FastAPI backend

Inspect the existing frontend and backend schemas before changing anything.

Do not rebuild authentication or expense read pages.

Do not change backend code unless a real frontend/backend mismatch is found.

---

# Scope

Implement only:

```text
Category types and API
Expense create/update request types
Reusable expense form component or simple shared form logic
Create expense page
Edit expense page
Nested expense-item form rows
Frontend validation
Backend validation display
Navigation changes
English/Thai fixed labels
Focused tests
Production build verification
```

Do not implement:

```text
Delete button
Receipt upload
Gemini extraction UI
AI confirmation UI
Dynamic translation button
Excel export button
Search
Filters
Pagination
Dashboard statistics
```

---

# Important Coding Style

1. Write simple, human-readable Vue and TypeScript code.
2. Make the code easy for a student to understand and explain.
3. Use clear interfaces and form state.
4. Keep API calls inside `src/api`.
5. Reuse one form component only if it clearly reduces duplication.
6. Avoid generic form engines.
7. Avoid complex validation libraries.
8. Avoid unnecessary composables.
9. Avoid service classes and repository classes.
10. Do not add a new UI framework.
11. Reuse the current CSS style.
12. Match backend schemas exactly.

---

# 1. Inspect Real Backend Schemas

Before coding, inspect the actual request schemas for:

```text
ExpenseCreate
ExpenseUpdate
ExpenseItemCreate
```

Also inspect:

```text
Category response schema
```

Match:

```text
field names
required fields
optional fields
nullability
Decimal serialization
date format
```

Do not invent unsupported fields.

---

# 2. Category Types and API

Create or update:

```text
frontend/src/types/category.ts
frontend/src/api/categoryApi.ts
```

Add simple types matching the backend.

Possible category fields:

```text
id
code
name_en
name_th
description
is_active
```

Use only real response fields.

Add:

```ts
getCategories()
```

Connect to:

```text
GET /api/categories
```

Use the existing Axios client.

Do not duplicate token logic.

---

# 3. Expense Request Types

Update:

```text
frontend/src/types/expense.ts
```

Add request interfaces matching the backend.

Suggested structure:

```ts
export interface ExpenseItemFormData {
  category_id: number | null
  original_name: string
  name_en: string
  name_th: string
  quantity: string
  unit: string
  unit_price: string
  discount_amount: string
  total_price: string
}

export interface ExpenseFormData {
  category_id: number | null
  title: string
  merchant_name: string
  receipt_number: string
  receipt_date: string
  document_type: string
  payment_method: string
  currency: string
  subtotal: string
  tax_amount: string
  discount_amount: string
  total_amount: string
  notes: string
  items: ExpenseItemFormData[]
}
```

Adjust fields to the real backend schemas.

Do not use `any`.

Do not include backend-controlled fields such as:

```text
id
user_id
input_method
ai_status
ai_confidence
is_confirmed
created_at
updated_at
deleted_at
```

---

# 4. Expense API Functions

Update:

```text
frontend/src/api/expenseApi.ts
```

Add:

```ts
createExpense(data)
updateExpense(expenseId, data)
```

Connect to:

```text
POST /api/expenses
PUT  /api/expenses/{expense_id}
```

Return typed `Expense` responses.

Do not navigate inside the API module.

Do not duplicate authentication headers.

---

# 5. Routes

Add protected routes:

```text
/expenses/new
/expenses/:id/edit
```

Suggested names:

```text
expense-create
expense-edit
```

Use:

```ts
meta: { requiresAuth: true }
```

Important route order:

```text
/expenses/new
```

must be registered before:

```text
/expenses/:id
```

so `new` is not treated as an expense ID.

Add a route test for this.

---

# 6. Shared Form Design

Use one simple shared form component if it reduces duplication:

```text
frontend/src/components/ExpenseForm.vue
```

The component may receive:

```text
initialData
categories
isSubmitting
submitLabel
```

and emit:

```text
submit
cancel
```

A shared component is preferred because create and edit use nearly the same fields.

Keep it straightforward.

Do not create a generic form generator.

---

# 7. Create Expense Page

Create:

```text
frontend/src/views/ExpenseCreateView.vue
```

On mount:

```text
Load categories
```

Initial form:

```text
Empty simple fields
Default currency may be THB if that matches the project requirement
items = []
```

Submit flow:

```text
1. Validate form
2. Convert empty optional strings to null or omit them
3. Convert category IDs to numbers
4. Send POST /api/expenses
5. Redirect to /expenses/{created.id}
```

Show:

```text
loading categories
submitting
validation errors
backend error
```

Do not create fake default expense data.

---

# 8. Edit Expense Page

Create:

```text
frontend/src/views/ExpenseEditView.vue
```

On mount:

```text
1. Validate route ID
2. Load categories
3. Load expense
4. Convert response into editable form data
```

Submit to:

```text
PUT /api/expenses/{expense_id}
```

After success:

```text
Redirect to /expenses/{expense_id}
```

Handle:

```text
loading
404
invalid ID
backend error
```

---

# 9. Important Item-Replacement Behavior

The backend update behavior is:

```text
items omitted
→ current items stay unchanged

items included
→ all active items are replaced
```

For this frontend edit page, always send the complete current item list.

This makes behavior predictable:

```text
Displayed items
→ user edits them
→ frontend sends all items
→ backend replaces old active items
```

Do not send only the changed item.

Do not create standalone item API calls.

---

# 10. Main Expense Fields

Include only fields supported by the backend.

Expected fields may include:

```text
Category
Title
Merchant Name
Receipt Number
Receipt Date
Document Type
Payment Method
Currency
Subtotal
Tax Amount
Discount Amount
Total Amount
Notes
```

If `receipt_time` is not supported by the current response/request schema, do not add it.

Use appropriate HTML inputs:

```text
date input
number/text inputs for decimal values
textarea for notes
select for category
```

Use text inputs for Decimal values if it avoids JavaScript floating-point issues.

---

# 11. Category Select

Load active categories from:

```text
GET /api/categories
```

Display according to selected frontend language:

```text
English locale → name_en
Thai locale → name_th
```

Fallback:

```text
name_en
name_th
code
Category #id
```

Send only:

```text
category_id
```

Manual expense category is required.

Do not create categories in the frontend.

---

# 12. Currency

Use a simple currency field.

Options may include:

```text
THB
USD
```

Use the actual backend rules.

Default to:

```text
THB
```

only if appropriate for this project.

Do not build currency conversion.

---

# 13. Expense Items Form

Allow:

```text
Add Item
Remove Item
```

Each item row should support fields available in the backend:

```text
Category
Original Name
English Name
Thai Name
Quantity
Unit
Unit Price
Discount Amount
Total Price
```

Use a simple array in form state.

New item template:

```text
category_id = null
original_name = ""
name_en = ""
name_th = ""
quantity = ""
unit = ""
unit_price = ""
discount_amount = ""
total_price = ""
```

Do not auto-calculate values unless the requirement is clear.

A small helper may calculate total only if it is transparent and does not overwrite user input unexpectedly.

---

# 14. Item Name Rules

At least one item name should be provided when an item exists:

```text
original_name
name_en
or name_th
```

Show a frontend validation message when all are empty.

Do not require items for every expense.

An expense with:

```text
items = []
```

is valid if the backend allows it.

---

# 15. Frontend Validation

Validate before submit.

Main expense:

```text
Category is required
Title is required
Currency is required
Total amount is required
Total amount must be zero or greater
Subtotal cannot be negative
Tax cannot be negative
Discount cannot be negative
```

For each item:

```text
At least one name is required
Quantity cannot be negative
Unit price cannot be negative
Discount cannot be negative
Total price cannot be negative
```

Use string-based decimal checks.

Avoid JavaScript floating-point calculations.

Do not create a complex validation framework.

---

# 16. Request Cleaning

Before sending:

```text
Trim strings
Convert empty optional strings to null or omit them
Convert category IDs to numbers
Keep decimal values as strings
Keep date in YYYY-MM-DD
```

Do not send invalid empty strings for numeric fields if the backend expects null.

Create one small request-building helper if useful.

Keep it inside the form or a small utility file.

---

# 17. Backend Error Display

Handle FastAPI errors safely.

Possible formats:

```text
detail: "message"
detail: [{ loc, msg, type }]
```

Display readable messages.

For field validation errors:

```text
Show a general form error
Optionally map simple field errors
```

Do not display raw JSON or stack traces.

Handle:

```text
401 → existing auth handling
404 on edit → expense not found
422 → validation error
500/network → unable to save
```

---

# 18. Navigation Changes

Update existing **Add Expense** button on the list page to link to:

```text
/expenses/new
```

Add an **Edit Expense** button on the detail page:

```text
/expenses/{id}/edit
```

Add:

```text
Cancel
```

behavior:

```text
Create cancel → /expenses
Edit cancel → /expenses/{id}
```

---

# 19. English and Thai UI Labels

Update:

```text
src/locales/en.json
src/locales/th.json
```

Add labels for:

```text
Create Expense
Edit Expense
Save Expense
Update Expense
Cancel
Category Required
Title Required
Currency Required
Total Required
Invalid Amount
Add Item
Remove Item
Item
Merchant Name
Receipt Number
Receipt Date
Document Type
Payment Method
Subtotal
Tax Amount
Discount Amount
Total Amount
Notes
Original Name
English Name
Thai Name
Quantity
Unit
Unit Price
Total Price
Loading Categories
Loading Expense
Saving
Expense Created
Expense Updated
Unable to Save Expense
Validation Error
Select Category
No Items Added
```

Use Vue I18n only for fixed UI labels.

Do not call Gemini translation.

---

# 20. Styling

Use existing CSS.

Add simple styles for:

```text
Form sections
Two-column desktop layout
Single-column mobile layout
Item cards or rows
Validation errors
Submit/cancel actions
Loading state
```

Do not add a new CSS framework.

Keep the form readable and responsive.

---

# 21. Tests

Add focused frontend tests.

Suggested files:

```text
src/views/expense.create.test.ts
src/views/expense.edit.test.ts
src/components/expense.form.test.ts
src/api/expense.write.test.ts
```

Test at least:

1. Category API calls `/categories`.
2. Create API calls `POST /expenses`.
3. Update API calls `PUT /expenses/{id}`.
4. `/expenses/new` is not treated as `:id`.
5. Create page loads categories.
6. Create page displays form.
7. Required category validation.
8. Required title validation.
9. Required total validation.
10. Negative main amount validation.
11. Add item.
12. Remove item.
13. Item requires one name.
14. Negative item amount validation.
15. Create submit sends cleaned request.
16. Create success redirects to detail.
17. Edit page loads existing expense.
18. Edit page fills fields.
19. Edit page includes all current items.
20. Edit submit sends complete item list.
21. Edit success redirects to detail.
22. Edit 404 is handled.
23. Backend 422 error is shown safely.
24. English/Thai labels switch.
25. Existing 48 tests remain green.

Mock all API calls.

Do not require the real backend in unit tests.

---

# 22. Manual Verification

Run backend:

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

Run frontend:

```bash
cd frontend
npm run dev
```

Manually test:

```text
Login
Open Expenses
Click Add Expense
Load categories
Create expense without items
Create expense with items
Open created detail
Click Edit
Change expense fields
Add/remove/edit items
Save
Confirm detail reflects changes
Switch English/Thai
Cancel create/edit
Refresh edit page
```

---

# 23. Build Verification

Run:

```bash
npm run test
npm run build
```

The TypeScript build must finish with zero errors.

---

# Do Not Implement Yet

Do not implement:

- Expense delete button
- Delete confirmation dialog
- Receipt upload
- Gemini extraction UI
- AI confirmation button
- Dynamic translation button
- Excel export button
- Search
- Filters
- Pagination
- Dashboard statistics

---

# Expected Result

After this step:

- Manual expense creation page
- Expense editing page
- Category loading
- Dynamic item rows
- Frontend validation
- Safe request cleaning
- Backend validation display
- Add/Edit navigation
- English/Thai fixed labels
- Focused tests
- Clean production build

---

# Required Completion Report

Provide:

1. Changed and created files
2. Category API and types
3. Expense create/update types
4. API functions added
5. Routes added
6. Shared form design
7. Create behavior
8. Edit behavior
9. Item replacement behavior
10. Validation behavior
11. Request cleaning behavior
12. Error handling
13. English/Thai changes
14. Tests and result
15. Build result
16. Manual verification result
17. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
