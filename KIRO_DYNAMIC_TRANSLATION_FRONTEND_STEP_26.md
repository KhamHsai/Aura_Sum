# Smart Receipt Project — Step 26: Dynamic English–Thai Expense Translation UI

## Goal

Add the frontend flow for translating dynamic expense data between English and Thai using the existing backend translation endpoint.

Connect to:

```text
POST /api/expenses/{expense_id}/translate
```

Expected flow:

```text
Open expense detail
→ Choose English or Thai
→ Click Translate Expense
→ Backend uses Gemini translation
→ Show translated expense data
→ Keep original values visible
```

This feature is different from Vue I18n:

```text
Vue I18n
→ translates fixed frontend labels and buttons

Backend translation endpoint
→ translates dynamic expense data such as titles, merchant names, notes, and item names
```

Write simple, human-readable Vue and TypeScript code that is easy to understand and explain.

Use clear names and straightforward logic.

Avoid unnecessary abstractions, translation stores, automatic translation workflows, and overengineering.

---

## Current Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list, detail, create, edit, delete, and confirmation
- SweetAlert2 helpers
- Receipt upload and Gemini extraction
- 222 frontend tests passing
- Clean production build
- Complete FastAPI backend with dynamic translation endpoint

Inspect the real backend translation request and response schemas before changing anything.

Do not rebuild existing features.

Do not change backend code unless a real integration mismatch is found.

---

# Scope

Implement only:

```text
Translation request and response types
Translation API function
Translation controls on expense detail page
Target language selection
Translation loading state
Translated expense display
Translated item-name display
Original data preserved
SweetAlert2 success/error feedback
English/Thai fixed labels
Focused frontend tests
Clean production build
```

Do not implement:

```text
Excel export
Search
Filters
Pagination
Dashboard statistics
Automatic translation on page load
Bulk translation
Translation history management
Translation editing
Translation deletion
```

---

# Important Coding Style

1. Write simple, human-readable code.
2. Match the backend translation schemas exactly.
3. Keep API calls inside `src/api`.
4. Reuse existing SweetAlert2 helpers.
5. Use Vue I18n for fixed labels only.
6. Keep translated state inside the expense detail view unless the backend response clearly updates the main expense object.
7. Do not add a translation Pinia store.
8. Do not automatically translate.
9. Do not hide original data.
10. Mock all Gemini-related calls in tests.

---

# 1. Inspect Real Backend Translation Behavior

Before coding, inspect:

```text
POST /api/expenses/{expense_id}/translate
```

Confirm:

```text
Request body fields
Allowed target-language values
Response shape
Whether translation is saved in the database
Whether the response contains:
- translated title
- translated merchant name
- translated notes
- translated item names
- source language
- target language
- translation ID
Behavior when already translated
Behavior for manual and AI expenses
Behavior when expense has no items
Error status codes
```

Do not guess.

Match the real backend behavior exactly.

---

# 2. Translation Types

Update:

```text
frontend/src/types/expense.ts
```

or create:

```text
frontend/src/types/translation.ts
```

Choose the simpler structure based on the real response.

Possible interfaces:

```ts
export type TranslationLanguage = 'en' | 'th'

export interface ExpenseTranslationRequest {
  target_language: TranslationLanguage
}
```

Possible translated item type:

```ts
export interface TranslatedExpenseItem {
  item_id: number
  original_name: string | null
  translated_name: string | null
  name_en: string | null
  name_th: string | null
}
```

Possible response type:

```ts
export interface ExpenseTranslationResponse {
  expense_id: number
  source_language: string | null
  target_language: TranslationLanguage
  translated_title: string | null
  translated_merchant_name: string | null
  translated_notes: string | null
  items: TranslatedExpenseItem[]
}
```

Adjust fully to the real backend response.

Do not use `any`.

Do not duplicate fields unnecessarily.

---

# 3. Translation API Function

Update:

```text
frontend/src/api/expenseApi.ts
```

Add:

```ts
translateExpense(
  expenseId: number,
  targetLanguage: 'en' | 'th'
)
```

Connect to:

```text
POST /api/expenses/{expense_id}/translate
```

Use the exact request body from the backend schema.

