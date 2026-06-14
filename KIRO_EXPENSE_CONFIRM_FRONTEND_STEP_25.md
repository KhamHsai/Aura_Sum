# Smart Receipt Project — Step 25: Review and Confirm AI-Extracted Expense

## Goal

Add the frontend flow for reviewing and confirming AI-created draft expenses.

Connect to:

```text
POST /api/expenses/{expense_id}/confirm
```

Expected flow:

```text
Upload receipt
→ Gemini creates draft expense
→ User reviews and edits the expense
→ User clicks Confirm Expense
→ SweetAlert2 confirmation
→ Backend confirms the expense
→ Success alert
→ Open expense detail
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain.

Use clear names and straightforward logic.

Avoid unnecessary abstractions, complex workflow engines, confirmation stores, and overengineering.

---

## Current Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list, detail, create, edit, and soft-delete
- SweetAlert2 helpers
- Receipt list, upload, detail, and Gemini extraction
- Automatic redirect to draft expense edit page
- 177 frontend tests passing
- Clean production build
- Complete FastAPI backend with expense confirmation endpoint

Inspect the real backend confirmation route and response before changing anything.

Do not rebuild existing features.

Do not change backend code unless a real integration mismatch is found.

---

# Scope

Implement only:

```text
Confirm expense API function
Confirm button for draft expenses
Confirmation dialog
Confirm success handling
Confirm error handling
Edit-page confirmation flow
Detail-page confirmation flow
Confirmed-state UI
English/Thai fixed labels
Focused frontend tests
Clean production build
```

Do not implement:

```text
Dynamic translation
Excel export
Search
Filters
Pagination
Dashboard statistics
Receipt deletion
Bulk confirmation
Unconfirm action
Approval workflow
Role-based confirmation
```

---

# Important Coding Style

1. Write simple, human-readable code.
2. Match the backend confirmation response exactly.
3. Keep API calls inside `src/api`.
4. Reuse the existing SweetAlert2 helpers.
5. Reuse existing expense types when possible.
6. Keep confirmation logic inside the related views.
7. Do not add a confirmation Pinia store.
8. Do not create a workflow framework.
9. Keep frontend checks simple.
10. Let the backend remain the final validator.

---

# 1. Inspect Real Backend Confirmation Behavior

Before coding, inspect:

```text
POST /api/expenses/{expense_id}/confirm
```

Confirm:

```text
Request body required or not
Response shape
Status code
Validation rules
Behavior when already confirmed
Behavior when expense does not exist
Behavior when expense belongs to another user
Whether confirmed expenses can still be edited
```

Do not guess.

Match the real backend behavior exactly.

---

# 2. Confirm API Function

Update:

```text
frontend/src/api/expenseApi.ts
```

Add:

```ts
confirmExpense(expenseId: number)
```

Connect to:

```text
POST /api/expenses/{expense_id}/confirm
```

Use the existing Axios client.

Return the typed backend response.

If the endpoint returns an updated `Expense`, return that.

If it returns a message object, type it correctly.

Do not navigate inside the API module.

---

# 3. Expense Types

Update:

```text
frontend/src/types/expense.ts
```

Only if needed.

Use the existing field:

```text
is_confirmed
```

If the confirmation endpoint returns another type, add a small typed interface.

Do not duplicate the full Expense interface.

Do not use `any`.

---

# 4. Draft vs Confirmed Rules

Use the real backend field:

```text
is_confirmed
```

Behavior:

```text
is_confirmed = false
→ show Draft badge
→ show Confirm Expense button

