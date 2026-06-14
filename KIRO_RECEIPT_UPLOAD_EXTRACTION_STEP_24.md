# Smart Receipt Project — Step 24: Receipt Upload and Gemini Extraction UI

## Goal

Build the Vue frontend flow for uploading receipts and extracting expense data with the existing Gemini-powered backend.

Create these protected routes:

```text
/receipts
/receipts/upload
/receipts/:id
```

Connect to the existing backend endpoints:

```text
POST /api/receipts/upload
GET  /api/receipts
GET  /api/receipts/{receipt_id}
POST /api/receipts/{receipt_id}/extract
```

Expected flow:

```text
Login
→ Open Receipts
→ Upload receipt
→ Automatically run extraction
→ Backend creates a draft expense
→ Open the draft expense edit page
→ User reviews and corrects the extracted data
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain.

Use clear names and straightforward logic.

Avoid unnecessary abstractions, upload frameworks, generic file managers, complex stores, and overengineering.

---

## Current Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list and detail
- Manual expense create and edit
- SweetAlert2 notification helpers
- Expense soft-delete
- 116 frontend tests passing
- Clean production build
- Complete FastAPI backend
- Receipt upload backend
- Gemini extraction backend
- Draft expense creation from extraction

Inspect the existing frontend and backend schemas before changing anything.

Do not rebuild existing features.

Do not change backend code unless a real integration mismatch is found.

---

# Scope

Implement only:

```text
Receipt TypeScript types
Receipt API functions
Receipt list page
Receipt upload page
Receipt detail page
File validation
Image preview
Multipart upload
Upload loading/progress state
Gemini extraction action
Automatic extraction after upload
Extraction loading state
Redirect to draft expense edit page
SweetAlert2 success/error feedback
English/Thai fixed labels
Focused frontend tests
Clean production build
```

Do not implement:

```text
AI expense confirmation
Dynamic expense translation
Excel export
Receipt edit
Receipt permanent delete
Bulk receipt actions
Search
Filters
Pagination
Dashboard statistics
Drag-and-drop library
Camera capture
```

---

# Important Coding Style

1. Write simple, human-readable Vue and TypeScript code.
2. Match the real backend response schemas exactly.
3. Keep API calls inside `src/api`.
4. Use the existing Axios client.
5. Use the existing SweetAlert2 helpers.
6. Use Vue I18n for fixed labels.
7. Avoid a receipt Pinia store unless it clearly simplifies the code.
8. Direct API calls from views are acceptable.
9. Do not install a file-upload library.
10. Do not install a preview library.
11. Use native file input and browser APIs.
12. Mock all Gemini calls in tests.

---

# 1. Inspect Real Backend Schemas

Before coding, inspect the actual backend schemas and route responses for:

```text
POST /api/receipts/upload
GET /api/receipts
GET /api/receipts/{receipt_id}
POST /api/receipts/{receipt_id}/extract
```

Confirm:

```text
Receipt field names
Receipt ID type
File URL/path field
Original file name field
MIME type field
File size field
Extraction status field
Linked expense field
Soft-delete behavior
Upload response shape
Extraction response shape
```

Do not invent fields.

Do not assume the extraction endpoint directly returns an expense ID until the real response is inspected.

If the response includes a nested expense, map it correctly.

---

# 2. Receipt Types

Create:

```text
frontend/src/types/receipt.ts
```

Add simple interfaces matching the backend.

Possible fields may include:

```ts
export interface Receipt {
  id: number
  original_filename: string
  stored_filename: string
  file_path: string
  mime_type: string
  file_size: number
  extraction_status: string | null
  expense_id: number | null
  created_at: string
  updated_at: string
}
```

Adjust this completely to the real backend response.

Add typed upload and extraction responses if they differ:

```ts
ReceiptUploadResponse
ReceiptExtractionResponse
```

Do not use `any`.

---

# 3. Receipt API Module

Create:

```text
frontend/src/api/receiptApi.ts
```

Add:

```ts
getReceipts()
getReceiptById(receiptId)
uploadReceipt(file, onUploadProgress?)
extractReceipt(receiptId)
```

Use the existing Axios client.

---

## Upload Request

Use:

```text
multipart/form-data
```

Create a `FormData` object:

```ts
const formData = new FormData()
formData.append('file', file)
```

Confirm the exact backend form field name.

Do not manually set an invalid multipart boundary.

Let Axios/browser set the correct boundary.

---

## Upload Progress

If Axios upload progress works in the current setup, support a simple percentage:

```text
0–100%
```

If reliable progress is unavailable in tests or browser setup, use a clear loading state instead.

Do not add complex progress infrastructure.

---

# 4. Routes

Add protected routes:

```text
/receipts
/receipts/upload
/receipts/:id
```

Suggested route names:

```text
receipts
receipt-upload
receipt-detail
```

Use:

```ts
meta: { requiresAuth: true }
```

Register:

```text
/receipts/upload
```

before:

```text
/receipts/:id
```

so `upload` is not treated as an ID.

Add a route test.

---

# 5. Navigation

Update:

```text
AppLayout.vue
```

Add:

```text
Receipts
```

to the main navigation.

Keep:

```text
Dashboard
Expenses
Receipts
Current user email
Language switcher
Logout
```

Use `RouterLink`.

Add active-link styling using the existing approach.

---

# 6. Receipt List Page

Create:

```text
frontend/src/views/ReceiptListView.vue
```

On mount:

```text
Call getReceipts()
```

State:

```text
receipts
isLoading
error
```

Show only fields actually returned by the backend.

Possible display:

```text
Original file name
MIME/file type
File size
Upload date
Extraction status
Linked expense
View Details
```

Use simple cards or a responsive table.

Do not show fake receipt data.

---

## List Actions

Add:

```text
Upload Receipt
```

linking to:

```text
/receipts/upload
```

Each receipt should link to:

```text
/receipts/{id}
```

If `expense_id` exists, optionally include:

```text
Open Expense
```

linking to:

```text
/expenses/{expense_id}
```

---

# 7. Receipt List States

Loading:

```text
Loading receipts...
```

Empty:

```text
No receipts found.
Upload your first receipt to extract expense data.
```

Error:

```text
Unable to load receipts.
```

Include a Retry button if consistent with the expense list page.

Do not show raw errors.

---

# 8. Receipt Upload Page

Create:

```text
frontend/src/views/ReceiptUploadView.vue
```

Use a native file input.

Support only the real backend-allowed formats.

Expected formats may include:

```text
JPEG
PNG
WEBP
PDF
```

Confirm them from backend validation.

Set the input `accept` attribute accordingly.

---

# 9. File Validation

Validate before upload:

```text
A file is selected
Allowed MIME type
Allowed extension when useful
Maximum file size
File is not empty
```

Read the real maximum size from backend configuration or validation.

Do not invent a different frontend size limit.

Show inline validation messages.

Use SweetAlert2 only for important upload failure feedback.

---

# 10. Selected File Display

After selection, show:

```text
File name
File type
Human-readable file size
```

For image files:

```text
Show a local preview using URL.createObjectURL(file)
```

For PDF:

```text
Show a PDF file indicator
Do not embed a complex PDF viewer
```

Clean up object URLs when:

```text
file changes
component unmounts
```

Avoid memory leaks.

---

# 11. Upload Flow

Recommended flow:

```text
1. User selects a valid file
2. User clicks Upload and Extract
3. Upload receipt
4. Receive receipt result
5. Automatically call extractReceipt(receipt.id)
6. Receive extraction result
7. Determine created draft expense ID
8. Show success alert
9. Navigate to /expenses/{expense_id}/edit
```

Use one clear button:

```text
Upload and Extract
```

Disable it while uploading or extracting.

Prevent duplicate submissions.

---

# 12. Upload and Extraction States

Use simple states:

```text
idle
uploading
extracting
success
error
```

Display:

During upload:

```text
Uploading receipt...
```

During extraction:

```text
Analyzing receipt...
This may take a moment.
```

If progress is available:

```text
Uploading: 65%
```

Do not claim Gemini progress percentage because the backend does not provide it.

---

# 13. Extraction Response Handling

Inspect the real extraction response.

The backend may return:

```text
expense_id
```

or:

```text
expense: { id: ... }
```

or a draft response object.

Use the real structure.

After successful extraction, redirect to:

```text
/expenses/{expense_id}/edit
```

This lets the user review and correct AI-extracted values before confirmation.

If no expense ID is returned but the receipt response later includes it, fetch the receipt detail once and retrieve the linked expense ID.

Do not guess silently.

---

# 14. Receipt Detail Page

Create:

```text
frontend/src/views/ReceiptDetailView.vue
```

On mount:

```text
Validate route ID
Call getReceiptById()
```

Show actual receipt metadata:

```text
Original file name
MIME type
File size
Upload date
Updated date
Extraction status
Linked expense
```

Include:

```text
Back to Receipts
```

---

## Preview

If the backend exposes a safe file URL or download endpoint:

```text
Show image preview for images
Show Open/Download File link for PDFs
```

Use the real backend URL behavior.

Do not build a URL from a server filesystem path unless the backend explicitly serves that path.

Never expose internal filesystem paths to the user.

If no public preview endpoint exists:

```text
Show metadata only
Do not modify backend in this step unless preview is a required integration bug
```

---

# 15. Receipt Detail Actions

When no linked expense exists and extraction can run:

```text
Show Extract Receipt button
```

On click:

```text
Confirm or start extraction
Show extracting state
Call extractReceipt(id)
Show success alert
Navigate to draft expense edit page
```

When linked to an expense:

```text
Show Open Expense button
```

linking to:

```text
/expenses/{expense_id}
```

Do not allow repeated extraction if the backend forbids it.

Match backend rules.

---

# 16. SweetAlert2 Feedback

Use the existing alert helpers.

Use success alerts for:

```text
Receipt uploaded and extracted
Extraction completed
```

Use error alerts for:

```text
Upload failed
Extraction failed
Unsupported file
File too large
Gemini not configured
Gemini quota/service error
```

Keep validation inline for:

```text
No file selected
Wrong type
Too large
```

An error popup may also be used after a server rejection, but avoid duplicate messages.

---

# 17. Gemini Error Mapping

Inspect backend error messages/status codes.

Map common cases safely:

```text
Gemini API key missing
Gemini model unavailable
Quota exceeded
Service temporarily unavailable
Invalid receipt content
Extraction returned incomplete data
```

Show user-friendly messages.

Do not expose:

```text
API keys
Raw provider response
Stack traces
Internal exception names
```

Do not promise that all receipts can be extracted successfully.

---

# 18. Real Gemini Usage Warning

Real extraction may use Gemini free quota or paid usage.

Add a small fixed note on the upload page:

```text
AI extraction may use your configured Gemini API quota.
```

Translate it to Thai.

Do not show pricing claims.

Do not make Gemini calls automatically on page load.

Only call extraction after a user uploads or explicitly clicks Extract.

---

# 19. English and Thai Labels

Update:

```text
src/locales/en.json
src/locales/th.json
```

Add keys for:

```text
Receipts
Receipt Details
Upload Receipt
Upload and Extract
Select File
Choose File
Selected File
File Name
File Type
File Size
Upload Date
Extraction Status
Linked Expense
Open Expense
View Receipt
Back to Receipts
Loading Receipts
No Receipts Found
Unable to Load Receipts
Uploading Receipt
Upload Progress
Analyzing Receipt
Analysis May Take a Moment
Extract Receipt
Receipt Uploaded
Receipt Uploaded Message
Extraction Completed
Extraction Completed Message
Upload Failed
Extraction Failed
Unsupported File
File Too Large
No File Selected
Invalid File
Image Preview
PDF File
Open File
Download File
Not Extracted
Extracted
Processing
Failed
AI Quota Notice
Retry
```

Use natural Thai translations.

Use Vue I18n only for fixed UI labels.

Do not use Gemini to translate frontend labels.

---

# 20. Styling

Use existing CSS.

Add simple responsive styles for:

```text
Receipt list cards/table
Upload card
File input
Selected-file information
Image preview
Progress bar if used
Extraction status badges
Detail metadata
Action buttons
```

Do not add another UI framework.

Do not add a file upload library.

Do not heavily redesign the whole application.

---

# 21. Tests

Add focused tests.

Suggested files:

```text
src/api/receiptApi.test.ts
src/views/receipt.list.test.ts
src/views/receipt.upload.test.ts
src/views/receipt.detail.test.ts
```

Follow the current test style.

Test at least:

1. Receipt list API calls `/receipts`.
2. Receipt detail API calls `/receipts/{id}`.
3. Upload uses `FormData`.
4. Upload sends the correct form field name.
5. Extraction calls `/receipts/{id}/extract`.
6. `/receipts/upload` is not treated as `:id`.
7. Receipt list loading state.
8. Receipt list displays data.
9. Receipt list empty state.
10. Receipt list error state.
11. Upload page displays file input.
12. No-file validation.
13. Unsupported-type validation.
14. File-size validation.
15. Image preview is created.
16. Object URL is cleaned up.
17. PDF does not attempt image preview.
18. Upload button is disabled while busy.
19. Successful upload starts extraction.
20. Successful extraction redirects to expense edit.
21. Upload failure shows safe error alert.
22. Extraction failure shows safe error alert.
23. Gemini configuration error is mapped safely.
24. Receipt detail loads valid route ID.
25. Invalid route ID is handled.
26. Receipt detail shows linked expense action.
27. Receipt detail shows extract action when appropriate.
28. Existing 116 tests remain green.
29. No test makes a real Gemini request.
30. English/Thai labels render correctly.

Mock:

```text
Axios/API calls
SweetAlert2 helpers
Router navigation
URL.createObjectURL
URL.revokeObjectURL
```

Never call real Gemini in tests.

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

Open:

```text
http://localhost:5173
```

Verify:

```text
Login
Open Receipts
See empty or real receipt list
Open Upload Receipt
Select valid image
See image preview
Upload and extract
See upload state
See extraction state
Open draft expense edit page
Review extracted fields
Return to receipt list
Open receipt detail
Open linked expense
Switch English/Thai
```

Also test:

```text
Unsupported file
Oversized file
No file selected
Backend stopped
Gemini key missing, if using a safe development configuration
```

Be careful: a successful real extraction can consume Gemini quota.

---

# 23. Backend Regression Check

No backend changes are expected.

If a real backend mismatch requires a backend change:

```bash
cd backend
source venv/bin/activate
pytest
```

Otherwise, leave backend behavior unchanged.

---

# 24. Build Verification

Run:

```bash
npm run test
npm run build
```

The TypeScript build must finish with zero errors.

---

# Do Not Implement Yet

Do not implement:

- AI expense confirmation
- Dynamic English/Thai expense translation
- Excel export
- Receipt editing
- Receipt deletion UI
- Receipt restore
- Permanent deletion
- Search
- Filters
- Pagination
- Dashboard statistics
- Camera integration
- Drag-and-drop library
- PDF viewer library

---

# Expected Result

After this step:

- Protected receipt list
- Protected receipt upload page
- Protected receipt detail page
- Native file selection and validation
- Image preview
- Multipart receipt upload
- Automatic Gemini extraction
- Extraction status feedback
- Redirect to draft expense edit page
- SweetAlert2 success/error feedback
- English/Thai fixed labels
- Focused tests with mocked Gemini calls
- Clean production build

---

# Required Completion Report

Provide:

1. Changed and created files
2. Real receipt response fields confirmed
3. Receipt types
4. API functions
5. Routes and navigation
6. Receipt list behavior
7. Upload validation
8. Preview behavior
9. Upload request behavior
10. Extraction response behavior
11. Redirect behavior
12. Receipt detail behavior
13. Gemini error mapping
14. SweetAlert2 behavior
15. English/Thai changes
16. Tests and result
17. Build result
18. Manual verification result
19. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
