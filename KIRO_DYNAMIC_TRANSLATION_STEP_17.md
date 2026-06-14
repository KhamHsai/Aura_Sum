# Smart Receipt Project — Step 17: On-Demand English–Thai Translation for Live Expense Data

## Goal

Implement backend translation for dynamic expense data only.

Create:

```text
POST /api/expenses/{expense_id}/translate
```

This endpoint must translate live user or receipt data between:

```text
English → Thai
Thai → English
```

The translation must happen only when the user requests it.

This feature is not for fixed frontend labels.

Fixed UI text such as:

```text
Dashboard
Save
Delete
Upload Receipt
Expenses
```

will later be translated in the frontend using normal language files such as:

```text
en.json
th.json
```

Do not use Gemini for fixed frontend labels.

Write simple, human-readable code that is easy to understand and explain. Use clear names and straightforward logic. Avoid unnecessary abstractions, complex design patterns, generic AI frameworks, and overengineering.

---

## Project Status

The project already has:

- FastAPI, MySQL, SQLAlchemy, Alembic, and Pydantic
- Authentication and current-user dependency
- Protected category endpoints
- Receipt upload, list, detail, soft delete, link, unlink, and Gemini extraction
- Expense create, list, detail, update, soft delete, and confirm
- English and Thai receipt extraction
- Gemini configuration and client
- Expense items with `name_en` and `name_th`
- A database translation model/table may already exist
- 510 tests passing

Inspect the existing files before changing anything:

```text
Translation model and migration
Expense model
ExpenseItem model
Expense schemas
Gemini service
Expense service
Expense routes
Existing tests
```

Do not rebuild completed features.

---

# Scope

Implement only:

```text
Translation request and response schemas
Gemini translation service
POST /api/expenses/{expense_id}/translate
Ownership validation
English/Thai validation
Dynamic expense text translation
Item-name translation
Reuse of existing saved translations where possible
One database transaction for saved changes
Fully mocked tests
```

Do not implement:

```text
Frontend en.json or th.json files
Fixed UI-label translation
Excel export
Re-extraction
Background translation jobs
Batch translation
Translation of every expense automatically
New database tables without approval
```

---

# Important Translation Design

There are two separate translation systems.

## Fixed frontend text

Examples:

```text
Dashboard
Save
Cancel
Delete
Upload Receipt
```

These belong in frontend language files.

They must not call Gemini.

## Dynamic live data

Examples:

```text
Expense title
Expense notes
Receipt item names
Text entered by the user
Text extracted from receipts
```

These are translated by this backend endpoint using Gemini.

The endpoint must not be called automatically every time a page loads.

The frontend will call it only when the user clicks something such as:

```text
Translate to English
Translate to Thai
```

---

# 1. Endpoint

Create:

```text
POST /api/expenses/{expense_id}/translate
```

Swagger summary:

```text
Translate Expense
```

Success status:

```text
200 OK
```

The route must require authentication.

Use:

```python
db: Session = Depends(get_db)
current_user: User = Depends(get_current_user)
```

Keep the route thin.

The route should only:

```text
1. Call the translation service
2. Convert service errors to HTTPException
3. Return the validated response
```

Do not place Gemini calls or SQLAlchemy queries directly in the route.

---

# 2. Request Schema

Create a simple request schema:

```python
class ExpenseTranslationRequest(BaseModel):
    target_language: Literal["en", "th"]
```

Accept only:

```text
en
th
```

Normalize simple uppercase forms if helpful:

```text
EN → en
TH → th
```

Reject all other values with `422`.

Do not support Myanmar or other languages.

---

# 3. Response Schema

Create a clear response schema similar to:

```python
class TranslatedExpenseItem(BaseModel):
    item_id: int
    original_name: str | None = None
    name_en: str | None = None
    name_th: str | None = None
    translated_name: str | None = None


class ExpenseTranslationResponse(BaseModel):
    expense_id: int
    source_language: Literal["en", "th"]
    target_language: Literal["en", "th"]
    translated_title: str | None = None
    translated_notes: str | None = None
    items: list[TranslatedExpenseItem] = []
    reused_existing_translation: bool = False
```

Adjust names only if the existing project already has suitable translation schemas.

Do not return local file paths, API keys, deleted fields, or raw provider objects.

---

# 4. Existing Translation Model

Inspect the existing translation model/table before writing code.

If it already supports saving translations for expense fields, reuse it.

Possible useful fields may include:

```text
expense_id
field_name
source_language
target_language
original_text
translated_text
created_at
updated_at
```

Use the real existing fields only.

Do not create a duplicate translation table.

Do not create an Alembic migration in this task unless the current translation model is genuinely unusable.

