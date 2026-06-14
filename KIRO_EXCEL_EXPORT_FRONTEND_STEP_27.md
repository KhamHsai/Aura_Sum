# Smart Receipt Project — Step 27: Excel Export UI

## Goal

Add the frontend flow for exporting expenses to an Excel file.

Connect to:

```text
GET /api/expenses/export
```

Expected flow:

```text
Open Expenses
→ Click Export Excel
→ Backend generates an .xlsx file
→ Browser downloads the file
→ Show success or error feedback
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain.

Use clear names and straightforward logic.

Avoid unnecessary abstractions, download libraries, export stores, generic file utilities, and overengineering.

---

## Current Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list, detail, create, edit, delete, and confirmation
- SweetAlert2 helpers
- Receipt upload and Gemini extraction
- Dynamic English–Thai expense translation
- 290 frontend tests passing
- Clean production build
- Complete FastAPI backend with Excel export support

Inspect the real backend export response before changing anything.

Do not rebuild existing features.

Do not change backend code unless a real integration mismatch is found.

---

# Scope

Implement only:

```text
Excel export API function
Blob response handling
Content-Disposition filename parsing
Fallback filename
Browser download trigger
Object URL cleanup
Export loading state
Duplicate-download prevention
SweetAlert2 success/error feedback
English/Thai fixed labels
Focused frontend tests
Clean production build
```

Do not implement:

```text
Dashboard statistics
Search
Filters
Pagination
Custom export columns
Date-range export
Category-filtered export
PDF export
CSV export
Scheduled export
Email export
```

---

# Important Coding Style

1. Write simple, human-readable code.
2. Use the existing Axios client.
3. Keep export API logic inside `src/api`.
4. Keep browser download logic simple and local.
5. Reuse SweetAlert2 helpers.
6. Use Vue I18n for fixed labels.
7. Do not add a file-download library.
8. Do not add an export Pinia store.
9. Do not duplicate authentication headers.
10. Clean up temporary browser resources.

---

# 1. Inspect Real Backend Export Behavior

Before coding, inspect:

```text
GET /api/expenses/export
```

Confirm:

```text
Status code
Response MIME type
Response body type
Content-Disposition header
Filename format
Behavior when no expenses exist
Behavior for deleted expenses
Authentication requirements
Error response format
```

Do not guess.

Expected successful MIME type may be:

```text
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

Match the real backend exactly.

---

# 2. Export API Function

Update:

```text
frontend/src/api/expenseApi.ts
```

Add a function such as:

```ts
exportExpenses()
```

Use:

```ts
responseType: 'blob'
```

Suggested shape:

```ts
export interface ExpenseExportResult {
  blob: Blob
  contentDisposition: string | null
  contentType: string | null
}

export async function exportExpenses(): Promise<ExpenseExportResult> {
  const response = await apiClient.get('/expenses/export', {
    responseType: 'blob',
  })

  return {
    blob: response.data,
    contentDisposition: response.headers['content-disposition'] ?? null,
    contentType: response.headers['content-type'] ?? null,
  }
}
```

Adjust to the project’s existing Axios typing style.

Do not navigate inside the API module.

Do not trigger browser downloads inside the API module unless the current project structure clearly makes that simpler.

---

# 3. Filename Parsing

Create a small helper only if useful:

```text
frontend/src/utils/download.ts
```

Possible functions:

```ts
getFilenameFromContentDisposition(header)
downloadBlob(blob, filename)
```

Keep it small and specific.

Support common header forms:

```text
attachment; filename="expenses.xlsx"
attachment; filename=expenses.xlsx
attachment; filename*=UTF-8''expenses.xlsx
```

Use the backend-provided filename when valid.

Fallback:

```text
expenses-export.xlsx
```

Do not trust unsafe path content.

Strip or reject:

```text
../
..\
directory separators
control characters
```

The final filename should remain a simple local filename.

---

# 4. Blob Download Helper

Use standard browser APIs:

```ts
const url = URL.createObjectURL(blob)
const link = document.createElement('a')

link.href = url
link.download = filename
document.body.appendChild(link)
link.click()
link.remove()

URL.revokeObjectURL(url)
```

Ensure cleanup runs even if clicking fails.

A `try/finally` block is recommended.

Do not leave temporary links in the DOM.

Do not leak object URLs.

---

# 5. Expense List Export Button

Update:

```text
frontend/src/views/ExpenseListView.vue
```

Place near:

```text
Add Expense
Export Excel
```

Use a clear button:

```text
Export Excel
```

State:

```text
isExporting
```

Behavior:

```text
1. User clicks Export Excel
2. Set isExporting = true
3. Call exportExpenses()
4. Validate Blob
5. Resolve filename
6. Trigger browser download
7. Show success alert
8. Reset isExporting
```

Disable while exporting.

Prevent duplicate clicks.

---

# 6. Export Loading State

While exporting:

```text
Exporting...
```

Disable the export button.

Do not block the entire expense list.

Do not show fake percentage progress because the backend does not provide download progress.

---

# 7. Validate Successful Response

Before download, check:

```text
Blob exists
Blob size is greater than 0
Content type is valid when available
```

Expected content type:

