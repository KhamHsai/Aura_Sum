# Smart Receipt Project — Step 11: Create Expense Service and Route

## Goal

Implement only expense creation.

Create:

```text
POST /api/expenses
```

The authenticated user should be able to create one expense with optional expense items.

Keep the code simple, readable, and easy for a student to explain.

Do not implement expense list, detail, update, delete, receipt linking, Gemini extraction, translation, Excel export, or frontend code yet.

---

## Project Status

The project already has:

- Database models and migrations
- Authentication system
- Current-user dependency
- Protected category read endpoints
- Receipt upload, list, detail, and soft delete
- Expense and expense-item Pydantic schemas
- Separate MySQL test database
- 195 tests passing

Inspect the existing models, schemas, and relationships before making changes.

Do not rebuild completed features.

---

## Architecture

Use this flow:

```text
Authenticated request
→ Expense route
→ Expense service
→ Expense and ExpenseItem models
→ MySQL
```

Routes must stay thin.

All business validation and database work must stay in the service layer.

---

## Important Coding Style

Follow these rules:

1. Use simple functions.
2. Keep route functions thin.
3. Use direct SQLAlchemy queries inside the service.
4. Reuse the existing `ExpenseCreate` and `ExpenseResponse` schemas.
5. Reuse `get_current_user`.
6. Do not add a repository layer.
7. Do not add service classes.
8. Do not add generic CRUD base classes.
9. Do not add automatic AI processing.
10. Do not add receipt linking yet.
11. Do not accept AI/internal fields from request data.
12. Use one database transaction for the expense and all items.
13. Roll back everything if any item creation fails.
14. Use type hints.
15. Add only short, useful comments.

---

## Expected Files

Create or update only what is needed:

```text
backend/app/services/
├── __init__.py
└── expense_service.py

backend/app/routes/
├── __init__.py
└── expenses.py

backend/app/main.py

backend/tests/
├── test_expense_service.py
└── test_expense_routes.py
```

If any files already exist as placeholders, update them instead of creating duplicates.

---

# 1. Inspect Existing Models and Schemas

Inspect:

```text
backend/app/models/expense.py
backend/app/models/expense_item.py
backend/app/models/category.py
backend/app/schemas/expense.py
backend/app/schemas/expense_item.py
```

Use the exact model and schema field names.

Important actual Expense fields already found:

```text
id
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
notes
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

Important actual ExpenseItem fields already found:

```text
id
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
created_at
updated_at
deleted_at
```

Do not invent `receipt_file_id`; it does not exist on the Expense model.

---

# 2. Create `backend/app/services/expense_service.py`

Create:

```text
ExpenseServiceError
create_expense
```

---

## `ExpenseServiceError`

Use a small service exception:

```python
class ExpenseServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
```

Do not create a large exception hierarchy.

Suggested status codes:

```text
Invalid category: 400 or 404
Invalid item category: 400 or 404
Database failure: allow original error to re-raise
```

Use the project's current error style consistently.

---

## `create_expense`

### Purpose

Create one expense and its optional items for the authenticated user.

### Recommended Signature

```python
def create_expense(
    db: Session,
    user_id: int,
    data: ExpenseCreate,
) -> Expense:
    ...
```

Adapt the exact type imports to the current project.

---

## Required Process

Use this order:

```text
1. Validate the main expense category
2. Validate each optional item category
3. Create the Expense model using current user ID
4. Add and flush the expense to obtain expense.id
5. Create ExpenseItem records using expense.id
6. Add all items
7. Commit once
8. Refresh the expense
9. Ensure items are available for ExpenseResponse
10. Return the expense
```

Use one transaction.

Do not commit the expense before all items are ready.

---

# 3. Main Category Validation

The main expense category must:

```text
exist
be active
not be soft-deleted
```

Use the existing category model or category service.

A simple direct query in `expense_service.py` is acceptable.

Do not use an inactive or deleted category.

Use a simple error message:

```text
Category not found
```

Do not expose whether it was inactive or deleted.

---

# 4. Expense Item Category Validation

Each expense item may have its own `category_id`.

If an item category is provided, it must:

```text
exist
be active
not be soft-deleted
```

Use:

```text
Item category not found
```

or another simple consistent message.

Do not create any expense or items if any category validation fails.

---

# 5. Create the Expense Record

Use only request fields allowed by `ExpenseCreate`.

Always set:

```text
user_id = current authenticated user ID
```

Never accept `user_id` from the client.

Do not accept or set these request-controlled internal fields:

```text
ai_confidence
ai_status
ai_raw_response
language_detected
deleted_at
created_at
updated_at
```

For internal fields required by the model:

- Use the model default where possible.
- If `input_method` requires a value, use `"manual"` only if the model or existing project supports that value.
- If `is_confirmed` requires a value, use the existing model default.

Do not invent unsupported enum values.

---

# 6. Create Expense Items

For every item in:

```text
data.items
```

create an `ExpenseItem` record.

Always set:

```text
expense_id = created expense.id
```

Use only fields allowed by `ExpenseItemCreate`.

Do not accept:

```text
id
expense_id
created_at
updated_at
deleted_at
```

from the client.

If no items are provided:

```text
Create the expense with an empty item list
```

This is valid.

---

# 7. Transaction Handling

Use one transaction for both expense and items.

Recommended concept:

```python
try:
    db.add(expense)
    db.flush()

    for item_data in data.items:
        db.add(ExpenseItem(expense_id=expense.id, ...))

    db.commit()
    db.refresh(expense)
    return expense

