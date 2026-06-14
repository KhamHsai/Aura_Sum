# Smart Receipt Project — Step 9: Receipt List, Detail, and Soft Delete

## Goal

Implement protected receipt management endpoints for the authenticated user.

Create:

```text
GET    /api/receipts
GET    /api/receipts/{receipt_id}
DELETE /api/receipts/{receipt_id}
```

These endpoints must allow each user to manage only their own uploaded receipt records.

Keep the code simple, readable, and easy for a student to explain.

Do not implement receipt editing, file download, Gemini extraction, OCR, expense creation, filtering, pagination, or frontend code yet.

---

## Project Status

The project already has:

- Database models and migrations
- Authentication and protected routes
- Protected category read endpoints
- Protected receipt upload endpoint
- Local receipt file storage
- Receipt file validation
- Receipt ownership using `user_id`
- Separate MySQL test database
- 128 tests passing

Inspect the existing code before making changes.

Do not rebuild completed features.

---

## API Convention

Use standard REST endpoints:

```text
GET    /api/receipts
GET    /api/receipts/{receipt_id}
DELETE /api/receipts/{receipt_id}
```

Do not add:

```text
/api/receipts/list
/api/receipts/view
/api/receipts/delete
```

Use clear Swagger summaries instead:

```text
List My Receipts
Get Receipt Details
Delete Receipt
```

---

## Ownership Rule

This is the most important rule.

```text
User A can only list User A's receipts.
User A can only view User A's receipt.
User A can only delete User A's receipt.
User A cannot access User B's receipt.
```

When a receipt does not exist, is soft-deleted, or belongs to another user, return:

```text
404 Receipt not found
```

Do not return `403` for another user's receipt.

This prevents revealing that the other receipt exists.

---

## Important Coding Style

Follow these rules:

1. Use simple functions.
2. Keep route functions thin.
3. Put SQLAlchemy queries in the service layer.
4. Reuse `get_current_user`.
5. Reuse the existing `ReceiptFileResponse`.
6. Do not add a repository layer.
7. Do not add service classes.
8. Do not add generic CRUD base classes.
9. Do not add pagination yet.
10. Do not add filters or search yet.
11. Use soft delete only.
12. Do not permanently delete database rows.
13. Do not delete the physical file in this step.
14. Do not expose `file_path`.
15. Use clear Swagger summaries.
16. Keep tests isolated in `smart_receipt_db_test`.

---

## Expected Files

Update only what is needed:

```text
backend/app/services/receipt_service.py
backend/app/services/__init__.py

backend/app/routes/receipts.py

backend/tests/test_receipt_service.py
backend/tests/test_receipt_routes.py
```

Do not create duplicate receipt service or route files.

---

# 1. Update `backend/app/services/receipt_service.py`

Add these functions:

```text
get_user_receipts
get_user_receipt_by_id
delete_user_receipt
```

---

## `get_user_receipts`

### Purpose

Return all non-deleted receipts belonging to one user.

### Recommended Signature

```python
def get_user_receipts(
    db: Session,
    user_id: int,
) -> list[ReceiptFile]:
    ...
```

### Query Rules

Filter by:

```text
ReceiptFile.user_id == user_id
ReceiptFile.deleted_at is null
```

Order by:

```text
uploaded_at descending
```

Newest receipt first.

If `uploaded_at` is unavailable, use the correct timestamp field from the existing model.

Return:

```text
[]
```

when the user has no receipts.

Do not raise an error for an empty list.

Do not return soft-deleted receipts.

Do not return another user's receipts.

---

## `get_user_receipt_by_id`

### Purpose

Return one receipt only when it belongs to the given user and is not soft-deleted.

### Recommended Signature

```python
def get_user_receipt_by_id(
    db: Session,
    user_id: int,
    receipt_id: int,
) -> ReceiptFile | None:
    ...
```

### Query Rules

Filter by:

```text
ReceiptFile.id == receipt_id
ReceiptFile.user_id == user_id
ReceiptFile.deleted_at is null
```

Return:

```text
ReceiptFile
```

when found.

Return:

```text
None
```

when:

```text
Receipt does not exist
Receipt belongs to another user
Receipt is soft-deleted
```

Do not raise `HTTPException` inside the service.

---

## `delete_user_receipt`

### Purpose

Soft-delete one receipt belonging to the user.

### Recommended Signature

```python
def delete_user_receipt(
    db: Session,
    user_id: int,
    receipt_id: int,
) -> bool:
    ...
```

### Required Process

```text
1. Find the receipt using get_user_receipt_by_id()
2. If no receipt is found, return False
3. Set deleted_at to current UTC time
4. Commit
5. Return True
```

Use:

```python
datetime.now(timezone.utc)
```

when compatible with the existing model.

If the existing database column expects a naive UTC datetime, follow the project's current datetime convention consistently.

### Transaction Handling

Use simple transaction handling:

```text
Set deleted_at
Commit
Rollback and re-raise on database failure
```

Do not permanently delete the row.

Do not delete the physical file.

Do not change `upload_status` unless the project already has a clear deleted status requirement.

---

# 2. Update `backend/app/services/__init__.py`

Expose:

```text
get_user_receipts
get_user_receipt_by_id
delete_user_receipt
```

Keep imports simple.

---

# 3. Update `backend/app/routes/receipts.py`

Keep the existing:

```text
POST /api/receipts/upload
```

Add the following routes.

---

## List My Receipts

### Endpoint

```text
GET /api/receipts
```

