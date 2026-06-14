# Smart Receipt Project — Step 15B: Extract Receipt, Create Draft Expense, and Link Receipt

## Goal

Implement the protected receipt extraction endpoint:

```text
POST /api/receipts/{receipt_id}/extract
```

This endpoint must:

```text
1. Verify receipt ownership
2. Verify the receipt is active
3. Verify the physical file exists
4. Call the existing Gemini extraction service
5. Create a draft Expense
6. Create nested ExpenseItem rows
7. Link the receipt to the new expense
8. Commit everything in one transaction
9. Return ExpenseResponse
```

Keep the code simple, human-readable, and easy to understand and explain.

Avoid unnecessary abstractions, complex patterns, generic frameworks, and overengineering.

Do not implement confirmation, standalone translation, Excel export, background jobs, or frontend code yet.

---

## Project Status

The project already has:

- FastAPI, MySQL, SQLAlchemy, Alembic, and Pydantic
- Authentication and current-user dependency
- Protected category endpoints
- Receipt upload, list, detail, soft delete, link, and unlink
- Expense create, list, detail, update, and soft delete
- Gemini configuration
- English/Thai extraction schemas
- Gemini extraction service
- Mocked Gemini tests
- 415 tests passing

Inspect the existing files before changing anything:

```text
ReceiptFile model
Expense model
ExpenseItem model
Category model
Receipt schemas
Expense schemas
AI extraction schemas
Gemini service
Expense service
Receipt routes
Existing tests
```

Do not rebuild completed features.

---

# Scope

Implement only:

```text
POST /api/receipts/{receipt_id}/extract
Receipt ownership and file validation
Calling extract_receipt_data()
Simple category-name matching
Draft Expense creation
ExpenseItem creation
Receipt linking
One database transaction
Mocked route and service tests
```

Do not implement:

```text
Confirm endpoint
Re-extraction
Standalone translation endpoint
English–Thai translation service
Excel export
Background processing
Automatic category creation
Frontend code
```

---

# Important Coding Style

Follow these rules:

1. Write simple, human-readable code.
2. Make the code easy for a student to understand and explain.
3. Use clear function and variable names.
4. Keep route functions thin.
5. Put database and business logic in the service layer.
6. Reuse existing schemas and helper functions.
7. Do not add service classes.
8. Do not add repository classes.
9. Do not add generic AI frameworks.
10. Do not add unnecessary helper layers.
11. Use one database transaction.
12. Roll back everything on failure.
13. Keep Gemini tests fully mocked.
14. Never use a real API request in automated tests.

---

# Suggested Files

Update only what is needed:

```text
backend/app/services/receipt_service.py
backend/app/services/expense_service.py
backend/app/services/__init__.py

backend/app/routes/receipts.py

backend/tests/test_receipt_extraction_service.py
backend/tests/test_receipt_routes.py
```

If extraction logic fits more naturally in an existing receipt service, use that.

Do not create duplicate or unnecessarily separated service files.

---

# 1. Public Endpoint

Create:

```text
POST /api/receipts/{receipt_id}/extract
```

Swagger summary:

```text
Extract Receipt Data
```

Success response:

```text
201 Created
```

Response model:

```text
ExpenseResponse
```

The returned expense must include nested items.

The route must require:

```python
db: Session = Depends(get_db)
current_user: User = Depends(get_current_user)
```

The route should only:

```text
1. Call the service
2. Convert service errors to HTTPException
3. Return the created expense
```

Do not put SQLAlchemy queries or Gemini logic directly in the route.

---

# 2. Main Service Function

Create a function similar to:

```python
def extract_receipt_to_draft_expense(
    db: Session,
    user_id: int,
    receipt_id: int,
) -> ExpenseResponse:
    ...
```

An async version is acceptable only if required by the existing Gemini service.

Choose the simplest style consistent with the project.

---

# 3. Receipt Validation

Before calling Gemini, find the receipt using all of these rules:

```text
ReceiptFile.id == receipt_id
ReceiptFile.user_id == user_id
ReceiptFile.deleted_at is null
```

If the receipt:

```text
does not exist
belongs to another user
is soft-deleted
```

raise:

```text
404 Receipt not found
```

Do not return `403`.

Do not reveal another user's receipt.

---

# 4. Existing Expense Link Check

If:

```text
receipt.expense_id is not null
```

reject extraction with:

```text
409 Receipt is already linked to an expense
```

Do not automatically overwrite or reassign the existing link.

Do not create another expense.

---

# 5. Physical File Validation

Use the stored receipt path safely.

Confirm:

```text
The file path exists
The file is a regular file
The MIME type is supported
```

If the file is missing, return:

```text
404 Receipt file not found
```

