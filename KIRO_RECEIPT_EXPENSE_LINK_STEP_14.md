# Smart Receipt Project — Step 14: Link and Unlink Receipt Files to Expenses

## Goal

Implement protected endpoints that connect an uploaded receipt file to an existing expense and allow that link to be removed.

Create:

```text
POST   /api/expenses/{expense_id}/receipts/{receipt_id}
DELETE /api/expenses/{expense_id}/receipts/{receipt_id}
```

The authenticated user must own both the expense and the receipt.

Keep the code simple, readable, and easy for a student to explain.

Do not implement Gemini extraction, OCR, translation, Excel export, pagination, filtering, or frontend code yet.

---

## Project Status

The project already has:

- Database models and migrations
- Authentication system
- Current-user dependency
- Protected category read endpoints
- Receipt upload, list, detail, and soft delete
- Expense create, list, detail, update, and soft delete
- Expense-item support
- Separate MySQL test database
- 329 tests passing

Inspect the existing `Expense`, `ReceiptFile`, service, route, and schema files before changing anything.

Do not rebuild completed features.

---

## Existing Relationship

The existing receipt model contains:

```text
receipt_files.expense_id
```

This means:

```text
One receipt belongs to zero or one expense.
One expense may have multiple receipt files.
```

Do not add a new relationship table.

Do not add `receipt_file_id` to the Expense model.

Do not create a migration unless the existing model genuinely does not support this relationship.

---

## API Endpoints

Use:

```text
POST   /api/expenses/{expense_id}/receipts/{receipt_id}
DELETE /api/expenses/{expense_id}/receipts/{receipt_id}
```

Use clear Swagger summaries:

```text
Link Receipt to Expense
Unlink Receipt from Expense
```

---

## Ownership Rules

The current user must own both records:

```text
expense.user_id == current_user.id
receipt.user_id == current_user.id
```

Both records must also be active:

```text
expense.deleted_at is null
receipt.deleted_at is null
```

For any missing, deleted, or other-user expense or receipt, return:

```text
404 Expense or receipt not found
```

Do not return `403`.

Do not reveal whether another user owns the record.

---

## Important Coding Style

Follow these rules:

1. Use simple service functions.
2. Keep route functions thin.
3. Put SQLAlchemy queries and business rules in services.
4. Reuse existing receipt and expense services where practical.
5. Do not add a repository layer.
6. Do not add service classes.
7. Do not add generic relationship helpers.
8. Use one transaction for each link or unlink operation.
9. Roll back on failure.
10. Do not delete any receipt file.
11. Do not delete any expense.
12. Do not change physical files.
13. Do not expose internal `file_path`.
14. Keep tests isolated in `smart_receipt_db_test`.

---

## Expected Files

Update only what is needed:

```text
backend/app/services/expense_service.py
backend/app/services/__init__.py

backend/app/routes/expenses.py

backend/tests/test_expense_service.py
backend/tests/test_expense_routes.py
```

If the project already keeps receipt-link logic in `receipt_service.py`, that is acceptable only if it is simpler and consistent.

Do not create duplicate service files.

---

# 1. Add Service Functions

Add:

```text
link_receipt_to_expense
unlink_receipt_from_expense
```

Recommended signatures:

```python
def link_receipt_to_expense(
    db: Session,
    user_id: int,
    expense_id: int,
    receipt_id: int,
) -> ReceiptFile:
    ...
```

```python
def unlink_receipt_from_expense(
    db: Session,
    user_id: int,
    expense_id: int,
    receipt_id: int,
) -> ReceiptFile:
    ...
```

Returning `ReceiptFileResponse` instead of ORM objects is also acceptable if it matches the existing service style.

---

# 2. `link_receipt_to_expense`

## Required Process

Use this order:

```text
1. Find the owned, non-deleted expense
2. Find the owned, non-deleted receipt
3. Return 404-style service error if either is unavailable
4. Check the receipt's current expense_id
5. If already linked to the same expense, return success safely
6. If linked to a different expense, reject with 409
7. Set receipt.expense_id = expense.id
8. Commit once
9. Refresh the receipt
10. Return the receipt
```