except Exception:
    db.rollback()
    raise
```

Do not call `commit()` inside the item loop.

If item creation fails:

```text
Expense must not remain in the database
No partial item records may remain
```

---

# 8. Loading Nested Items

`ExpenseResponse` includes:

```text
items: list[ExpenseItemResponse]
```

The SQLAlchemy relationship may be named:

```text
expense_items
```

Inspect the actual model relationship.

Ensure the returned expense can be serialized correctly.

Use the simplest approach compatible with the existing model:

- Refresh the expense and access the relationship, or
- Re-query the expense with eager-loaded items.

Do not create complicated loading abstractions.

Do not rename the database relationship.

---

# 9. Update `backend/app/services/__init__.py`

Expose:

```text
ExpenseServiceError
create_expense
```

Use simple imports.

---

# 10. Create `backend/app/routes/expenses.py`

Create a protected router:

```python
router = APIRouter(
    prefix="/api/expenses",
    tags=["Expenses"],
)
```

Create only one route in this step.

---

## Create Expense Route

### Endpoint

```text
POST /api/expenses
```

### Swagger Summary

```text
Create Expense
```

### Request Model

```text
ExpenseCreate
```

### Response Model

```text
ExpenseResponse
```

### Success Status

```text
201 Created
```

### Dependencies

```python
db: Session = Depends(get_db)
current_user: User = Depends(get_current_user)
```

### Route Responsibilities

The route should only:

```text
1. Receive validated ExpenseCreate data
2. Call create_expense(db, current_user.id, data)
3. Convert ExpenseServiceError to HTTPException
4. Return the created expense
```

Do not query the database inside the route.

Do not validate categories inside the route.

Do not create items inside the route.

---

# 11. Update Router Registration

Update:

```text
backend/app/routes/__init__.py
backend/app/main.py
```

Expose and include the expenses router.

Do not remove or modify existing:

```text
Health routes
Authentication routes
Category routes
Receipt routes
```

After implementation, Swagger should show:

```text
POST /api/expenses
```

---

# 12. Expense Service Tests

Create:

```text
backend/tests/test_expense_service.py
```

Use:

```text
smart_receipt_db_test
```

Include tests for:

1. Successful expense creation.
2. Created expense belongs to the correct user.
3. Main category is stored correctly.
4. Money fields are stored correctly.
5. Currency is stored uppercase.
6. Expense with no items is created successfully.
7. Expense with one item is created successfully.
8. Expense with multiple items is created successfully.
9. Created items use the correct expense ID.
10. Invalid main category is rejected.
11. Inactive main category is rejected.
12. Soft-deleted main category is rejected.
13. Invalid item category is rejected.
14. Inactive item category is rejected.
15. Soft-deleted item category is rejected.
16. If one item fails, no expense remains in the database.
17. If one item fails, no partial items remain.
18. Internal AI fields cannot be set through `ExpenseCreate`.
19. Returned expense includes nested items.
20. User ID always comes from the service argument, not request data.

Keep tests readable.

---

# 13. Expense Route Tests

Create:

```text
backend/tests/test_expense_routes.py
```

Use FastAPI `TestClient`.

Use:

```text
smart_receipt_db_test
```

Continue overriding `get_db`.

Include tests for:

1. Authenticated user can create an expense.
2. Successful creation returns `201`.
3. Response contains the current user's ID.
4. Response contains the correct category.
5. Response includes an empty items list when no items are sent.
6. Response includes created nested items.
7. Missing access token returns `401`.
8. Invalid access token returns `401`.
9. Invalid request schema returns `422`.
10. Invalid main category returns the service error status.
11. Inactive category is rejected.
12. Soft-deleted category is rejected.
13. Invalid item category is rejected.
14. Another user cannot control the created expense owner.
15. Response does not expose `deleted_at`.
16. Response does not expose internal AI fields.
17. Existing auth, category, and receipt routes still pass in the full suite.

---

# 14. Security and Business Rules

1. The current authenticated user always owns the expense.
2. Never accept `user_id` from request data.
3. Main category must be active and non-deleted.
4. Item categories must be active and non-deleted.
5. Use one transaction.
6. Roll back all records on failure.
7. Do not expose AI/internal fields.
8. Do not link receipts yet.
9. Do not create AI data automatically.
10. Do not calculate totals automatically unless already required.

---

# 15. Verification Commands

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

---

# Do Not Implement Yet

Do not implement:

- `GET /api/expenses`
- `GET /api/expenses/{id}`
- `PUT /api/expenses/{id}`
- `DELETE /api/expenses/{id}`
- Receipt linking
- Receipt download
- Gemini extraction
- OCR
- Translation
- Excel export
- Pagination
- Search
- Filters
- Dashboard statistics
- Frontend pages

---

# Expected Final Result

After this step, the project should have:

- Expense creation service
- Optional nested item creation
- Category business validation
- One database transaction
- Rollback on failure
- Protected `POST /api/expenses`
- Expense service tests
- Expense route tests
- No expense CRUD beyond create
- No receipt linking or AI processing yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Service functions and exception created
3. Route created
4. Category validation behavior
5. Transaction and rollback behavior
6. Nested item behavior
7. Expense service test result
8. Expense route test result
9. Full test-suite result
10. Any model mismatch or issue found

Do not produce a long walkthrough unless an error occurs.