If the existing translation model cannot safely support this feature:

```text
Stop before changing the schema
Report the exact mismatch
Do not create a surprise migration
```

Expense-item translations should use existing:

```text
ExpenseItem.name_en
ExpenseItem.name_th
```

when possible.

---

# 5. Ownership and Availability

Find the expense using:

```text
Expense.id == expense_id
Expense.user_id == user_id
Expense.deleted_at is null
```

For a missing, other-user, or soft-deleted expense, return:

```text
404 Expense not found
```

Do not return `403`.

Only include active items:

```text
ExpenseItem.deleted_at is null
```

---

# 6. Source Language

Use the expense's existing:

```text
language_detected
```

Allowed source languages:

```text
en
th
```

If `language_detected` is missing or unsupported, use a simple fallback:

```text
Infer from the requested target:
target th → source en
target en → source th
```

Do not add automatic language detection libraries.

If source and target are the same, do not call Gemini.

Return existing text safely.

---

# 7. Fields to Translate

Translate only dynamic text fields.

## Expense fields

Translate:

```text
title
notes
```

Merchant name may be preserved unchanged by default.

Do not translate merchant names unless the existing product requirement clearly needs it.

## Expense-item fields

Translate item names.

For target `en`:

```text
Set or return `name_en`
Keep `name_th`
Keep `original_name`
```

For target `th`:

```text
Set or return `name_th`
Keep `name_en`
Keep `original_name`
```

Use the best source text in this order.

For target English:

```text
name_th
original_name
name_en
```

For target Thai:

```text
name_en
original_name
name_th
```

Do not translate:

```text
receipt_number
receipt_date
receipt_time
currency
subtotal
tax_amount
discount_amount
total_amount
payment method codes
category IDs
user IDs
receipt links
```

---

# 8. Reuse Existing Translations

Avoid unnecessary Gemini calls.

Before translating:

```text
1. Check whether the requested translation already exists
2. Reuse it when available
3. Do not call Gemini again for unchanged text
```

For items:

```text
target en and name_en already exists → reuse it
target th and name_th already exists → reuse it
```

For expense title and notes:

```text
reuse matching records from the existing translation table
```

Set:

```text
reused_existing_translation = true
```

when no Gemini call was needed.

If only some fields already exist, call Gemini only for missing translations.

Keep the logic simple.

---

# 9. Gemini Translation Service

Add a small function such as:

```python
def translate_expense_text(
    source_language: str,
    target_language: str,
    title: str | None,
    notes: str | None,
    items: list[dict],
) -> ValidatedTranslationResult:
    ...
```

An async function is acceptable only if required by the existing Gemini SDK style.

Reuse the existing Gemini client/configuration.

Do not duplicate API-key handling.

Do not build a generic LLM-provider framework.

---

# 10. Gemini Prompt

The prompt must clearly say:

```text
Translate only the provided text.
Source and target languages are English and Thai only.
Return JSON only.
Do not include Markdown or code fences.
Preserve meaning.
Do not add information.
Do not change numbers, currency, dates, IDs, or codes.
Use null when source text is null.
Keep the same item order.
```

Request structured output similar to:

```json
{
  "translated_title": null,
  "translated_notes": null,
  "items": [
    {
      "item_id": 1,
      "translated_name": null
    }
  ]
}
```

Do not send unnecessary database fields to Gemini.

Do not send:

```text
user_id
API key
file path
receipt binary
monetary fields
AI raw response
```

---

# 11. Translation Result Validation

Create Pydantic schemas for Gemini translation output.

Validate:

```text
item IDs match requested items
no extra item IDs are returned
item order or mapping remains correct
translated fields are strings or null
```

Do not trust an unvalidated Gemini dictionary.

Small defensive JSON-fence cleaning is acceptable.

Do not write a complex response-repair engine.

---

# 12. Saving Translation Results

Save only validated translations.

## Expense title and notes

Use the existing translation table if compatible.

Save or update translations using a simple uniqueness rule such as:

```text
expense_id + field_name + target_language
```

Use the real existing model constraints.

Do not overwrite the original Expense.title or Expense.notes unless the current design explicitly requires it.

The original expense text should remain available.

## Expense item names

For target English:

```text
item.name_en = translated_name
```

For target Thai:

```text
item.name_th = translated_name
```

Do not overwrite the other language field.

Do not overwrite `original_name`.

---

# 13. Transaction

All saved translation changes must succeed together.

Use one transaction for:

```text
Expense title translation records
Expense notes translation records
ExpenseItem name updates
```

If any database write fails:

```text
rollback everything
keep existing translations unchanged
```

Do not commit inside an item loop.

