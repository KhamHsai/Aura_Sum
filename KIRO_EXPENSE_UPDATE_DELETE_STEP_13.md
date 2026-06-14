# Smart Receipt Project — Step 13: Expense Update and Soft Delete

## Goal

Implement protected expense update and soft-delete endpoints.

Create:

```text
PUT    /api/expenses/{expense_id}
DELETE /api/expenses/{expense_id}
```

The authenticated user must be able to update or delete only their own non-deleted expenses.

Keep the code simple, readable, and easy for a student to explain.

Do not implement receipt linking, Gemini extraction, OCR, translation, Excel export, pagination, filtering, or frontend code yet.

---

## Project Status

The project already has:

- Database models and migrations
- Authentication system
- Current-user dependency
- Protected category read endpoints
- Receipt upload, list, detail, and soft delete
- Expense and expense-item schemas
- Protected expense creation
- Protected expense list and detail
- Nested expense-item responses
- Separate MySQL test database
- 272 tests passing

Inspect the existing expense models, schemas, service, and routes before making changes.

Do not rebuild completed features.

---

## API Endpoints

Use standard REST endpoints:

```text
PUT    /api/expenses/{expense_id}
DELETE /api/expenses/{expense_id}
```

Use clear Swagger summaries:

```text
Update Expense
Delete Expense
```

Do not add:

```text
/api/expenses/{expense_id}/edit
/api/expenses/{expense_id}/delete
```

---

## Ownership Rule

This is the most important rule.

```text
User A can update only User A's expense.
User A can delete only User A's expense.
User A cannot update or delete User B's expense.
```

When an expense:

```text
does not exist
belongs to another user
is already soft-deleted
```

return:

```text
404 Expense not found
```

Do not return `403`.

This prevents revealing that another user's expense exists.

---

## Important Coding Style

Follow these rules:

1. Use simple functions.
2. Keep route functions thin.
3. Put SQLAlchemy queries and business logic in the service layer.
4. Reuse `ExpenseUpdate` and `ExpenseResponse`.
5. Reuse `get_current_user`.
6. Reuse existing category validation logic where practical.
7. Do not add a repository layer.
8. Do not add service classes.
9. Do not add generic CRUD base classes.
10. Use one transaction for each update or delete.
11. Roll back on failure.
12. Use soft delete only.
13. Do not permanently delete database rows.
14. Do not delete linked receipt files.
15. Do not expose `deleted_at`.
16. Do not expose internal AI fields.
17. Keep tests isolated in `smart_receipt_db_test`.

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

Do not create duplicate expense files.

---

# 1. Update `backend/app/services/expense_service.py`

Add:

```text
update_user_expense
delete_user_expense
```

Keep existing:

```text
create_expense
get_user_expenses
get_user_expense_by_id
ExpenseServiceError
```

unchanged unless a real bug is found.

---

# 2. `update_user_expense`

## Purpose

Update one owned, non-deleted expense.

## Recommended Signature

```python
def update_user_expense(
    db: Session,
    user_id: int,
    expense_id: int,
    data: ExpenseUpdate,
) -> ExpenseResponse | None:
    ...
```

Returning `None` for unavailable expense is acceptable.

The route will convert `None` into:

```text
404 Expense not found
```

---

## Required Process

Use this order:

```text
1. Find the owned, non-deleted expense
2. Return None if unavailable
3. Read only fields actually provided in ExpenseUpdate
4. Validate a new main category when category_id is provided
5. Update simple expense fields
6. Handle items only when items was provided
7. Commit once
8. Return updated ExpenseResponse
```

Use Pydantic v2:

```python
data.model_dump(exclude_unset=True)
```

This is important so missing fields do not overwrite existing values.

---

# 3. Updating Simple Expense Fields

Update only allowed fields from `ExpenseUpdate`.

Possible editable fields may include:

```text
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
notes
```

Use only fields that actually exist in the current `ExpenseUpdate` schema.

Do not allow updates to:

```text
id
user_id
input_method
language_detected
ai_confidence
ai_status
ai_raw_response
is_confirmed
created_at
updated_at
deleted_at
```

unless the existing schema intentionally includes one of them.