---

## Already Linked to Same Expense

This should be idempotent.

If:

```text
receipt.expense_id == expense_id
```

return the existing receipt successfully.

Do not create an error.

Do not write unnecessary database changes.

---

## Linked to Another Expense

If:

```text
receipt.expense_id is not null
and
receipt.expense_id != expense_id
```

reject with:

```text
409 Conflict
```

Use a simple message:

```text
Receipt is already linked to another expense
```

Do not automatically move the receipt.

Reassignment should be explicit:

```text
unlink first
then link to another expense
```

---

# 3. `unlink_receipt_from_expense`

## Required Process

Use this order:

```text
1. Find the owned, non-deleted expense
2. Find the owned, non-deleted receipt
3. Return 404-style service error if either is unavailable
4. Confirm receipt.expense_id == expense.id
5. If not linked to that expense, reject
6. Set receipt.expense_id = None
7. Commit once
8. Refresh the receipt
9. Return the receipt
```

If the receipt is not linked to that expense, use:

```text
409 Conflict
```

with:

```text
Receipt is not linked to this expense
```

Do not delete the receipt row.

Do not delete the physical file.

---

# 4. Error Handling

Reuse `ExpenseServiceError` if that keeps the code simple.

Suggested statuses:

```text
Missing/deleted/other-user expense or receipt: 404
Receipt already linked to another expense: 409
Receipt not linked to this expense: 409
```

Do not raise `HTTPException` inside the service.

The route should convert service errors to HTTP responses.

---

# 5. Transaction Handling

Use one transaction for each operation.

Recommended concept:

```python
try:
    receipt.expense_id = expense.id
    db.commit()
    db.refresh(receipt)
    return receipt
except Exception:
    db.rollback()
    raise
```

Do the equivalent for unlink.

Do not commit more than once.

Do not modify the physical file.

---

# 6. Update Service Exports

Update:

```text
backend/app/services/__init__.py
```

Expose:

```text
link_receipt_to_expense
unlink_receipt_from_expense
```

Keep imports simple.

---

# 7. Update Expense Routes

Update:

```text
backend/app/routes/expenses.py
```

Add the following protected routes.

---

## Link Receipt to Expense

### Endpoint

```text
POST /api/expenses/{expense_id}/receipts/{receipt_id}
```

### Swagger Summary

```text
Link Receipt to Expense
```

### Response Model

Use:

```text
ReceiptFileResponse
```

### Success Status

```text
200 OK
```

### Behavior

```text
1. Call link_receipt_to_expense(db, current_user.id, expense_id, receipt_id)
2. Convert ExpenseServiceError to HTTPException
3. Return the updated receipt
```

Do not query the database inside the route.

---

## Unlink Receipt from Expense

### Endpoint

```text
DELETE /api/expenses/{expense_id}/receipts/{receipt_id}
```

### Swagger Summary

```text
Unlink Receipt from Expense
```

### Response Model

Use:

```text
ReceiptFileResponse
```

### Success Status

```text
200 OK
```

### Behavior

```text
1. Call unlink_receipt_from_expense(db, current_user.id, expense_id, receipt_id)
2. Convert ExpenseServiceError to HTTPException
3. Return the updated receipt
```

The returned response should show:

```text
expense_id = null
```

only if `expense_id` is included in `ReceiptFileResponse`.

If the current response schema does not expose `expense_id`, returning a simple success message is acceptable:

```json
{
  "message": "Receipt unlinked successfully"
}
```

Choose the simplest approach consistent with the existing schema.

---

# 8. Receipt Response Schema

Inspect the existing:

```text
ReceiptFileResponse
```

If `expense_id` is already included, keep it.

If it is not included, do not change the schema unless showing link status is clearly useful.

A small schema update to include:

```text
expense_id: int | None
```

is acceptable because it is a real safe relationship field.

Do not expose:

```text
file_path
deleted_at
```

---

# 9. Expense Service Tests

