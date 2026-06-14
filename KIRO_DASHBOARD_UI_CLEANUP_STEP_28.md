# Smart Receipt Project — Step 28: Dashboard Summary and Final UI Cleanup

## Goal

Upgrade the current basic dashboard into a useful summary page and perform a final consistency cleanup across the Vue frontend.

Use the existing backend endpoints:

```text
GET /api/expenses
GET /api/receipts
```

Expected dashboard flow:

```text
Login
→ Open Dashboard
→ See expense and receipt summaries
→ See spending grouped by currency
→ See recent expenses
→ Use quick actions
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain.

Use clear names and straightforward logic.

Avoid unnecessary chart libraries, analytics stores, backend changes, complex abstractions, and overengineering.

---

## Current Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list, detail, create, edit, delete, confirmation, translation, and Excel export
- Receipt list, upload, detail, and Gemini extraction
- SweetAlert2 notification system
- 348 frontend tests passing
- Clean production build
- Complete FastAPI backend

Inspect the existing dashboard, expense types, receipt types, API modules, formatting helpers, locales, styles, and tests before changing anything.

Do not rebuild existing features.

Do not change backend code unless a real integration mismatch is found.

---

# Scope

Implement only:

```text
Dashboard expense and receipt loading
Summary cards
Spending totals grouped by currency
Recent-expense list
Quick-action links
Dashboard loading, empty, and error states
Final visual consistency cleanup
Responsive layout cleanup
English/Thai fixed labels
Focused tests
Clean production build
```

Do not implement:

```text
New backend statistics endpoint
Charts requiring a new library
Search
Filters
Pagination
Date-range analytics
Category analytics
Budgeting
Forecasting
Notifications
Admin dashboard
```

---

# Important Coding Style

1. Write simple, human-readable code.
2. Reuse existing API functions.
3. Reuse existing expense and receipt types.
4. Reuse existing formatting helpers.
5. Keep dashboard calculations inside the dashboard view or one small utility.
6. Do not add a dashboard Pinia store unless clearly necessary.
7. Do not add a chart library.
8. Do not add a UI framework.
9. Do not combine different currencies.
10. Use real backend data only.

---

# 1. Inspect Existing Dashboard

Inspect:

```text
frontend/src/views/DashboardView.vue
```

Reuse the current protected dashboard route.

Do not create a second dashboard route.

Replace the placeholder content with the real summary layout.

Keep the current user welcome message.

---

# 2. Data Loading

On dashboard mount:

```text
Call getExpenses()
Call getReceipts()
```

Use:

```ts
Promise.all(...)
```

when practical.

State:

```text
expenses
receipts
isLoading
error
```

If one request fails:

```text
Show a safe dashboard error state
Allow Retry
```

Keep the implementation simple.

Do not make repeated API calls for each summary card.

---

# 3. Summary Calculations

Calculate:

```text
Total expenses
Confirmed expenses
Draft expenses
Total receipts
Linked receipts
Unlinked receipts
```

Definitions:

```text
Total expenses
→ number of active expenses returned by GET /api/expenses

Confirmed expenses
→ expense.is_confirmed === true

Draft expenses
→ expense.is_confirmed === false

Total receipts
→ number of receipts returned by GET /api/receipts

Linked receipts
→ receipt.expense_id is not null