A Gemini failure before database writes must leave the database unchanged.

---

# 14. Error Handling

Reuse or create one lightweight translation service error.

Suggested behavior:

```text
404 Expense not found
422 Unsupported target language
422 Expense language is unsupported
502 Gemini translation failed
502 Gemini returned invalid JSON
502 Gemini translation validation failed
```

A missing Gemini API key may preserve the existing Gemini error status.

Do not expose provider secrets or full provider errors.

Do not raise `HTTPException` inside the service.

---

# 15. Tests Must Be Mocked

No automated test may call the real Gemini API.

Patch the Gemini translation function or client boundary.

No network requests.

No real API-key requirement.

---

# 16. Schema Tests

Test at least:

1. Request accepts `en`.
2. Request accepts `th`.
3. Uppercase language normalizes if supported.
4. Unsupported language is rejected.
5. Valid translation response is accepted.
6. Empty item list is accepted.
7. Invalid item ID mapping is rejected.
8. Extra item IDs are rejected.
9. Missing required response structure is rejected.
10. English and Thai values remain separate.

---

# 17. Service Tests

Test at least:

1. English expense translates to Thai.
2. Thai expense translates to English.
3. Expense title is translated.
4. Expense notes are translated.
5. Item names are translated.
6. Target English saves `name_en`.
7. Target Thai saves `name_th`.
8. `original_name` remains unchanged.
9. Existing opposite-language name remains unchanged.
10. Merchant name remains unchanged.
11. Money fields remain unchanged.
12. Category remains unchanged.
13. Receipt link remains unchanged.
14. Missing expense returns `404`.
15. Other user's expense returns `404`.
16. Soft-deleted expense returns `404`.
17. Soft-deleted items are excluded.
18. Unsupported target language returns `422`.
19. Same source and target avoids Gemini.
20. Existing item translations are reused.
21. Existing title/notes translations are reused.
22. Partial existing translations call Gemini only for missing fields.
23. Gemini failure writes nothing.
24. Invalid Gemini JSON writes nothing.
25. Invalid item mapping writes nothing.
26. Database failure rolls back all changes.
27. No real Gemini call occurs.

Use `smart_receipt_db_test`.

---

# 18. Route Tests

Test at least:

1. Authenticated user can translate an owned expense.
2. Success returns `200`.
3. English-to-Thai response is correct.
4. Thai-to-English response is correct.
5. Translated title is returned.
6. Translated notes are returned.
7. Translated items are returned.
8. Missing expense returns `404`.
9. Other user's expense returns `404`.
10. Soft-deleted expense returns `404`.
11. Unsupported language returns `422`.
12. Missing token returns `401`.
13. Invalid token returns `401`.
14. Existing translation is reused.
15. No fixed frontend labels are translated.
16. No monetary data changes.
17. Internal fields are not exposed.
18. No real Gemini call occurs.
19. Existing full test suite remains green.

---

# 19. Verification Commands

Run from the backend folder:

```bash
python -m compileall app tests
```

Run translation schema tests:

```bash
pytest tests/test_translation_schemas.py
```

Run translation service tests:

```bash
pytest tests/test_translation_service.py
```

Run expense route tests:

```bash
pytest tests/test_expense_routes.py
```

Run the full suite:

```bash
pytest
```

Confirm that no test contacts Gemini.

Optionally verify in Swagger:

```text
POST /api/expenses/{expense_id}/translate
```

Example request:

```json
{
  "target_language": "th"
}
```

---

# Do Not Implement Yet

Do not implement:

- Frontend `en.json` or `th.json`
- Fixed UI-label translation
- Excel export
- Batch translation
- Automatic translation on page load
- Translation of all expenses
- Background jobs
- New translation tables without approval
- Frontend pages

---

# Expected Result

After this step, the backend should have:

- On-demand English–Thai translation
- Dynamic expense-title and notes translation
- Expense-item name translation
- Strict ownership checks
- Reuse of saved translations
- No unnecessary Gemini calls
- Fully mocked tests
- No fixed frontend translation
- No Excel export yet

---

# Required Completion Report

Provide:

1. Changed file list
2. Translation schemas added
3. Service function added
4. Route added
5. Existing translation model usage
6. Source and target language behavior
7. Fields translated
8. Fields intentionally not translated
9. Existing-translation reuse behavior
10. Gemini prompt and structured parsing approach
11. Database save behavior
12. Transaction and rollback behavior
13. Schema test result
14. Service test result
15. Route test result
16. Full test-suite result
17. Confirmation that no real Gemini calls were made
18. Any translation-model or schema mismatch found

Do not produce a long walkthrough unless an error occurs.
