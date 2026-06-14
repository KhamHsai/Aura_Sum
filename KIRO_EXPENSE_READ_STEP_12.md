# Smart Receipt Project — Step 12: Expense List and Detail

## Goal

Implement protected expense read endpoints for the authenticated user.

Create:

```text
GET /api/expenses
GET /api/expenses/{expense_id}
```

These endpoints must allow each user to view only their own non-deleted expenses.

Keep the code simple, readable, and easy for a student to explain.

Do not implement expense update, delete, receipt linking, pagination, filtering, Gemini extraction, translation, Excel export, or frontend code yet.

---

## Project Status

The project already has:

- Database models and migrations
- Authentication system
- Current-user dependency
- Protected category read endpoints
- Receipt upload, list, detail, and soft delete
- Expense and expense-item schemas
- Protected expense creation endpoint
- Nested expense-item creation
- Separate MySQL test database
- 235 tests passing

Inspect the existing expense service, models, schemas, and routes before changing anything.

Do not rebuild completed features.

---

## API Endpoints

Use standard REST endpoints:

```text
GET /api/expenses
GET /api/expenses/{expense_id}
```

Use clear Swagger summaries:

```text
List My Expenses
Get Expense Details
```

Do not add:

```text
/api/expenses/list
/api/expenses/view
```

---

## Ownership Rule

This is the most important rule.

```text
User A can only list User A's expenses.
User A can only view User A's expense.
User A cannot view User B's expense.
```

When an expense:

```text
does not exist
belongs to another user
is soft-deleted
```

return:

```text
404 Expense not found
```

Do not return `403`.

This avoids revealing that another user's expense exists.

---

## Important Coding Style

Follow these rules:

1. Use simple functions.
2. Keep route functions thin.
3. Put SQLAlchemy queries in the service layer.
4. Reuse `get_current_user`.
5. Reuse `ExpenseResponse`.
6. Include only non-deleted expense items.
7. Do not add a repository layer.
8. Do not add service classes.
9. Do not add generic CRUD base classes.
10. Do not add pagination yet.
11. Do not add search or filters yet.
12. Do not expose internal AI fields.
13. Do not expose `deleted_at`.
14. Keep tests isolated in `smart_receipt_db_test`.
15. Keep existing expense creation behavior unchanged.

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

Do not create duplicate expense service or route files.

---

# 1. Update `backend/app/services/expense_service.py`

Add:

```text
get_user_expenses
get_user_expense_by_id
```

Keep the existing:

```text
create_expense
ExpenseServiceError
```

unchanged unless a real bug is found.

---

## `get_user_expenses`

### Purpose

Return all non-deleted expenses belonging to one user.

### Recommended Signature

```python
def get_user_expenses(
    db: Session,
    user_id: int,
) -> list[ExpenseResponse]:
    ...
```

Returning ORM objects is also acceptable if `ExpenseResponse` can serialize them safely.

Use whichever approach is simplest and consistent with the existing `create_expense()` implementation.

### Query Rules

Filter by:

```text
Expense.user_id == user_id
Expense.deleted_at is null
```

Include only non-deleted expense items:

```text
ExpenseItem.deleted_at is null
```

Do not return another user's expenses.

Do not return soft-deleted expenses.

---

## Ordering

Return newest expenses first.

Use stable ordering based on real model fields.

Recommended:

```text
receipt_date descending
created_at descending
id descending
```

Because `receipt_date` may be null, the simplest reliable order is also acceptable:

```text
created_at descending
id descending
```

Choose one clear and stable ordering and use the same ordering in tests.

Do not add user-controlled sorting yet.

---

## Empty Result

When the user has no expenses, return:

```text
[]
```

Do not raise an error.

---

## Nested Items

Each returned expense should include:

```text
items: list[ExpenseItemResponse]
```

Only include expense items where:

```text
deleted_at is null
```

Keep item ordering stable.

Preferred ordering:

```text
id ascending
```

or another simple real field.

Do not include deleted items.

---

## `get_user_expense_by_id`

### Purpose

Return one owned, non-deleted expense with its non-deleted items.

### Recommended Signature

```python
def get_user_expense_by_id(
    db: Session,
    user_id: int,
    expense_id: int,
) -> ExpenseResponse | None:
    ...
```

Returning an ORM object is also acceptable if serialization is reliable.

### Query Rules

Filter by:

```text
Expense.id == expense_id
Expense.user_id == user_id
Expense.deleted_at is null
```

Include only items where:

```text
ExpenseItem.deleted_at is null
```

Return:

```text
None
```

when:

```text
Expense does not exist
Expense belongs to another user
Expense is soft-deleted
```

Do not raise `HTTPException` inside the service.

---

# 2. SQLAlchemy Loading

The previous expense creation step found relationship-loading issues with:

```text
autoflush=False
SQLAlchemy identity map caching
```

Use the simplest reliable solution.

Acceptable approaches:

1. Query expense rows and item rows separately, then build `ExpenseResponse`.
2. Use eager loading only if it works reliably in the existing test session.
3. Reuse a small response-building helper inside `expense_service.py`.

A small private helper is acceptable:

```python
def _build_expense_response(expense, items) -> ExpenseResponse:
    ...
```

Do not create a generic serializer framework.

Do not rely on lazy loading if it causes inconsistent results.

---

# 3. Update `backend/app/services/__init__.py`

Expose:

```text
get_user_expenses
get_user_expense_by_id
```

Keep imports simple.

---

# 4. Update `backend/app/routes/expenses.py`

Keep the existing:

```text
POST /api/expenses
```

Add the following routes.

---

## List My Expenses

### Endpoint

```text
GET /api/expenses
```

### Swagger Summary

```text
List My Expenses
```

### Response Model

```text
list[ExpenseResponse]
```

### Success Status

```text
200 OK
```

### Dependencies

```python
db: Session = Depends(get_db)
current_user: User = Depends(get_current_user)
```

### Behavior

```text
Call get_user_expenses(db, current_user.id)
Return the result
```

Use:

```python
@router.get("")
```

to avoid a trailing-slash redirect.

Do not query the database inside the route.

---

## Get Expense Details

### Endpoint

```text
GET /api/expenses/{expense_id}
```

### Swagger Summary

```text
Get Expense Details
```

### Response Model

```text
ExpenseResponse
```

### Success Status

```text
200 OK
```

### Behavior

```text
1. Call get_user_expense_by_id(db, current_user.id, expense_id)
2. If None, raise HTTPException(404, "Expense not found")
3. Return the expense
```

Do not reveal whether another user owns the expense.

---

# 5. Expense Service Tests

Update:

```text
backend/tests/test_expense_service.py
```

Keep all existing create tests.

Add tests for:

1. `get_user_expenses()` returns only the current user's expenses.
2. Another user's expenses are excluded.
3. Soft-deleted expenses are excluded.
4. Empty expense table returns `[]`.
5. User with no expenses returns `[]`.
6. Results are ordered newest first.
7. Ordering remains stable when dates are equal.
8. Returned expenses include nested items.
9. Soft-deleted items are excluded.
10. Item order is stable.
11. `get_user_expense_by_id()` returns an owned expense.
12. Detail response includes nested items.
13. Unknown expense ID returns `None`.
14. Another user's expense returns `None`.
15. Soft-deleted expense returns `None`.
16. Detail excludes soft-deleted items.
17. Internal AI fields are not exposed.
18. `deleted_at` is not exposed.

Use real model fields and `smart_receipt_db_test`.

---

# 6. Expense Route Tests

Update:

```text
backend/tests/test_expense_routes.py
```

Keep existing create-route tests.

Add tests for:

1. Authenticated user can list expenses.
2. List route returns `200`.
3. List route returns an array.
4. List route returns only the authenticated user's expenses.
5. List route excludes soft-deleted expenses.
6. List route returns newest expenses first.
7. Empty list returns `200` and `[]`.
8. List response includes nested items.
9. List response excludes soft-deleted items.
10. Missing access token on list returns `401`.
11. Invalid access token on list returns `401`.
12. Authenticated user can retrieve their expense by ID.
13. Detail response includes nested items.
14. Unknown expense ID returns `404`.
15. Another user's expense returns `404`.
16. Soft-deleted expense returns `404`.
17. Missing access token on detail returns `401`.
18. Response does not expose `deleted_at`.
19. Response does not expose internal AI fields.
20. Existing create, auth, category, and receipt tests still pass in the full suite.

---

# 7. Test Isolation

All tests must use:

```text
smart_receipt_db_test
```

Never use:

```text
smart_receipt_db
```

Continue overriding `get_db`.

Clean only test expense and item records.

Do not touch development data.

---

# 8. Security Requirements

1. Always filter expenses by `current_user.id`.
2. Never trust `expense_id` alone.
3. Return `404` for another user's expense.
4. Exclude soft-deleted expenses.
5. Exclude soft-deleted items.
6. Do not expose `deleted_at`.
7. Do not expose AI internal fields.
8. Do not expose another user's information.
9. Keep response ordering stable.

---

# 9. Verification Commands

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
POST /api/expenses
GET  /api/expenses
GET  /api/expenses/{expense_id}
```

---

# Do Not Implement Yet

Do not implement:

- `PUT /api/expenses/{expense_id}`
- `DELETE /api/expenses/{expense_id}`
- Expense item standalone routes
- Pagination
- Search
- Date filtering
- Category filtering
- Receipt linking
- Gemini extraction
- OCR
- Translation
- Excel export
- Dashboard statistics
- Frontend pages

---

# Expected Final Result

After this step, the project should have:

- Protected expense list endpoint
- Protected expense detail endpoint
- Strict user ownership
- Soft-deleted expenses hidden
- Soft-deleted items hidden
- Stable newest-first ordering
- Nested items included
- Service tests
- Route tests
- Existing create endpoint unchanged
- No update or delete yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Service functions added
3. Routes added
4. Ownership rules implemented
5. Ordering used
6. Nested-item loading approach
7. Expense service test result
8. Expense route test result
9. Full test-suite result
10. Any issue or model mismatch

Do not produce a long walkthrough unless an error occurs.