is_confirmed = true
→ show Confirmed badge
→ hide Confirm Expense button
```

Do not show confirmation action for already confirmed expenses.

Prevent duplicate confirmation while the request is in progress.

---

# 5. Confirmation Dialog

Use SweetAlert2 before calling the API.

Suggested text:

```text
Confirm this expense?
Please make sure the extracted information is correct before confirming.
```

Buttons:

```text
Confirm Expense
Cancel
```

Flow:

```text
1. User clicks Confirm Expense
2. Open warning confirmation dialog
3. Cancel → do nothing
4. Confirm → call API
5. Disable repeated action while loading
6. Show success alert
7. Navigate or refresh
```

Do not call the API before user confirmation.

---

# 6. Expense Edit Page

Update:

```text
frontend/src/views/ExpenseEditView.vue
```

When expense is a draft:

```text
Save Changes
Confirm Expense
Cancel
```

Recommended behavior:

```text
Save Changes
→ save current form only
→ stay with normal existing update flow

Confirm Expense
→ validate current form
→ save current form first
→ then call confirm endpoint
→ show success alert
→ navigate to expense detail
```

This ensures the latest corrections are saved before confirmation.

Important:

```text
Do not confirm unsaved form data.
```

If saving fails:

```text
Do not call confirm endpoint.
```

If confirmation fails after save:

```text
Keep the user on the page
Show safe error feedback
Allow retry
```

---

# 7. Edit-Page Confirm Flow

Use this clear sequence:

```text
1. Run frontend validation
2. If invalid, show inline errors only
3. Ask for SweetAlert2 confirmation
4. If cancelled, stop
5. Build the cleaned complete update request
6. Call updateExpense(id, request)
7. If update succeeds, call confirmExpense(id)
8. Show success alert
9. Navigate to /expenses/{id}
```

Keep the button disabled during:

```text
saving
confirming
```

Use one simple loading label:

```text
Confirming...
```

---

# 8. Expense Detail Page

Update:

```text
frontend/src/views/ExpenseDetailView.vue
```

For a draft expense:

```text
Show Confirm Expense button
```

For a confirmed expense:

```text
Show Confirmed badge only
Hide Confirm Expense button
```

Detail-page flow:

```text
1. Click Confirm Expense
2. Open confirmation dialog
3. Confirm
4. Call confirmExpense(id)
5. Show success alert
6. Refresh local expense state or reload detail
```

Preferred simple behavior:

```text
Replace local expense state with returned updated expense
```

If the endpoint does not return the expense:

```text
Call getExpenseById(id) once after confirmation
```

Do not reload the whole browser page.

---

# 9. Edit Availability After Confirmation

Inspect backend behavior.

If confirmed expenses can still be edited:

```text
Keep Edit Expense button
Hide Confirm Expense button
Show Confirmed badge
```

If backend blocks editing after confirmation:

```text
Hide or disable Edit Expense button
Show a clear confirmed message
```

Follow the real backend rule.

Do not invent a restriction.

---

# 10. Frontend Validation

Before confirm from edit page, reuse existing validation:

```text
Category required
Title required
Currency required
Total required
Amounts valid
Item rules valid
```

Do not create a second validation system.

Detail-page confirmation should rely mostly on backend validation because there is no active form.

Backend remains the final validator.

---

# 11. Confirmation Error Mapping

Handle safely:

```text
400 or 422 → expense data is incomplete or invalid
404 → expense not found
409 → already confirmed, if backend uses this
401 → existing auth handling
500/network → unable to confirm
```

Show user-friendly messages.

Do not expose:

```text
Raw validation JSON
Stack traces
Internal exception names
Database details
```

For backend validation errors, show the safest useful message.

---

# 12. SweetAlert2 Feedback

Use existing alert helpers.

Confirmation dialog:

```text
Warning icon
Confirm button
Cancel button
```

Success:

```text
Expense confirmed
The expense has been confirmed successfully.
```

Failure:

```text
Unable to confirm expense
Please review the information and try again.
```

Avoid duplicate alerts.

Frontend field validation remains inline.

---

# 13. English and Thai Labels

Update:

```text
frontend/src/locales/en.json
frontend/src/locales/th.json
```

Add keys for:

```text
Confirm Expense
Confirm This Expense
Confirm Expense Message
Confirming
Expense Confirmed
Expense Confirmed Message
Unable to Confirm Expense
Review Information
Already Confirmed
Confirmed Expense
Save Before Confirming
Incomplete Expense
Please Review and Try Again
```

Use natural Thai translations.

Do not hard-code alert text in components.

---

# 14. Styling

Use existing CSS.

Add simple styles only if needed for:

```text
Confirm button
Confirmed status area
Draft action group
Disabled confirmation button
```

Reuse existing button classes where possible.

Do not redesign the whole page.

Do not add another UI framework.

---

# 15. Tests

Add focused tests.

Suggested files:

```text
src/api/expense.confirm.test.ts
src/views/expense.confirm.detail.test.ts
src/views/expense.confirm.edit.test.ts
```

Or follow the current test organization.

Test at least:

1. Confirm API calls `POST /expenses/{id}/confirm`.
2. Confirm API uses the existing Axios client.
3. Draft detail shows Confirm Expense button.
4. Confirmed detail hides Confirm Expense button.
5. Detail confirmation opens SweetAlert2 dialog.
6. Cancelled confirmation does not call API.
7. Confirmed action calls API.
8. Detail success shows success alert.
9. Detail success updates displayed confirmed state.
10. Detail failure shows safe error alert.
11. Detail failure stays on current page.
12. Duplicate confirmation is prevented.
13. Draft edit page shows Confirm Expense button.
14. Confirmed edit page hides or disables confirmation according to backend behavior.
15. Edit confirmation validates form first.
16. Invalid edit form does not show confirmation popup.
17. Cancelled edit confirmation does not save or confirm.
18. Edit confirm saves complete current expense first.
19. Edit confirm sends full item list.
20. Confirm endpoint is called only after update succeeds.
21. Update failure prevents confirmation.
22. Confirm failure after update is handled safely.
23. Successful edit confirmation navigates to detail.
24. Already-confirmed response is handled safely.
25. English labels render.
26. Thai labels render.
27. Existing 177 tests remain green.

Mock:

```text
Expense API calls
SweetAlert2 helpers
Router navigation
```

Do not call the real backend in unit tests.

---

# 16. Manual Verification

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
Upload and extract a receipt
Open draft expense edit page
Correct extracted data
Click Confirm Expense
Cancel once
Confirm again
See success alert
Open detail page
See Confirmed badge
Confirm button is hidden
Refresh page
Confirmed state remains
Switch English/Thai
```

