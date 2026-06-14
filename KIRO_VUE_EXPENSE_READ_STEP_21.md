# Smart Receipt Project — Step 21: Expense List and Detail UI

## Goal

Build protected Vue pages for:

```text
/expenses
/expenses/:id
```

Connect them to:

```text
GET /api/expenses
GET /api/expenses/{expense_id}
```

Expected flow:

```text
Login
→ Open Expenses
→ View expense list
→ Open one expense
→ View full details and nested items
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain. Use clear names and straightforward logic. Avoid unnecessary abstractions, complex patterns, generic UI frameworks, and overengineering.

## Current Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Login, registration, protected dashboard, logout
- Token persistence and current-user loading
- English/Thai fixed frontend labels
- 25 frontend tests passing
- Clean frontend production build
- Complete FastAPI backend

Inspect the existing frontend first. Reuse current authentication, router, Axios client, layout, styles, and test setup.

Do not rebuild authentication.

Do not change backend code unless a real integration mismatch is found.

## Scope

Implement only:

- Expense TypeScript types
- Expense API functions
- Expense list page
- Expense detail page
- Nested item display
- Loading, empty, error, and not-found states
- Navigation update
- English/Thai fixed labels
- Focused frontend tests
- Production build verification

Do not implement:

- Create, edit, or delete expense UI
- Receipt upload
- Gemini extraction UI
- Confirmation UI
- Dynamic translation button
- Excel export button
- Search, filters, pagination, or dashboard statistics

## 1. Inspect Real Backend Responses

Inspect Swagger or backend schemas for:

```text
GET /api/expenses
GET /api/expenses/{expense_id}
```

Match field names and nullability exactly.

Do not invent response fields.

## 2. Expense Types

Create:

```text
frontend/src/types/expense.ts
```

Add simple interfaces for `Expense` and `ExpenseItem`.

Expected fields may include:

```text
Expense:
id
category_id
title
merchant_name
receipt_number
receipt_date
receipt_time
document_type
payment_method
currency
subtotal
tax_amount
discount_amount
total_amount
notes
input_method
language_detected
ai_confidence
ai_status
is_confirmed
created_at
updated_at
items