Never allow the client to change ownership.

---

# 4. Main Category Validation

If `category_id` is provided in the update:

```text
Category must exist
Category must be active
Category must not be soft-deleted
```

If unavailable, raise:

```text
Category not found
```

with the same status code used by expense creation.

Do not change the expense if category validation fails.

---

# 5. Expense Item Update Behavior

Keep item updates simple.

Use this rule:

```text
If items is not provided:
→ keep current items unchanged

If items is provided:
→ soft-delete all current active items
→ create new item records from the request
```

Examples:

```json
{
  "title": "Team lunch",
  "total_amount": "450.00"
}
```

This must keep existing items unchanged.

```json
{
  "items": []
}
```

This must remove all current items by soft-deleting them.

```json
{
  "items": [
    {
      "category_id": 1,
      "original_name": "Coffee",
      "quantity": "2",
      "unit": "cup",
      "unit_price": "60.00",
      "discount_amount": "0.00",
      "total_price": "120.00"
    }
  ]
}
```

This must replace the current active items.

---

## Item Category Validation

Before writing any changes, validate every new item's `category_id`, when present.

Each item category must:

```text
exist
be active
not be soft-deleted
```

Use:

```text
Item category not found
```

Do not partially update the expense when one item category is invalid.

---

## Replacing Items

When `items` is provided:

```text
1. Validate all new item categories
2. Soft-delete all existing active items
3. Create all new ExpenseItem records
4. Commit once
```

Use one UTC timestamp for soft-deleting current items.

Do not permanently delete old item rows.

New item records must use:

```text
expense_id = current expense ID
```

---

# 6. Transaction Handling for Update

Use one transaction.

Recommended concept:

```python
try:
    # validate and update expense
    # replace items when provided
    db.commit()
    return updated_response
except Exception:
    db.rollback()
    raise
```

If any update or item creation fails:

```text
No partial field updates should remain
Old active items should remain unchanged
No partial new items should remain
```

Do not commit inside an item loop.

---

# 7. `delete_user_expense`

## Purpose

Soft-delete an owned expense and its active items.

## Recommended Signature

```python
def delete_user_expense(
    db: Session,
    user_id: int,
    expense_id: int,
) -> bool:
    ...
```

---

## Required Process

```text
1. Find the owned, non-deleted expense
2. Return False if unavailable
3. Create one current UTC timestamp
4. Set expense.deleted_at to that timestamp
5. Set deleted_at on all active expense items
6. Commit once
7. Return True
```

Use the same timestamp for the expense and its items where practical.

Do not permanently delete rows.

Do not delete or modify receipt files.

Do not change another user's expense.

---

## Date and Time

Follow the project's existing UTC datetime convention.

The project currently uses UTC naive datetimes in some soft-delete logic.

Use the same convention consistently rather than mixing naive and timezone-aware values.

---

# 8. Update `backend/app/services/__init__.py`

Expose:

```text
update_user_expense
delete_user_expense
```

Keep imports simple.

---

# 9. Update `backend/app/routes/expenses.py`

Keep existing:

```text
POST /api/expenses
GET  /api/expenses
GET  /api/expenses/{expense_id}
```

Add the following routes.

---

## Update Expense

### Endpoint

```text
PUT /api/expenses/{expense_id}
```

### Swagger Summary

```text
Update Expense
```

### Request Model

```text
ExpenseUpdate
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
1. Call update_user_expense(db, current_user.id, expense_id, data)
2. If None, raise HTTPException(404, "Expense not found")
3. Convert ExpenseServiceError to HTTPException
4. Return updated expense
```

Do not query the database inside the route.

---

## Delete Expense

### Endpoint

```text
DELETE /api/expenses/{expense_id}
```

### Swagger Summary

```text
Delete Expense
```

### Success Status

```text
200 OK
```

### Response

```json
{
  "message": "Expense deleted successfully"
}
```

### Behavior

```text
1. Call delete_user_expense(db, current_user.id, expense_id)
2. If False, raise HTTPException(404, "Expense not found")
3. Return success message
```

Do not delete rows or files inside the route.

---

# 10. Expense Service Tests

Update:

```text
backend/tests/test_expense_service.py
```