Likely request:

```json
{
  "target_language": "th"
}
```

or:

```json
{
  "target_language": "en"
}
```

Return the typed translation response.

Do not navigate inside the API module.

Do not duplicate token logic.

---

# 4. Translation Controls on Expense Detail

Update:

```text
frontend/src/views/ExpenseDetailView.vue
```

Add a new section:

```text
Translate Expense
```

Include:

```text
Target Language
English
Thai
Translate Expense button
```

Use a simple select or radio buttons.

Recommended default:

```text
If current frontend locale is "th" → target = "th"
Otherwise → target = "en"
```

Still allow the user to change the target manually.

Do not automatically start translation when the page loads.

---

# 5. Translation State

Use simple local state:

```text
targetLanguage
isTranslating
translationResult
translationError
```

Behavior:

```text
Before request:
- clear old translation error
- set loading state

On success:
- save response in translationResult
- show success alert

On failure:
- keep original expense visible
- show safe error alert
- allow retry
```

Disable the translate button while a request is active.

Prevent duplicate translation requests.

---

# 6. Translation Loading State

While translating, show:

```text
Translating...
This may take a moment.
```

Do not display fake progress percentages.

Do not block the whole page if not necessary.

The user should still be able to see the original expense data.

---

# 7. Original and Translated Expense Display

Keep original values visible.

Suggested layout:

```text
Original
Translated
```

For supported fields, show:

```text
Title
Merchant Name
Notes
```

Example:

```text
Original Title:
ค่าอาหารกลางวัน

Translated Title:
Lunch Expense
```

If a translated field is null or missing:

```text
Not available
```

Do not replace the original expense object silently.

Do not hide the original receipt text.

---

# 8. Translated Item Display

For each expense item, show:

```text
Original Name
English Name
Thai Name
Translated Name
```

Use the real translation response.

If the backend saves translations into:

```text
name_en
name_th
```

then display those updated values clearly.

If it returns separate translated fields, display them from the translation response.

Keep item matching reliable using:

```text
item_id
```

or the real backend identifier.

Do not match items only by array index if a real item ID is available.

---

# 9. Existing Translation Data

Inspect whether `GET /api/expenses/{id}` already returns saved translation fields.

If yes:

```text
Display existing English/Thai values when the detail page loads
```

If no:

```text
Display only the result returned from the current translation request
```

Do not invent translation history.

Do not add extra API calls unless required.

---

# 10. Target Language Rules

Support only backend-approved values:

```text
en
th
```

Do not allow arbitrary language input.

If the expense is already mainly in the selected target language:

```text
Still allow the request if the backend permits it
```

Do not create unsupported frontend restrictions.

Let the backend remain the final validator.

---

# 11. SweetAlert2 Feedback

Use existing alert helpers.

Success:

```text
Translation completed
The expense translation was generated successfully.
```

Failure:

```text
Unable to translate expense
Please try again later.
```

Use safe mapped messages for common backend errors.

Do not show raw provider responses.

Do not expose Gemini model names, API keys, stack traces, or internal exceptions.

---

# 12. Gemini Error Mapping

Inspect backend status codes and messages.

Map safely:

```text
503 → Gemini is not configured
429 → Gemini quota exceeded
400 or 422 → invalid translation request
404 → expense not found
409 → translation conflict, if used
500/network → translation service unavailable
```

Suggested user-friendly messages:

```text
Gemini is not configured.
Translation quota has been reached.
The selected language is not supported.
Unable to translate this expense right now.
```

If backend returns a safe short detail string, it may be reused.

Hide long or suspicious strings.

---

# 13. Real Gemini Usage Notice

Add a small note in the translation section:

```text
AI translation may use your configured Gemini API quota.
```

Translate it to Thai.

Do not make pricing claims.

Do not call translation automatically.

Only call after the user clicks the translate button.

---

# 14. English and Thai Fixed Labels

Update:

```text
frontend/src/locales/en.json
frontend/src/locales/th.json
```

Add keys for:

```text
Translate Expense
Target Language
Translate
Translating
Translation May Take a Moment
Translation Completed
Translation Completed Message
Unable to Translate Expense
Original
Translated
Original Title
Translated Title
Original Merchant
Translated Merchant
Original Notes
Translated Notes
Translated Name
Source Language
English
Thai
Select Language
Unsupported Language
Translation Service Unavailable
Gemini Not Configured
Gemini Quota Exceeded
AI Translation Quota Notice
No Translation Available
Retry Translation
```

Use natural Thai translations.

Do not hard-code alert strings inside components.

---

# 15. Styling

Use existing CSS.

Add simple styles for:

```text
Translation section
Target-language controls
Original/translated comparison grid
Translated item block
Loading state
Responsive mobile layout
```

Do not add another UI framework.

Do not redesign the entire expense detail page.

Keep the original expense section visually distinct from translated data.

---

# 16. Tests

Add focused frontend tests.

Suggested files:

```text
src/api/expense.translation.test.ts
src/views/expense.translation.test.ts
```

Or follow the current test organization.

Test at least:

1. Translation API calls `POST /expenses/{id}/translate`.
2. English target sends `target_language: "en"`.
3. Thai target sends `target_language: "th"`.
4. Translation uses the existing Axios client.
5. No translation request occurs on page mount.
6. Translation controls appear on expense detail.
7. Default target follows current frontend locale.
8. User can change target language.
9. Translate button starts request.
10. Button is disabled while translating.
11. Loading message is shown.
12. Success result is stored.
13. Success alert is shown.
14. Original title remains visible.
15. Translated title is displayed.
16. Original merchant remains visible.
17. Translated merchant is displayed.
18. Original notes remain visible.
19. Translated notes are displayed.
20. Translated item names are displayed.
21. Items are matched by real item ID where available.
22. Missing translated fields show safe fallback.
23. 503 maps to Gemini not configured.
24. 429 maps to quota exceeded.
25. Invalid target language is handled safely.
26. Network failure shows safe error alert.
27. Failure keeps original expense visible.
28. Duplicate translation requests are prevented.
29. English labels render.
30. Thai labels render.
31. Existing 222 tests remain green.
32. No test makes a real Gemini request.

Mock:

```text
Translation API
SweetAlert2 helpers
Expense detail API
Router where needed
```

Never call real Gemini in unit tests.

---

# 17. Manual Verification

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
Open an expense detail page
See Translate Expense section
Choose Thai
Click Translate
See loading state
See success alert
See original and translated fields
See translated item names
Choose English
Translate again
Switch frontend language
Confirm fixed labels change
Refresh page
Check saved translation behavior according to backend
```

Also test:

```text
Gemini key missing
Quota error if safely reproducible
Backend stopped
Invalid expense ID
Expense with no notes
Expense with no items
```

Real translation may consume Gemini quota.

---

# 18. Backend Regression Check

No backend changes are expected.

If a real mismatch requires backend changes:

```bash
cd backend
source venv/bin/activate
pytest
```

Otherwise, leave backend code unchanged.

---

# 19. Build Verification

Run:

```bash
npm run test
npm run build
```

The TypeScript build must finish with zero errors.

---

# Do Not Implement Yet

Do not implement:

- Excel export
- Dashboard statistics
- Search
- Filters
- Pagination
- Translation history
- Translation editing
- Translation deletion
- Bulk translation
- Automatic translation
- Additional languages

---

# Expected Result

After this step:

- Dynamic English/Thai translation API integration
- Target-language controls
- Translation loading state
- Original values preserved
- Translated expense fields displayed
- Translated item names displayed
- Safe Gemini error mapping
- SweetAlert2 success/error feedback
- English/Thai fixed labels
- Focused tests with mocked translation calls
- Clean production build

---

# Required Completion Report

Provide:

1. Changed and created files
2. Real backend translation request and response
3. Translation types
4. API function
5. Translation controls
6. Default target-language behavior
7. Loading behavior
8. Original/translated display behavior
9. Item translation behavior
10. Existing saved translation behavior
11. Gemini error mapping
12. SweetAlert2 behavior
13. English/Thai fixed-label changes
14. Tests and result
15. Build result
16. Manual verification result
17. Any backend/frontend mismatch

Do not produce a long walkthrough unless an error occurs.