Do not expose the local file path in the response.

Do not log full file contents.

Do not use OCR libraries.

---

# 6. Call Existing Gemini Service

Reuse:

```python
extract_receipt_data(file_path, mime_type)
```

Do not duplicate Gemini prompt or parsing logic.

The existing Gemini service already handles:

```text
English and Thai only
Structured JSON
Decimal validation
Currency normalization
Provider errors
Invalid JSON
Schema validation
```

Propagate `GeminiServiceError` safely.

Do not convert Gemini errors into generic 500 errors unless unexpected.

---

# 7. Category Matching

Gemini returns:

```text
category_name
```

It does not return database IDs.

Use a simple category matching function.

Recommended behavior:

```text
1. Trim category_name
2. Compare case-insensitively
3. Match only categories where:
   is_active = true
   deleted_at is null
4. If matched, use category.id
5. If not matched, use None
```

Do not create categories automatically.

Do not use fuzzy matching.

Do not use embeddings.

Do not call Gemini again for category matching.

Use the same simple logic for:

```text
Main expense category
Each expense-item category
```

If the extracted receipt does not provide a main category name, use:

```text
category_id = None
```

If the current `ExtractedReceiptData` schema has no main `category_name`, keep the expense category as `None`.

---

# 8. Create Draft Expense

Create an Expense using validated extracted data.

Map fields where available:

```text
user_id
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
language_detected
ai_confidence
```

Use model fields only if they actually exist.

Set draft/AI fields using existing model values:

```text
input_method = "ai"
ai_status = "completed"
is_confirmed = false
```

Use exact enum/string values already supported by the project.

Do not invent incompatible values.

Do not allow Gemini to set:

```text
user_id
id
created_at
updated_at
deleted_at
```

---

# 9. Title Fallback

If Gemini does not return a useful title, use a simple fallback:

```text
merchant_name
```

If merchant name is also missing, use:

```text
Extracted Receipt
```

Do not create a complicated title-generation system.

---

# 10. Create Expense Items

For every validated extracted item, create an `ExpenseItem`.

Map fields where available:

```text
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
```

Use `None` when optional values are unavailable.

Do not create an item if all name fields are empty after validation.

Do not calculate missing prices unless the project already has a clear business rule.

Do not overwrite Gemini values with invented numbers.

---

# 11. English and Thai Rules

The project supports only:

```text
en
th
```

Preserve:

```text
language_detected
name_en
name_th
```

Do not add Myanmar language support.

Do not create the standalone translation feature in this step.

Gemini-provided `name_en` and `name_th` may be saved when available.

---

# 12. AI Raw Response

Inspect the existing Expense model.

If `ai_raw_response` exists, storing a JSON-safe version of the validated extraction result is acceptable.

Use:

```python
extracted.model_dump(mode="json")
```

or the project's equivalent.

Do not store:

```text
API key
local file path
provider client object
binary file content
```

If storing the raw validated result adds unnecessary complexity, leave `ai_raw_response` as `None`.

Choose the simplest safe behavior and explain it in the completion report.

---

# 13. Transaction Requirements

These actions must succeed together:

```text
Create Expense
Create ExpenseItem rows
Set receipt.expense_id
```

Use one transaction.

Recommended process:

```text
1. Validate receipt and file
2. Call Gemini
3. Match categories
4. Create Expense
5. Flush to obtain expense.id
6. Create ExpenseItems
7. Set receipt.expense_id = expense.id
8. Commit once
9. Refresh required objects
10. Return ExpenseResponse
```

If anything fails after database changes begin:

```text
db.rollback()
```

After rollback:

```text
No expense remains
No expense items remain
Receipt remains unlinked
```

Do not commit inside an item loop.

---

# 14. Gemini Failure Behavior

If Gemini fails:

```text
Do not create an Expense
Do not create ExpenseItems
Do not link the receipt
```

Preserve the error status from `GeminiServiceError`.

Examples:

```text
503 Gemini API key is not configured
415 Unsupported receipt file type
502 Gemini extraction failed
502 Gemini returned invalid JSON
502 Gemini response validation failed
```

Do not expose sensitive provider details.

---

# 15. Concurrent or Duplicate Extraction

Before extraction, check:

```text
receipt.expense_id is null
```

After Gemini returns and before committing, ensure the receipt is still unlinked if practical within the current transaction style.

Keep the solution simple.

Do not add distributed locks or job queues.

A second extraction request for an already-linked receipt must return:

```text
409 Receipt is already linked to an expense
```

---

# 16. Response Construction

Return:

```text
ExpenseResponse
```

Include:

```text
Nested active ExpenseItems
AI fields only if ExpenseResponse already safely exposes them
No deleted_at
No local file path
No API key
```