Unlinked receipts
→ receipt.expense_id is null
```

Do not include deleted records if the backend already excludes them.

Do not add fake numbers.

---

# 4. Spending Totals by Currency

Calculate total spending grouped by:

```text
expense.currency
```

Example:

```text
THB 12,500.00
USD 250.00
```

Important:

```text
Do not combine THB and USD
Do not convert currencies
Do not display one grand total across different currencies
```

Use safe decimal handling.

Because amounts are strings, use a clear strategy.

For this student project, converting each amount with:

```ts
Number(expense.total_amount)
```

is acceptable for display-only dashboard summaries, provided invalid values are skipped safely.

Use the existing `formatMoney()` helper for display.

If there are no expenses:

```text
No spending data available.
```

Sort currency codes alphabetically for stable display.

---

# 5. Recent Expenses

Show the latest five expenses.

Sort by:

```text
created_at descending
```

If `receipt_date` is more appropriate for display, use it only as the visible date.

Do not use receipt date for sorting unless the project requirement specifically says so.

Each recent expense should show:

```text
Title
Merchant name
Date
Amount and currency
Draft or Confirmed status
View Details link
```

Display at most:

```text
5
```

If no expenses:

```text
No recent expenses.
```

Do not show fake sample data.

---

# 6. Dashboard Layout

Use simple sections:

```text
Welcome header
Summary cards
Spending by currency
Recent expenses
Quick actions
```

Suggested summary cards:

```text
Total Expenses
Confirmed
Drafts
Receipts
Linked Receipts
Unlinked Receipts
```

Use a responsive CSS grid.

Do not add charts unless they can be done with very simple existing CSS and add real value.

Charts are not required.

---

# 7. Quick Actions

Add buttons or links for:

```text
Add Expense
Upload Receipt
View Expenses
View Receipts
Export Excel
```

Use existing named routes:

```text
expense-create
receipt-upload
expenses
receipts
```

For Excel export:

```text
Reuse the existing export flow
```

Preferred approach:

```text
Extract the existing expense-export action into a small reusable utility/composable only if needed
```

or:

```text
Add a simple dashboard export handler using the same existing API and download helpers
```

Do not duplicate a large amount of export code.

Keep it easy to understand.

---

# 8. Dashboard Export Action

If Export Excel appears on the dashboard:

```text
Use exportExpenses()
Use getFilenameFromContentDisposition()
Use downloadBlob()
Use existing SweetAlert2 helpers
Use isExporting state
Prevent duplicate clicks
```

Reuse the same English/Thai labels already added for export.

Do not create a new export endpoint.

---

# 9. Loading State

While dashboard data loads:

```text
Loading dashboard...
```

Use a simple loading block.

Do not show summary cards with zero placeholders before real data finishes loading.

---

# 10. Error State

When loading fails:

```text
Unable to load dashboard.
```

Show:

```text
Retry
```

Do not expose raw Axios errors.

The existing 401 handler should manage expired sessions.

---

# 11. Empty State

When both expenses and receipts are empty:

```text
Welcome to Smart Receipt
Start by adding an expense or uploading a receipt.
```

Still show quick actions.

Summary cards may correctly display zero.

Do not hide the entire dashboard.

---

# 12. Final UI Consistency Cleanup

Review these pages:

```text
Dashboard
Expense List
Expense Detail
Expense Create
Expense Edit
Receipt List
Receipt Upload
Receipt Detail
Login
Register
```

Check consistency for:

```text
Page titles
Page-header spacing
Primary buttons
Secondary buttons
Danger buttons
Confirm buttons
Cards
Forms
Status badges
Loading messages
Empty states
Error states
Back links
Action rows
Mobile spacing
```

Only make small consistency improvements.

Do not redesign every page.

Do not rename working routes or API functions without a real reason.

---

# 13. Navigation Cleanup

Review `AppLayout.vue`.

Keep:

```text
Dashboard
Expenses
Receipts
User email
Language switcher
Logout
```

Ensure:

```text
Active link is clear
Navigation wraps or collapses safely on small screens
Buttons remain usable
No horizontal overflow
```

A simple mobile wrapping layout is enough.

Do not add a complex hamburger menu unless necessary.

---

# 14. Responsive Cleanup

Test typical widths:

```text
Desktop
Tablet
Mobile
```

Ensure:

```text
Summary cards wrap
Recent-expense rows remain readable
Forms stay single-column on mobile
Action buttons wrap
Tables remain scrollable
Navigation does not overflow
SweetAlert2 remains usable
```

Do not add device-specific JavaScript.

Use CSS media queries only when needed.

---

# 15. Accessibility Cleanup

Check:

```text
Buttons have readable text
Links are keyboard accessible
Inputs have labels
Disabled states are clear
Status is not communicated by color alone
Focus outlines remain visible
Images have alt text
```

Do not remove browser focus outlines without providing a replacement.

Keep changes simple.

---

# 16. English and Thai Labels

Update:

```text
frontend/src/locales/en.json
frontend/src/locales/th.json
```

Add keys for:

```text
Dashboard Summary
Loading Dashboard
Unable to Load Dashboard
Total Expenses
Confirmed Expenses
Draft Expenses
Total Receipts
Linked Receipts
Unlinked Receipts
Spending by Currency
No Spending Data
Recent Expenses
No Recent Expenses
Quick Actions
Add Expense
Upload Receipt
View Expenses
View Receipts
Welcome to Smart Receipt
Get Started Message
View Details
Retry
```

Reuse existing keys where they already exist.

Do not create duplicate keys for the same label.

Use natural Thai translations.

---

# 17. Optional Small Dashboard Utility

If calculations become crowded, create:

```text
frontend/src/utils/dashboard.ts
```

Possible functions:

```ts
countConfirmedExpenses(expenses)
countDraftExpenses(expenses)
countLinkedReceipts(receipts)
groupTotalsByCurrency(expenses)
getRecentExpenses(expenses, limit)
```

Keep functions pure and small.

Do not create a general analytics framework.

---

# 18. Tests

Add focused tests.

Suggested files:

```text
src/utils/dashboard.test.ts
src/views/dashboard.test.ts
```

Follow the existing project test style.

Test at least:

1. Dashboard calls expense API.
2. Dashboard calls receipt API.
3. Loading state displays.
4. Total-expense count is correct.
5. Confirmed count is correct.
6. Draft count is correct.
7. Total-receipt count is correct.
8. Linked-receipt count is correct.
9. Unlinked-receipt count is correct.
10. Spending totals group by currency.
11. THB and USD are not combined.
12. Invalid amount is skipped safely.
13. Currency groups are sorted consistently.
14. Recent expenses sort by `created_at` descending.
15. Only five recent expenses display.
16. Recent expense links to detail.
17. Empty dashboard state displays.
18. Quick actions remain visible when empty.
19. API failure shows safe error state.
20. Retry reloads data.
21. Add Expense quick action links correctly.
22. Upload Receipt quick action links correctly.
23. View Expenses quick action links correctly.
24. View Receipts quick action links correctly.
25. Export action reuses existing export behavior.
26. Export loading prevents duplicates.
27. English labels render.
28. Thai labels render.
29. Existing 348 tests remain green.

Mock:

```text
Expense API
Receipt API
Export API
SweetAlert2 helpers
Download helpers
Router where necessary
```

Do not call the real backend in unit tests.

---

# 19. Manual Verification

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

Verify:

```text
Login
Open Dashboard
See correct expense counts
See confirmed and draft counts
See receipt counts
See spending separated by currency
See only five recent expenses
Open recent expense detail
Use Add Expense
Use Upload Receipt
Use View Expenses
Use View Receipts
Use Export Excel
Switch English/Thai
Resize browser to mobile width
Check navigation and cards
```

Also test:

```text
No expenses
No receipts
Backend stopped
Retry after backend restarts
Mixed THB and USD expenses
More than five expenses
```

---

# 20. Backend Regression Check

No backend changes are expected.

If a real mismatch requires backend changes:

```bash
cd backend
source venv/bin/activate
pytest
```

Otherwise, leave backend code unchanged.

---

# 21. Build Verification

Run:

```bash
npm run test
npm run build
```

The TypeScript build must finish with zero errors.

---

# Do Not Implement Yet

Do not implement:

- Full end-to-end integration testing
- New backend statistics endpoints
- Charts requiring libraries
- Search
- Filters
- Pagination
- Budgets
- Forecasting
- Notifications
- Admin dashboard
- Date-range analytics
- Category analytics

---

# Expected Result

After this step:

- Useful dashboard summary
- Correct expense and receipt counts
- Spending grouped by currency
- Five recent expenses
- Quick actions
- Dashboard loading, empty, and error states
- Consistent navigation and page styling
- Improved responsive layout
- English/Thai labels
- Focused tests
- Clean production build

---

# Required Completion Report

Provide:

1. Changed and created files
2. Dashboard data-loading behavior
3. Summary calculations
4. Currency grouping behavior
5. Recent-expense sorting behavior
6. Quick-action behavior
7. Export reuse behavior
8. Loading, empty, error, and retry behavior
9. Navigation cleanup
10. Responsive cleanup
11. Accessibility cleanup
12. English/Thai changes
13. Tests and result
14. Build result
15. Manual verification result
16. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