Update:

```text
backend/tests/test_expense_service.py
```

Keep all existing tests.

Add tests for:

1. Successful receipt link.
2. Linked receipt stores correct `expense_id`.
3. Linking the same receipt to the same expense is idempotent.
4. Receipt linked to another expense returns `409`.
5. Unknown expense returns `404`.
6. Unknown receipt returns `404`.
7. Another user's expense returns `404`.
8. Another user's receipt returns `404`.
9. Soft-deleted expense returns `404`.
10. Soft-deleted receipt returns `404`.
11. Successful unlink sets `expense_id` to `None`.
12. Unlink preserves receipt database row.
13. Unlink preserves physical file.
14. Unlink from wrong expense returns `409`.
15. Unlink an unlinked receipt returns `409`.
16. Unknown expense on unlink returns `404`.
17. Unknown receipt on unlink returns `404`.
18. Another user's records cannot be unlinked.
19. Database failure rolls back link.
20. Database failure rolls back unlink.

Use `smart_receipt_db_test`.

Use temporary upload directories when physical receipt files are involved.

---

# 10. Expense Route Tests

Update:

```text
backend/tests/test_expense_routes.py
```

Keep all existing tests.

Add tests for:

1. Authenticated user can link their receipt to their expense.
2. Link returns `200`.
3. Link response shows correct relationship when exposed.
4. Linking same receipt again succeeds safely.
5. Linking receipt already attached elsewhere returns `409`.
6. Unknown expense returns `404`.
7. Unknown receipt returns `404`.
8. Another user's expense returns `404`.
9. Another user's receipt returns `404`.
10. Soft-deleted expense returns `404`.
11. Soft-deleted receipt returns `404`.
12. Missing token on link returns `401`.
13. Invalid token on link returns `401`.
14. Authenticated user can unlink receipt.
15. Unlink returns `200`.
16. Unlink response shows no expense relation when exposed.
17. Unlink from wrong expense returns `409`.
18. Unlink unlinked receipt returns `409`.
19. Missing token on unlink returns `401`.
20. Existing auth, category, receipt, and expense tests still pass.

---

# 11. Security Requirements

1. Always validate expense ownership.
2. Always validate receipt ownership.
3. Never trust IDs alone.
4. Return `404` for other-user records.
5. Do not move a receipt automatically between expenses.
6. Require explicit unlink before linking elsewhere.
7. Do not delete files.
8. Do not expose internal paths.
9. Use one transaction.
10. Roll back on failure.

---

# 12. Verification Commands

Run from the `backend` folder with the virtual environment active:

```bash
python -m compileall app tests
```

Run expense service tests:

```bash
pytest tests/test_expense_service.py
```

Run expense route tests:

```bash
pytest tests/test_expense_routes.py
```

Run the full suite:

```bash
pytest
```

Optionally verify in Swagger:

```text
http://127.0.0.1:8000/docs
```

Confirm:

```text
POST   /api/expenses/{expense_id}/receipts/{receipt_id}
DELETE /api/expenses/{expense_id}/receipts/{receipt_id}
```

---

# Do Not Implement Yet

Do not implement:

- Automatic receipt reassignment
- Gemini extraction
- OCR
- English–Thai translation
- Review/confirmation workflow
- Excel export
- Pagination
- Search
- Filters
- Dashboard statistics
- Public file download
- Frontend pages

---

# Expected Final Result

After this step, the project should have:

- Protected receipt-to-expense linking
- Protected receipt unlinking
- Strict ownership checks
- Idempotent same-expense linking
- Conflict handling for cross-expense links
- No record deletion
- No physical-file deletion
- Service tests
- Route tests
- No AI or translation yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Service functions added
3. Routes added
4. Ownership rules
5. Same-expense idempotent behavior
6. Cross-expense conflict behavior
7. Unlink behavior
8. Transaction and rollback behavior
9. Expense service test result
10. Expense route test result
11. Full test-suite result
12. Any model mismatch or issue found

Do not produce a long walkthrough unless an error occurs.