Keep all existing tests.

Add tests for:

1. Successful simple-field update.
2. Update returns updated `ExpenseResponse`.
3. Missing fields remain unchanged.
4. Empty update is accepted and changes nothing.
5. Category can be changed to another valid category.
6. Invalid category is rejected.
7. Inactive category is rejected.
8. Soft-deleted category is rejected.
9. Another user's expense cannot be updated.
10. Soft-deleted expense cannot be updated.
11. Unknown expense cannot be updated.
12. Updating without `items` preserves current items.
13. Updating with `items=[]` soft-deletes all active items.
14. Updating with items replaces old active items.
15. Old item rows remain in the database as soft-deleted.
16. New items use the correct expense ID.
17. Invalid new item category rejects the full update.
18. Failed item replacement rolls back field changes.
19. Failed item replacement keeps old items active.
20. Current user remains the owner after update.
21. Successful delete sets expense `deleted_at`.
22. Successful delete soft-deletes all active items.
23. Expense and items use a consistent delete timestamp.
24. Deleted expense row remains in the database.
25. Deleted item rows remain in the database.
26. Unknown expense delete returns `False`.
27. Another user's expense delete returns `False`.
28. Already-deleted expense delete returns `False`.
29. Receipt files are not deleted or changed.
30. Response does not expose internal fields.

---

# 11. Expense Route Tests

Update:

```text
backend/tests/test_expense_routes.py
```

Keep all existing tests.

Add tests for:

1. Authenticated user can update their expense.
2. Update returns `200`.
3. Updated fields appear in response.
4. Fields not sent remain unchanged.
5. Empty update succeeds.
6. Update can replace items.
7. Update with `items=[]` returns an empty active item list.
8. Update without `items` preserves items.
9. Invalid category returns expected error.
10. Invalid item category returns expected error.
11. Unknown expense update returns `404`.
12. Another user's expense update returns `404`.
13. Soft-deleted expense update returns `404`.
14. Missing token on update returns `401`.
15. Invalid token on update returns `401`.
16. Authenticated user can delete their expense.
17. Delete returns `200`.
18. Delete response contains `"Expense deleted successfully"`.
19. Deleted expense cannot be retrieved afterward.
20. Deleted expense does not appear in list afterward.
21. Another user's expense delete returns `404`.
22. Unknown expense delete returns `404`.
23. Already-deleted expense delete returns `404`.
24. Missing token on delete returns `401`.
25. Response does not expose `deleted_at`.
26. Response does not expose AI/internal fields.
27. Existing create/read/auth/category/receipt tests pass in full suite.

---

# 12. Security Requirements

1. Always filter by `current_user.id`.
2. Never trust `expense_id` alone.
3. Return `404` for another user's expense.
4. Never allow `user_id` to be updated.
5. Exclude soft-deleted expenses.
6. Soft-delete items when replacing or deleting.
7. Do not permanently delete rows.
8. Do not modify receipt files.
9. Do not expose internal AI fields.
10. Use one transaction.

---

# 13. Verification Commands

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
POST   /api/expenses
GET    /api/expenses
GET    /api/expenses/{expense_id}
PUT    /api/expenses/{expense_id}
DELETE /api/expenses/{expense_id}
```

---

# Do Not Implement Yet

Do not implement:

- Receipt linking
- Receipt-to-expense assignment
- Gemini extraction
- OCR
- Translation
- Excel export
- Pagination
- Search
- Filters
- Dashboard statistics
- Permanent deletion
- Frontend pages

---

# Expected Final Result

After this step, the project should have:

- Protected expense update endpoint
- Protected expense soft-delete endpoint
- Partial update support
- Simple item replacement behavior
- Category validation
- Strict current-user ownership
- Soft deletion of expense items
- Transaction rollback on failure
- Service tests
- Route tests
- No receipt linking or AI processing yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Service functions added
3. Routes added
4. Partial-update behavior
5. Item replacement behavior
6. Category validation behavior
7. Soft-delete behavior
8. Transaction and rollback behavior
9. Expense service test result
10. Expense route test result
11. Full test-suite result
12. Any issue or model mismatch

Do not produce a long walkthrough unless an error occurs.