### Swagger Summary

```text
List My Receipts
```

### Response Model

```text
list[ReceiptFileResponse]
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
Call get_user_receipts(db, current_user.id)
Return the result
```

Do not query the database directly inside the route.

Use:

```python
@router.get("")
```

to avoid a trailing-slash redirect.

---

## Get Receipt Details

### Endpoint

```text
GET /api/receipts/{receipt_id}
```

### Swagger Summary

```text
Get Receipt Details
```

### Response Model

```text
ReceiptFileResponse
```

### Success Status

```text
200 OK
```

### Behavior

```text
1. Call get_user_receipt_by_id(db, current_user.id, receipt_id)
2. If None, raise HTTPException(404, "Receipt not found")
3. Return the receipt
```

Do not expose whether another user owns the receipt.

---

## Delete Receipt

### Endpoint

```text
DELETE /api/receipts/{receipt_id}
```

### Swagger Summary

```text
Delete Receipt
```

### Success Status

```text
200 OK
```

### Response

```json
{
  "message": "Receipt deleted successfully"
}
```

### Behavior

```text
1. Call delete_user_receipt(db, current_user.id, receipt_id)
2. If False, raise HTTPException(404, "Receipt not found")
3. Return the success message
```

Do not delete the physical file.

Do not permanently delete the database row.

---

# 4. Service Tests

Update:

```text
backend/tests/test_receipt_service.py
```

Keep existing upload tests.

Add tests for:

1. `get_user_receipts()` returns only the current user's receipts.
2. Results are ordered by newest `uploaded_at` first.
3. Soft-deleted receipts are excluded.
4. Another user's receipts are excluded.
5. A user with no receipts receives `[]`.
6. `get_user_receipt_by_id()` returns an owned receipt.
7. Unknown receipt ID returns `None`.
8. Another user's receipt returns `None`.
9. Soft-deleted receipt returns `None`.
10. `delete_user_receipt()` sets `deleted_at`.
11. Soft-deleted database row still exists.
12. Physical file still exists after soft delete.
13. Deleting an unknown receipt returns `False`.
14. Deleting another user's receipt returns `False`.

Use `smart_receipt_db_test`.

Use temporary upload directories for any test files.

---

# 5. Route Tests

Update:

```text
backend/tests/test_receipt_routes.py
```

Keep existing upload tests.

Add tests for:

1. Authenticated user can list their receipts.
2. List route returns `200`.
3. List route returns an array.
4. List route returns only the authenticated user's receipts.
5. List route excludes soft-deleted receipts.
6. List route returns newest receipts first.
7. Empty list returns `200` and `[]`.
8. Missing access token on list route returns `401`.
9. Authenticated user can get their receipt by ID.
10. Unknown receipt ID returns `404`.
11. Another user's receipt returns `404`.
12. Soft-deleted receipt returns `404`.
13. Authenticated user can soft-delete their receipt.
14. Delete response contains `"Receipt deleted successfully"`.
15. Deleted receipt cannot be retrieved afterward.
16. Deleted receipt does not appear in the list afterward.
17. Another user cannot delete the receipt and receives `404`.
18. Missing access token on detail/delete returns `401`.
19. Response never contains `file_path`.
20. Existing upload, auth, health, and category tests still pass in the full suite.

---

# 6. Test Isolation

All tests must use:

```text
smart_receipt_db_test
```

Never use:

```text
smart_receipt_db
```

Continue overriding `get_db`.

Clean only test records and temporary test files.

Do not delete development uploads.

---

# 7. Security Requirements

1. Always filter by `current_user.id`.
2. Never trust a receipt ID alone.
3. Return `404` for another user's receipt.
4. Do not expose internal `file_path`.
5. Do not include soft-deleted receipts.
6. Use soft delete with `deleted_at`.
7. Do not remove physical files yet.
8. Do not return deleted records after deletion.

---

# 8. Verification Commands

Run from the `backend` folder with the virtual environment active:

```bash
python -m compileall app tests
```

Run receipt service tests:

```bash
pytest tests/test_receipt_service.py
```

Run receipt route tests:

```bash
pytest tests/test_receipt_routes.py
```

Run the full suite:

```bash
pytest
```

Optionally verify in Swagger:

```text
http://127.0.0.1:8000/docs
```

Confirm these receipt routes appear:

```text
POST   /api/receipts/upload
GET    /api/receipts
GET    /api/receipts/{receipt_id}
DELETE /api/receipts/{receipt_id}
```

---

# Do Not Implement Yet

Do not implement:

- `PUT /api/receipts/{receipt_id}`
- Receipt metadata editing
- Permanent database deletion
- Physical-file deletion
- Public file download
- Receipt image serving
- Pagination
- Search
- Date filtering
- Status filtering
- Gemini extraction
- OCR
- Expense creation
- Expense items
- Translation
- Excel export
- Frontend pages

---

# Expected Final Result

After this step, the project should have:

- Protected receipt list endpoint
- Protected receipt detail endpoint
- Protected receipt soft-delete endpoint
- Strict receipt ownership
- Newest-first receipt list
- Soft-deleted receipts hidden
- Physical files preserved
- Service tests
- Route tests
- Existing upload endpoint unchanged
- No receipt edit or AI processing yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Service functions added
3. Routes added
4. Ownership rules implemented
5. Soft-delete behavior
6. Receipt service test result
7. Receipt route test result
8. Full test-suite result
9. Any issue or model mismatch

Do not produce a long walkthrough unless an error occurs.
