# Smart Receipt Project — Step 16: Review and Confirm AI-Extracted Expense

## Goal

Implement:

```text
POST /api/expenses/{expense_id}/confirm
```

This endpoint allows the authenticated user to confirm an AI-extracted draft expense after reviewing and correcting it.

Expected workflow:

```text
Upload receipt
→ Extract with Gemini
→ Draft expense created
→ User reviews and updates it
→ User confirms it
```

Write simple, human-readable code that is easy to understand and explain. Avoid unnecessary abstractions, complex patterns, and overengineering.

## Project Status

Already completed:

- Authentication and current-user dependency
- Category read endpoints
- Receipt upload, list, detail, soft delete, link, unlink, and Gemini extraction
- Expense create, list, detail, update, and soft delete
- AI extraction schemas and Gemini service
- Draft AI expense creation
- Nullable `expenses.category_id` Alembic migration
- 466 tests passing

Inspect the current Expense model, schemas, service, routes, and tests before changing anything.

Do not rebuild completed features.

## Scope

Implement only:

- `POST /api/expenses/{expense_id}/confirm`
- Confirmation service logic
- Ownership validation
- Draft validation
- Already-confirmed conflict handling
- Service tests
- Route tests

Do not implement translation, Excel export, re-extraction, background jobs, frontend code, or new database tables.

## Coding Style

1. Use clear function and variable names.
2. Keep route functions thin.
3. Put validation and database logic in the service layer.
4. Reuse `ExpenseResponse`.
5. Reuse `ExpenseServiceError`.
6. Do not add service classes or repository classes.
7. Use one database transaction.
8. Roll back on failure.
9. Keep existing expense update behavior unchanged.

## Files

Update only what is needed:

```text
backend/app/services/expense_service.py
backend/app/services/__init__.py
backend/app/routes/expenses.py
backend/tests/test_expense_service.py
backend/tests/test_expense_routes.py
```

## Endpoint

Create:

```text
POST /api/expenses/{expense_id}/confirm
```

Swagger summary:

```text
Confirm Expense
```

Success:

```text
200 OK
```

Response model:

```text
ExpenseResponse
```

The route must use:

```python
db: Session = Depends(get_db)
current_user: User = Depends(get_current_user)
```

The route should only call the service, convert service errors to `HTTPException`, and return the response.

## Service Function

Add:

```python
def confirm_user_expense(
    db: Session,
    user_id: int,
    expense_id: int,
) -> ExpenseResponse:
    ...
```

## Ownership Validation

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

## AI Expense Validation

Only AI-created expenses may use this endpoint.

Check:

```text
expense.input_method == "ai"
```

Use the exact stored value already used by the project.

If it is not an AI expense, return:

```text
409 Only AI-extracted expenses can be confirmed
```

## Already Confirmed

If:

```text
expense.is_confirmed is True
```

return:

```text
409 Expense is already confirmed
```

Do not write to the database again.

## Required Fields

Before confirmation, require:

```text
category_id is not null
title is present and not blank
total_amount is present
total_amount is zero or greater
```

Suggested validation errors:

```text
422 Expense category is required before confirmation
422 Expense title is required before confirmation
422 Expense total amount is required before confirmation
422 Expense total amount must be zero or greater
```

Use a clear validation order:

```text
1. category
2. title
3. total amount
```

## Category Validation

If `category_id` exists, confirm the category:

```text
exists
is active
is not soft-deleted
```

If not valid, return:

```text
422 A valid expense category is required before confirmation
```

Do not assign another category automatically.

Do not create categories.

## Confirmation Update

After validation:

```python
expense.is_confirmed = True
```

Keep:

```text
ai_status = "completed"
```

unless the project already has a defined confirmed status.

Do not modify:

```text
receipt links
expense items
ai_raw_response
language_detected
ai_confidence
input_method
user_id
```

## Transaction

Use one commit:

```python
try:
    expense.is_confirmed = True
    db.commit()
    db.refresh(expense)
    return response
except Exception:
    db.rollback()
    raise
```

If the commit fails, the expense must remain unconfirmed.

## Response

Return `ExpenseResponse` with active nested items.

Reuse the current expense response builder.

Do not expose internal fields such as `deleted_at`.

## Service Export

Export:

```text
confirm_user_expense
```

from:

```text
backend/app/services/__init__.py
```

## Service Tests

Keep all existing tests and add tests for:

1. Successful confirmation.
2. `ExpenseResponse` is returned.
3. `is_confirmed` becomes `True`.
4. `ai_status` remains unchanged.
5. Items remain unchanged.
6. Receipt link remains unchanged.
7. Unknown expense returns `404`.
8. Other user's expense returns `404`.
9. Soft-deleted expense returns `404`.
10. Manual expense returns `409`.
11. Already-confirmed expense returns `409`.
12. Missing category returns `422`.
13. Invalid category returns `422`.
14. Inactive category returns `422`.
15. Soft-deleted category returns `422`.
16. Blank title returns `422`.
17. Missing total returns `422` when possible.
18. Negative total returns `422`.
19. Zero total is accepted.
20. Failed validation does not confirm.
21. Database failure rolls back.
22. Ownership does not change.
23. No unrelated fields change.
24. Internal fields are not exposed.

Use `smart_receipt_db_test`.

## Route Tests

Keep existing tests and add tests for:

1. Authenticated user can confirm an AI expense.
2. Success returns `200`.
3. Response uses `ExpenseResponse`.
4. Response shows `is_confirmed = true`.
5. Nested items are included.
6. Unknown expense returns `404`.
7. Other user's expense returns `404`.
8. Soft-deleted expense returns `404`.
9. Manual expense returns `409`.
10. Already-confirmed expense returns `409`.
11. Missing category returns `422`.
12. Blank title returns `422`.
13. Invalid total returns `422`.
14. Missing token returns `401`.
15. Invalid token returns `401`.
16. Confirmed expense remains visible in list.
17. Confirmed expense remains available in detail.
18. Existing update still works before confirmation.
19. Internal fields are not exposed.
20. Full test suite remains green.

## Verification

Run:

```bash
python -m compileall app tests
pytest tests/test_expense_service.py
pytest tests/test_expense_routes.py
pytest
```

Optionally verify in Swagger:

```text
POST /api/expenses/{expense_id}/confirm
```

## Do Not Implement Yet

- English–Thai translation
- Translation history
- Excel export
- Re-extraction
- Background processing
- Frontend pages
- New database tables

## Expected Result

After this step:

- Protected confirmation endpoint
- Strict ownership checks
- AI-expense-only confirmation
- Required-field validation
- Valid-category validation
- Already-confirmed conflict handling
- Atomic transaction
- Service and route tests
- No translation or export yet

## Completion Report

Provide:

1. Changed files
2. Service function added
3. Route added
4. Ownership behavior
5. AI-expense validation
6. Required-field validation
7. Category validation
8. Already-confirmed behavior
9. Transaction and rollback behavior
10. Service test result
11. Route test result
12. Full test-suite result
13. Any model or schema mismatch
