# Smart Receipt Project — Step 23: SweetAlert2 Notifications and Expense Soft-Delete

## Goal

Add a consistent alert system with SweetAlert2 and implement expense soft-delete from the Vue frontend.

This step should add:

```text
SweetAlert2 setup
Reusable alert helpers
Success alerts
Server-error alerts
Delete confirmation dialog
Expense soft-delete button
Post-delete navigation
English/Thai alert text
Focused tests
Clean production build
```

Expected flow:

```text
Expense Detail
→ Click Delete
→ SweetAlert2 confirmation
→ Confirm
→ DELETE /api/expenses/{expense_id}
→ Success alert
→ Return to Expenses list
```

Also improve create and update success feedback:

```text
Create Expense
→ Save
→ SweetAlert2 success alert
→ Open detail page
```

```text
Edit Expense
→ Save
→ SweetAlert2 success alert
→ Return to detail page
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain.

Use clear names and straightforward logic.

Avoid unnecessary wrappers, complex notification frameworks, global event buses, and overengineering.

---

## Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list and detail pages
- Manual expense create and edit pages
- Category loading
- Dynamic item rows
- Frontend validation
- 74 frontend tests passing
- Clean production build
- Complete FastAPI backend with soft-delete support

Inspect the existing frontend and backend route definitions before changing anything.

Do not rebuild existing features.

Do not change backend code unless a real integration mismatch is found.

---

# Scope

Implement only:

```text
Install SweetAlert2
Create simple reusable alert helpers
Add success alerts to create and update
Add important server-error alerts
Add delete API function
Add delete button to expense detail
Add delete confirmation dialog
Handle delete success and failure
Add English/Thai fixed alert labels
Add focused tests
Verify build
```

Do not implement:

```text
Receipt upload
Gemini extraction UI
AI confirmation UI
Dynamic translation button
Excel export button
Search
Filters
Pagination
Dashboard statistics
Bulk delete
Undo delete
Permanent delete
```

---

# Important UX Rule

Do not replace all inline validation with popups.

Keep this behavior:

```text
Inline validation
→ required fields
→ invalid amounts
→ item validation
→ field-specific form errors
```

Use SweetAlert2 for:

```text
Create success
Update success
Delete confirmation
Delete success
Important server failure
Session-expired notice if appropriate
```

Do not show a popup for every small field error.

---

# Important Coding Style

1. Write simple, human-readable code.
2. Use the direct `sweetalert2` package.
3. Do not add `vue-sweetalert2`.
4. Create one small alert utility.
5. Avoid global plugins unless truly required.
6. Avoid event buses.
7. Avoid a large notification store.
8. Reuse Vue I18n strings.
9. Keep delete logic in the expense detail page.
10. Match the real backend delete response exactly.

---

# 1. Install SweetAlert2

Inside:

```text
frontend/
```

Install:

```bash
npm install sweetalert2
```

Do not install:

```text
vue-sweetalert2
```

Use direct imports:

```ts
import Swal from 'sweetalert2'
```

---

# 2. Alert Utility

Create:

```text
frontend/src/utils/alerts.ts
```

Keep it small.

Suggested helpers:

```ts
showSuccessAlert(...)
showErrorAlert(...)
showDeleteConfirmation(...)
```

Possible shape:

```ts
import Swal from 'sweetalert2'

export function showSuccessAlert(
  title: string,
  text?: string
) {
  return Swal.fire({
    icon: 'success',
    title,
    text,
    confirmButtonText: 'OK',
  })
}
```

```ts
export function showErrorAlert(
  title: string,
  text?: string
) {
  return Swal.fire({
    icon: 'error',
    title,
    text,
    confirmButtonText: 'OK',
  })
}
```

```ts
export function showDeleteConfirmation(options: {
  title: string
  text: string
  confirmButtonText: string
  cancelButtonText: string
}) {
  return Swal.fire({
    icon: 'warning',
    title: options.title,
    text: options.text,
    showCancelButton: true,
    confirmButtonText: options.confirmButtonText,
    cancelButtonText: options.cancelButtonText,
    focusCancel: true,
  })
}
```

Use translated strings from the calling component.

Do not import Vue I18n directly inside the alert utility unless the existing architecture makes that clearly simpler.

---

# 3. Delete API Function

Update:

```text
frontend/src/api/expenseApi.ts
```

Add:

```ts
deleteExpense(expenseId: number)
```

Connect to the actual backend route:

```text
DELETE /api/expenses/{expense_id}
```

Inspect the real backend response.

It may return:

```text
204 No Content
```

or a JSON response.

Match the real behavior exactly.

Do not assume response data exists.

Do not navigate inside the API module.

---

# 4. Expense Detail Delete Button

Update:

```text
frontend/src/views/ExpenseDetailView.vue
```

Add a visible button:

```text
Delete Expense
```

Place it near:

```text
Edit Expense
Back to Expenses
```

Use a danger style.

Do not show the delete button while the page is loading or when the expense failed to load.

---

# 5. Delete Confirmation Flow

On Delete click:

```text
1. Open SweetAlert2 warning dialog
2. Show expense title when available
3. User can cancel
4. If cancelled, do nothing
5. If confirmed, call deleteExpense(id)
6. Disable repeated delete actions while request is running
7. Show success alert
8. Redirect to /expenses
```

Suggested confirmation text:

```text
Delete this expense?
This expense will be removed from your active expense list.
```

Because the backend uses soft-delete, do not say:

```text
This permanently deletes the record
```

unless that is actually true.

---

# 6. Delete Failure Handling

If delete fails:

```text
Show SweetAlert2 error alert
Keep the user on the detail page
Do not clear the loaded expense
Allow retry
```

Handle:

```text
401 → existing auth handling
404 → expense already missing
422 → safe validation message
500/network → generic delete failure
```

Do not show raw Axios errors or stack traces.

---

# 7. Create Success Alert

Update:

```text
frontend/src/views/ExpenseCreateView.vue
```

After successful creation:

```text
1. Show success alert
2. Then navigate to /expenses/{created.id}
```

Suggested text:

```text
Expense created
Your expense was saved successfully.
```

Use translated labels.

Avoid showing both an inline success message and a popup for the same event.

---

# 8. Edit Success Alert

Update:

```text
frontend/src/views/ExpenseEditView.vue
```

After successful update:

```text
1. Show success alert
2. Then navigate to /expenses/{id}
```

Suggested text:

```text
Expense updated
Your changes were saved successfully.
```

Use translated labels.

---

# 9. Important Save Failure Alerts

The form should keep existing inline/backend error text.

Additionally, for major save failures such as network/server failure:

```text
Show SweetAlert2 error alert
```

Do not show duplicate popups for simple frontend validation errors.

Recommended rule:

```text
Frontend validation failure
→ inline only