Reuse the existing response-building helper if available.

Do not create duplicate serialization logic unless necessary.

---

# 17. Service Errors

Use a small existing service exception if possible.

Suggested messages:

```text
Receipt not found
Receipt file not found
Receipt is already linked to an expense
```

Suggested status codes:

```text
404 Receipt not found
404 Receipt file not found
409 Receipt is already linked to an expense
```

Preserve existing `GeminiServiceError` statuses.

Do not raise `HTTPException` inside the service layer.

---

# 18. Service Tests

Create or update service tests.

Mock:

```text
extract_receipt_data()
```

Do not call Gemini.

Test at least:

1. Valid owned receipt creates a draft expense.
2. Created expense belongs to current user.
3. `input_method` is set to AI value.
4. `ai_status` is set to completed value.
5. `is_confirmed` is false.
6. English extraction is saved.
7. Thai extraction is saved.
8. Nested items are created.
9. English and Thai item names are saved.
10. Receipt is linked to created expense.
11. Main category name matches an active category.
12. Item category name matches an active category.
13. Category matching is case-insensitive.
14. Unknown category leaves category ID as `None`.
15. Inactive category is ignored.
16. Soft-deleted category is ignored.
17. Missing receipt returns `404`.
18. Another user's receipt returns `404`.
19. Soft-deleted receipt returns `404`.
20. Missing physical file returns `404`.
21. Already-linked receipt returns `409`.
22. Gemini failure creates no expense.
23. Gemini failure creates no items.
24. Gemini failure leaves receipt unlinked.
25. Database failure rolls back expense.
26. Database failure rolls back items.
27. Database failure leaves receipt unlinked.
28. Empty extracted items creates expense with `items=[]`.
29. Missing title uses merchant name.
30. Missing title and merchant uses `Extracted Receipt`.
31. No real Gemini request is made.

Use temporary receipt files.

Use `smart_receipt_db_test`.

---

# 19. Route Tests

Add route tests for:

1. Authenticated user can extract their receipt.
2. Success returns `201`.
3. Success returns `ExpenseResponse`.
4. Response includes nested items.
5. Receipt becomes linked.
6. English receipt works.
7. Thai receipt works.
8. Missing receipt returns `404`.
9. Another user's receipt returns `404`.
10. Soft-deleted receipt returns `404`.
11. Missing file returns `404`.
12. Already-linked receipt returns `409`.
13. Missing token returns `401`.
14. Invalid token returns `401`.
15. Mocked Gemini error preserves expected status.
16. Invalid Gemini output creates no database records.
17. Response does not expose local file path.
18. Response does not expose deleted fields.
19. No real Gemini call occurs.
20. Existing full test suite remains green.

---

# 20. Test Isolation

All database tests must use:

```text
smart_receipt_db_test
```

Never use the development database.

Override `get_db`.

Use temporary upload folders.

Clean dependent records in safe foreign-key order.

Do not delete real uploaded files.

---

# 21. Verification Commands

Run from the backend folder with the virtual environment active:

```bash
python -m compileall app tests
```

Run extraction service tests:

```bash
pytest tests/test_receipt_extraction_service.py
```

Run receipt route tests:

```bash
pytest tests/test_receipt_routes.py
```

Run the full suite:

```bash
pytest
```

Confirm no test sends a real Gemini request.

Optionally verify in Swagger:

```text
http://127.0.0.1:8000/docs
```

Confirm:

```text
POST /api/receipts/{receipt_id}/extract
```

---

# Do Not Implement Yet

Do not implement:

- Expense confirmation endpoint
- Re-extraction endpoint
- Standalone English–Thai translation
- Translation history management
- Excel export
- Pagination
- Search and filters
- Background workers
- Automatic category creation
- Frontend pages

---

# Expected Final Result

After this step, the project should have:

- Protected receipt extraction endpoint
- Strict receipt ownership validation
- Physical-file validation
- Mocked Gemini integration
- Draft Expense creation
- ExpenseItem creation
- Simple category matching
- Receipt-to-expense linking
- One atomic transaction
- Full rollback on failure
- English and Thai extraction support
- No confirmation or standalone translation yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Service function added
3. Route added
4. Receipt ownership and file checks
5. Gemini service reuse
6. Expense field mapping
7. Draft and AI field values
8. Category matching behavior
9. Expense-item mapping
10. Receipt linking behavior
11. Transaction and rollback behavior
12. Service test result
13. Route test result
14. Full test-suite result
15. Confirmation that tests use no real Gemini calls
16. Any schema, model, enum, or file-path mismatch found

Do not produce a long walkthrough unless an error occurs.