```text
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

Some servers may append charset or use a generic binary type.

Do not reject a valid file only because the header is slightly different.

Use practical validation.

---

# 8. Blob Error Response Handling

Because the request uses:

```text
responseType: 'blob'
```

backend JSON errors may arrive as Blob data.

Handle safely:

```text
1. Check error.response.data instanceof Blob
2. Read Blob text
3. Attempt JSON.parse
4. Extract a safe detail/message
5. Fall back to generic export failure
```

Support FastAPI formats:

```json
{
  "detail": "message"
}
```

and:

```json
{
  "detail": [
    {
      "loc": ["..."],
      "msg": "message",
      "type": "..."
    }
  ]
}
```

Do not expose raw JSON, stack traces, database messages, or internal paths.

Hide suspiciously long messages.

---

# 9. Error Mapping

Handle:

```text
401 → existing auth/session handling
404 → export endpoint or resource not found
409 → no exportable expenses, if backend uses it
422 → invalid export request, if applicable
500 → export generation failed
Network failure → unable to connect
Empty Blob → invalid export response
```

Use safe user-facing messages.

If the backend returns a safe short message such as:

```text
No expenses available for export
```

it may be displayed.

---

# 10. SweetAlert2 Feedback

Use existing alert helpers.

Success:

```text
Export completed
Your Excel file has been downloaded.
```

Failure:

```text
Unable to export expenses
Please try again.
```

Possible no-data message:

```text
No expenses to export
Create at least one expense before exporting.
```

Avoid duplicate inline and popup messages for the same export result.

---

# 11. English and Thai Labels

Update:

```text
frontend/src/locales/en.json
frontend/src/locales/th.json
```

Add keys for:

```text
Export Excel
Exporting
Export Completed
Export Completed Message
Unable to Export Expenses
Export Failed Message
No Expenses to Export
No Expenses to Export Message
Invalid Export File
Download Started
Excel File
Please Try Again
```

Use natural Thai translations.

Do not hard-code alert strings in components.

---

# 12. Styling

Use existing CSS.

Add simple styles only if needed for:

```text
Expense-list action row
Export button
Disabled exporting state
Responsive action buttons
```

Keep:

```text
Add Expense
Export Excel
```

usable on mobile.

Do not add another UI framework.

Do not redesign the whole expense list.

---

# 13. Tests

Add focused frontend tests.

Suggested files:

```text
src/api/expense.export.test.ts
src/utils/download.test.ts
src/views/expense.export.test.ts
```

Or follow the current test organization.

Test at least:

1. Export API calls `GET /expenses/export`.
2. Export API uses `responseType: 'blob'`.
3. Export API uses the existing Axios client.
4. Content-Disposition header is returned.
5. Content-Type header is returned.
6. Quoted filename is parsed.
7. Unquoted filename is parsed.
8. UTF-8 filename format is parsed.
9. Missing filename uses fallback.
10. Unsafe path characters are removed.
11. Blob download creates an object URL.
12. Temporary anchor is created.
13. Anchor receives correct `download` filename.
14. Anchor click is triggered.
15. Temporary anchor is removed.
16. Object URL is revoked.
17. Cleanup occurs if click throws.
18. Export button appears on expense list.
19. Clicking export starts API request.
20. Button is disabled while exporting.
21. Duplicate export clicks are prevented.
22. Valid Blob starts download.
23. Success alert is shown.
24. Empty Blob shows error alert.
25. Missing filename uses fallback.
26. Backend JSON error Blob is parsed safely.
27. FastAPI array error is parsed safely.
28. Invalid JSON Blob uses generic message.
29. Network failure shows safe error alert.
30. No real file download occurs in tests.
31. English labels render.
32. Thai labels render.
33. Existing 290 tests remain green.

Mock:

```text
Export API
SweetAlert2 helpers
URL.createObjectURL
URL.revokeObjectURL
document.createElement or anchor click
```

Do not write real files during unit tests.

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

Verify:

```text
Login
Open Expenses
Click Export Excel
See Exporting state
Confirm one .xlsx file downloads
Open the file in Excel, Numbers, or LibreOffice
Confirm filename is correct
Confirm expense data is present
Switch English/Thai
Confirm button and alerts change language
Click rapidly and confirm duplicate downloads are prevented
```

Also test:

```text
No expenses available
Backend stopped
Session expired
Backend export error
Missing Content-Disposition header, if safely testable
```

---

# 15. Backend Regression Check

No backend changes are expected.

If a real mismatch requires backend changes:

```bash
cd backend
source venv/bin/activate
pytest
```

Otherwise, leave backend code unchanged.

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

- Dashboard statistics
- Search
- Filters
- Pagination
- Date-range export
- Category-filtered export
- Custom export columns
- CSV export
- PDF export
- Scheduled exports
- Email exports

---

# Expected Result

After this step:

- Excel export API integration
- Blob response handling
- Safe filename parsing
- Fallback filename
- Browser file download
- Temporary URL cleanup
- Export loading state
- Duplicate-download prevention
- SweetAlert2 success/error feedback
- English/Thai labels
- Focused tests
- Clean production build

---

# Required Completion Report

Provide:

1. Changed and created files
2. Real backend export behavior
3. Export API function
4. Blob response handling
5. Filename parsing
6. Download helper behavior
7. Object URL and DOM cleanup
8. Expense-list export button behavior
9. Loading and duplicate prevention
10. Blob error parsing
11. Error mapping
12. SweetAlert2 behavior
13. English/Thai changes
14. Tests and result
15. Build result
16. Manual verification result
17. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