Backend 422 validation failure
→ inline form error

Network/500 failure
→ inline error + SweetAlert2 error alert
```

Keep the implementation simple and consistent.

---

# 10. English and Thai Labels

Update:

```text
frontend/src/locales/en.json
frontend/src/locales/th.json
```

Add keys for:

```text
Delete Expense
Delete Expense Title
Delete Expense Message
Confirm Delete
Cancel
Expense Deleted
Expense Deleted Message
Unable to Delete Expense
Expense Created
Expense Created Message
Expense Updated
Expense Updated Message
Unable to Save Expense
Something Went Wrong
OK
```

Use natural Thai text.

Do not hard-code English alert strings inside components.

---

# 11. Styling

Update existing CSS for:

```text
Danger button
Disabled delete button
Action button spacing
```

SweetAlert2 provides its own dialog styling.

Do not heavily customize SweetAlert2.

Do not add custom themes unless necessary.

Keep the existing project design consistent.

---

# 12. Session Expired Behavior

Inspect the existing Axios `401` handling.

If it currently redirects silently to login, optionally show one SweetAlert2 notice:

```text
Session expired
Please log in again.
```

Only add this if it can be implemented without redirect loops or duplicate dialogs.

If it complicates the architecture, leave the current 401 behavior unchanged in this step.

Do not build refresh-token handling.

---

# 13. Tests

Add focused tests.

Suggested files:

```text
src/utils/alerts.test.ts
src/api/expense.delete.test.ts
src/views/expense.delete.test.ts
```

Or follow the current project test organization.

Test at least:

1. SweetAlert2 package is used directly.
2. Success alert helper calls `Swal.fire`.
3. Error alert helper calls `Swal.fire`.
4. Confirmation helper uses warning icon.
5. Confirmation helper includes cancel button.
6. Delete API calls `DELETE /expenses/{id}`.
7. Detail page shows Delete Expense button.
8. Delete click opens confirmation.
9. Cancelled confirmation does not call API.
10. Confirmed deletion calls API.
11. Delete success shows success alert.
12. Delete success redirects to `/expenses`.
13. Delete failure shows error alert.
14. Delete failure stays on detail page.
15. Repeated delete is prevented while loading.
16. Create success shows success alert.
17. Create success navigates after alert.
18. Edit success shows success alert.
19. Edit success navigates after alert.
20. Frontend validation does not show SweetAlert2.
21. English labels render.
22. Thai labels render.
23. Existing 74 tests remain green.

Mock:

```text
SweetAlert2
Axios/API calls
Router navigation
```

Do not open real browser dialogs in unit tests.

---

# 14. Manual Verification

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

Manually verify:

```text
Create expense
See success alert
Open created detail
Edit expense
See update success alert
Click Delete
Cancel confirmation
Confirm expense remains
Click Delete again
Confirm deletion
See success alert
Return to expense list
Confirm deleted expense no longer appears
Switch English/Thai
Check alert text changes language
```

Also test one server failure if practical:

```text
Stop backend
Try deleting or saving
Confirm safe error alert appears
Restart backend
```

---

# 15. Backend Regression Check

Because this step should not change backend code, backend tests should remain unchanged.

If backend code is changed for a real mismatch, run:

```bash
cd backend
source venv/bin/activate
pytest
```

Otherwise, no backend modification is expected.

---

# 16. Build Verification

Run:

```bash
npm run test
npm run build
```

The TypeScript build must finish with zero errors.

---

# Do Not Implement Yet

Do not implement:

- Receipt upload
- Gemini extraction UI
- AI review/confirmation
- Dynamic expense translation
- Excel export
- Search
- Filters
- Pagination
- Dashboard statistics
- Permanent delete
- Restore deleted expense
- Bulk delete

---

# Expected Result

After this step:

- SweetAlert2 installed directly
- Small reusable alert utility
- Create success alert
- Update success alert
- Delete confirmation dialog
- Expense soft-delete frontend flow
- Delete success/error feedback
- English/Thai alert labels
- Focused tests
- Clean production build

---

# Required Completion Report

Provide:

1. Changed and created files
2. SweetAlert2 package setup
3. Alert helper design
4. Delete API behavior
5. Delete button behavior
6. Confirmation behavior
7. Delete success/failure behavior
8. Create/update success alert behavior
9. Inline validation versus popup behavior
10. English/Thai alert labels
11. Tests added and result
12. Build result
13. Manual verification result
14. Any backend/frontend mismatch found

Do not produce a long walkthrough unless an error occurs.