ExpenseItem:
id
expense_id
category_id
original_name
name_en
name_th
quantity
unit
unit_price
discount_amount
total_price
created_at
updated_at
```

Use only real backend fields.

Do not use `any`.

## 3. Expense API Module

Create:

```text
frontend/src/api/expenseApi.ts
```

Add:

```ts
getExpenses(): Promise<Expense[]>
getExpenseById(expenseId: number): Promise<Expense>
```

Use the existing Axios client.

Do not duplicate token logic.

Do not navigate inside the API module.

## 4. Routes

Add protected routes:

```text
/expenses
/expenses/:id
```

Suggested names:

```text
expenses
expense-detail
```

Use:

```ts
meta: { requiresAuth: true }
```

Handle invalid IDs safely.

## 5. Navigation

Update `AppLayout.vue` with:

```text
Dashboard
Expenses
Current user email
Language switcher
Logout
```

Use `RouterLink`.

Add a simple active-link style.

Do not build the final sidebar yet.

## 6. Expense List View

Create:

```text
frontend/src/views/ExpenseListView.vue
```

On mount, call `getExpenses()`.

State:

```text
expenses
isLoading
error
```

Show for each expense:

```text
Title
Merchant name
Receipt date
Category
Total amount and currency
Input method
Confirmation status
Detected language
```

If the response has only `category_id`:

```text
category exists → Category #<id>
category is null → Uncategorized
```

Do not add extra category API calls in this step.

Each row or card must link to:

```text
/expenses/{id}
```

Show a visible `Add Expense` placeholder button, but do not build the form yet.

## 7. Expense List States

Loading:

```text
Loading expenses...
```

Empty:

```text
No expenses found.
Your expenses will appear here after you create or extract one.
```

Error:

```text
Unable to load expenses.
```

A simple Retry button is acceptable.

Do not display fake data or raw Axios errors.

## 8. Expense Detail View

Create:

```text
frontend/src/views/ExpenseDetailView.vue
```

Read the route ID and call `getExpenseById()`.

State:

```text
expense
isLoading
error
notFound
```

Show:

```text
Title
Merchant
Total
Category
Receipt number
Receipt date and time
Document type
Payment method
Currency
Subtotal
Tax
Discount
Notes
Input method
Detected language
AI confidence
Confirmation status
Created at
Updated at
```

Include:

```text
Back to Expenses
```

For absent fields, use one consistent label such as:

```text
Not available
```

## 9. Nested Expense Items

Display active items from:

```text
expense.items
```

For each item show:

```text
Original name
English name
Thai name
Quantity
Unit
Unit price
Discount
Total price
Category
```

Main item-name fallback:

```text
name_en
name_th
original_name
Unnamed item
```

If no items:

```text
No items found for this expense.
```

Do not add item editing yet.

## 10. Formatting

Create a small helper only if shared by both views:

```text
frontend/src/utils/formatters.ts
```

Possible functions:

```ts
formatMoney(amount, currency)
formatDate(value)
formatDateTime(value)
```

Requirements:

- Handle null safely
- Avoid `NaN`
- Use two decimal places for money
- Use current frontend locale where practical

Keep the helper small.

## 11. Fixed UI Translation

Update:

```text
src/locales/en.json
src/locales/th.json
```

Add keys for:

```text
Expenses
Expense Details
Add Expense
View Details
Back to Expenses
Loading Expenses
No Expenses Found
Unable to Load Expenses
Retry
Title
Merchant
Category
Receipt Number
Receipt Date
Receipt Time
Document Type
Payment Method
Currency
Subtotal
Tax
Discount
Total
Notes
Input Method
Language
AI Confidence
Confirmed
Draft
Manual
AI Extracted
English
Thai
Unknown
Not Available
Expense Items
Original Name
English Name
Thai Name
Quantity
Unit
Unit Price
Total Price
No Items
Uncategorized
Unnamed Item
```

Use Vue I18n only for fixed frontend labels.

Do not call Gemini or the backend translation endpoint.

## 12. Status Display

Show readable labels:

```text
manual → Manual
ai → AI Extracted
true → Confirmed
false → Draft
en → English
th → Thai
null → Unknown
```

Use translated UI labels.

## 13. Error Handling

For backend `404`:

```text
Expense not found.
```

Show a link back to expenses.

For `401`, rely on the existing authentication handling.

For server/network failure:

```text
Unable to connect to the server.
```

Do not expose internal error details.

## 14. Styling

Use the existing CSS approach.

Requirements:

- Responsive list
- Readable spacing
- Clear status badges
- Accessible links/buttons
- No horizontal overflow on mobile
- Simple detail sections
- No new UI framework

## 15. Frontend Tests

Add focused tests using the current Vitest/Vue Test Utils setup.

Test at least:

1. List API calls `/expenses`.
2. Detail API calls `/expenses/{id}`.
3. List loading state.
4. List displays expenses.
5. Money and currency display.
6. Manual status.
7. AI Extracted status.
8. Confirmed status.
9. Draft status.
10. Empty state.
11. Error state.
12. Detail link.
13. Detail loads route ID.
14. Main fields display.
15. Amounts display.
16. Nested items display.
17. No-items state.
18. `404` state.
19. Invalid route ID handling.
20. English/Thai labels switch.
21. Internal fields are not shown.
22. Existing auth tests remain green.

Mock all API calls.

Do not require the real backend for unit tests.

## 16. Manual Verification

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

Open:

```text
http://localhost:5173
```

Verify:

```text
Login
Open Expenses
See real backend data
Open expense detail
See nested items
Switch English/Thai
Refresh detail page
Return to list
Logout
```

If no expenses exist, create one through Swagger first.

## 17. Build and Test

Run:

```bash
npm run test
npm run build
```

Use the real package scripts.

The TypeScript build must finish without errors.

## Expected Result

After this step:

- Protected expense list page
- Protected expense detail page
- Real backend data
- Nested items
- Loading, empty, error, and 404 states
- Responsive simple UI
- English/Thai fixed labels
- Updated navigation
- Focused tests
- Clean production build

## Completion Report

Provide:

1. Changed and created files
2. Expense types
3. API functions
4. Routes
5. Navigation changes
6. List behavior
7. Detail behavior
8. Nested item behavior
9. Loading, empty, error, and 404 handling
10. English/Thai changes
11. Test result
12. Build result
13. Manual verification result
14. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