Also verify:

```text
Try confirming incomplete draft data
Confirm backend validation is displayed safely
Try repeated confirmation
Confirm duplicate request is prevented or safely handled
```

A real extraction may consume Gemini quota. Existing draft expenses may be used for manual confirmation testing.

---

# 17. Backend Regression Check

No backend changes are expected.

If a real mismatch requires backend changes:

```bash
cd backend
source venv/bin/activate
pytest
```

Otherwise, leave the backend unchanged.

---

# 18. Build Verification

Run:

```bash
npm run test
npm run build
```

The TypeScript build must finish with zero errors.

---

# Do Not Implement Yet

Do not implement:

- Dynamic English/Thai expense translation
- Excel export
- Search
- Filters
- Pagination
- Dashboard statistics
- Unconfirm action
- Bulk confirmation
- Approval workflow
- Role permissions
- Receipt deletion

---

# Expected Result

After this step:

- Confirm expense API integration
- Draft-only confirmation action
- Edit-page save-then-confirm flow
- Detail-page confirmation flow
- SweetAlert2 confirmation dialog
- Success and error feedback
- Confirmed status UI
- English/Thai labels
- Focused tests
- Clean production build

---

# Required Completion Report

Provide:

1. Changed and created files
2. Real backend confirmation behavior
3. Confirm API function
4. Draft/confirmed UI behavior
5. Edit-page confirm flow
6. Detail-page confirm flow
7. Save-before-confirm behavior
8. Error mapping
9. SweetAlert2 behavior
10. Edit availability after confirmation
11. English/Thai changes
12. Tests and result
13. Build result
14. Manual verification result
15. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
