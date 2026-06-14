# Smart Receipt Project — Step 10: Expense and Expense Item Schemas

## Goal

Implement only the Pydantic schemas and validation rules for expenses and expense items.

This step must define the request and response data structures that will be used later by the expense service and API routes.

Do not implement database queries, services, routes, Gemini extraction, receipt processing, Excel export, or frontend code yet.

Keep the code simple, readable, and easy for a student to explain.

---

## Project Status

The project already has:

- Database models and migrations
- Authentication system
- Current-user dependency
- Protected category read endpoints
- Protected receipt upload
- Receipt list, detail, and soft delete
- Separate MySQL test database
- 162 tests passing

Inspect the existing `Expense` and `ExpenseItem` SQLAlchemy models before writing schemas.

Do not rebuild completed features.

---

## Why This Step Comes Next

The expense feature will connect:

```text
User
→ Expense
→ Category
→ Optional Receipt File
→ Expense Items
```

The schemas will define:

```text
What the frontend sends
What validation happens before service logic
What the API safely returns
```

This step covers only schema validation.

---

## Important Coding Style

Follow these rules:

1. Use clear schema names.
2. Use simple Pydantic v2 code.
3. Use built-in validation where possible.
4. Avoid unnecessary custom validators.
5. Avoid complicated inheritance.
6. Keep request and response schemas separate.
7. Use type hints.
8. Add only short, useful comments.
9. Do not query the database.
10. Do not validate ownership here.
11. Do not check whether category or receipt records exist here.
12. Do not calculate totals automatically unless the existing project already requires it.
13. Do not add extra fields not found in the models.
14. Do not change database models unless a real mismatch is discovered.
15. Do not create migrations in this step.

---

## Expected Files

Create or update:

```text
backend/app/schemas/
├── __init__.py
├── expense.py
└── expense_item.py

backend/tests/
├── test_expense_schemas.py
└── test_expense_item_schemas.py
```

If schema files already exist as placeholders, update them instead of creating duplicates.

---

# 1. Inspect Existing Models First

Inspect the actual files, likely:

```text
backend/app/models/expense.py
backend/app/models/expense_item.py
```

Use the exact field names and types from the existing models.

Also inspect:

```text
backend/app/models/category.py
backend/app/models/receipt_file.py
```

to understand foreign-key relationships.

Do not assume the model fields from this task are exact.

At completion, report the actual fields found.

---

# 2. Expense Item Schemas

Create in:

```text
backend/app/schemas/expense_item.py
```

Recommended schemas:

```text
ExpenseItemCreate
ExpenseItemUpdate
ExpenseItemResponse
```

---

## `ExpenseItemCreate`

### Purpose

Validate one item sent when creating an expense.

Use only fields that exist in the `ExpenseItem` model.

Likely fields may include:

```text
name
quantity
unit_price
total_price
description
```

Possible structure:

```python
class ExpenseItemCreate(BaseModel):
    name: str
    quantity: Decimal
    unit_price: Decimal | None = None
    total_price: Decimal
```

Adapt this to the real model.

### Validation Rules

- `name` must not be empty or whitespace-only.
- `name` should have a reasonable maximum length matching the model.
- `quantity` must be greater than `0`.
- `unit_price` must not be negative when present.
- `total_price` must not be negative.
- Optional text fields should respect model length limits.
- Trim leading and trailing spaces from item names when simple to implement.

Do not calculate:

```text
quantity × unit_price
```

automatically unless that is already an explicit project rule.

Do not reject small decimal differences in this schema.

---

## `ExpenseItemUpdate`

### Purpose

Validate partial item updates later.

All fields must be optional.

Use the same validation rules as create when a field is provided.

Example concept:

```python
class ExpenseItemUpdate(BaseModel):
    name: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
```

Do not include:

```text
id
expense_id
created_at
updated_at
deleted_at
```

---

## `ExpenseItemResponse`

### Purpose

Return safe expense-item data.

Use actual model fields.

Likely fields may include:

```text
id
expense_id
name
quantity
unit_price
total_price
created_at
updated_at
```

Do not expose:

```text
deleted_at
internal relationships
```

Configure Pydantic v2 for SQLAlchemy objects:

```python
model_config = ConfigDict(from_attributes=True)
```

---

# 3. Expense Schemas

Create in:

```text
backend/app/schemas/expense.py
```

Recommended schemas:

```text
ExpenseCreate
ExpenseUpdate
ExpenseResponse
```

---

## `ExpenseCreate`

### Purpose

Validate data sent when creating an expense.

Use only real fields from the `Expense` model.

Likely fields may include:

```text
category_id
receipt_file_id
merchant_name
expense_date
currency
subtotal
tax_amount
total_amount
notes
items
```

Possible structure:

```python
class ExpenseCreate(BaseModel):
    category_id: int
    receipt_file_id: int | None = None
    merchant_name: str | None = None
    expense_date: date
    currency: str = "THB"
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal
    notes: str | None = None
    items: list[ExpenseItemCreate] = []
```

Adapt this to the real model.

### Important List Rule

Do not use a mutable list default like:

```python
items: list[ExpenseItemCreate] = []
```

Use:

```python
Field(default_factory=list)
```

when an empty list default is needed.

### Validation Rules

- `category_id` must be a positive integer.
- `receipt_file_id`, when present, must be a positive integer.
- `merchant_name`, when present, must not be whitespace-only.
- `merchant_name` must respect the model length limit.
- `expense_date` must be a valid date or datetime matching the model.
- `currency` must be trimmed and converted to uppercase.
- `currency` should be exactly 3 letters when the model uses ISO-style codes.
- `subtotal`, when present, must not be negative.
- `tax_amount`, when present, must not be negative.
- `total_amount` must not be negative.
- `notes`, when present, must respect the model length or text type.
- `items` should default to an empty list when supported.

Do not check whether:

```text
category exists
receipt exists
receipt belongs to the user
```

Those are service-layer business rules for the next step.

Do not compare subtotal, tax, and total unless the project has a confirmed calculation rule.

---

## `ExpenseUpdate`

### Purpose

Validate partial expense updates later.

All fields must be optional.

Use the same validation rules as `ExpenseCreate` when fields are provided.

Likely fields:

```text
category_id
receipt_file_id
merchant_name
expense_date
currency
subtotal
tax_amount
total_amount
notes
items
```

Be careful with `receipt_file_id`:

```text
missing field
```

and:

```text
receipt_file_id = null
```

may have different meanings later.

Keep the schema simple for now, but do not introduce complicated sentinel values unless truly needed.

Do not include:

```text
id
user_id
created_at
updated_at
deleted_at
AI internal fields
```

unless they are intentionally editable in the existing requirements.

---

## `ExpenseResponse`

### Purpose

Return safe expense data.

Use actual model fields.

Likely safe fields may include:

```text
id
user_id
category_id
receipt_file_id
merchant_name
expense_date
currency
subtotal
tax_amount
total_amount
notes
created_at
updated_at
items
```

Include:

```text
items: list[ExpenseItemResponse]
```

only if the existing SQLAlchemy relationship is configured and this remains simple.

If including nested items would cause lazy-loading or circular-import problems, report it and keep the first response schema simple.

Do not expose:

```text
deleted_at
internal AI prompts
internal relationships
server paths
```

Configure:

```python
model_config = ConfigDict(from_attributes=True)
```

---

# 4. Decimal Handling

Use:

```python
from decimal import Decimal
```

for money fields.

Do not use `float` for stored money values.

This avoids common rounding problems.

Use Pydantic constraints such as:

```text
greater than or equal to 0
```

where simple.

Do not add manual rounding unless required by the existing model.

---

# 5. Currency Validation

Keep currency validation simple.

Recommended rules:

```text
Required or default based on actual model
Exactly 3 alphabetic characters
Converted to uppercase
```

Valid examples:

```text
THB
USD
MMK
```

Invalid examples:

```text
th
US
123
USDD
```

Do not create a large currency enum in this step.

---

# 6. Date Validation

Match the actual model type.

Use:

```python
date
```

when the model stores only a calendar date.

Use:

```python
datetime
```

when the model stores date and time.

Do not invent timezone conversion rules in the schema.

---

# 7. Update Schema Package Exports

Update:

```text
backend/app/schemas/__init__.py
```

Expose:

```text
ExpenseItemCreate
ExpenseItemUpdate
ExpenseItemResponse
ExpenseCreate
ExpenseUpdate
ExpenseResponse
```

Use simple imports.

Do not create complicated `__all__` logic unless already used by the project.

---

# 8. Expense Item Schema Tests

Create:

```text
backend/tests/test_expense_item_schemas.py
```

Test only schema validation.

Do not connect to MySQL.

Include tests based on actual model fields:

1. Valid item creation.
2. Empty item name rejected.
3. Whitespace-only item name rejected.
4. Quantity equal to zero rejected.
5. Negative quantity rejected.
6. Negative unit price rejected.
7. Negative total price rejected.
8. Valid partial update.
9. Empty update accepted.
10. Response schema loads from a SQLAlchemy-like object.
11. Response does not expose `deleted_at`.

Keep tests simple.

---

# 9. Expense Schema Tests

Create:

```text
backend/tests/test_expense_schemas.py
```

Test only schema validation.

Do not connect to MySQL.

Include tests based on actual fields:

1. Valid expense creation.
2. Positive category ID required.
3. Invalid receipt ID rejected when provided.
4. Negative subtotal rejected.
5. Negative tax amount rejected.
6. Negative total amount rejected.
7. Valid three-letter currency accepted.
8. Lowercase currency is normalized to uppercase.
9. Invalid currency length rejected.
10. Non-alphabetic currency rejected.
11. Whitespace-only merchant name rejected when provided.
12. Expense with no items defaults safely to an empty list.
13. Expense with valid nested items accepted.
14. Invalid nested item rejected.
15. Valid partial update.
16. Empty update accepted.
17. Response schema loads from a SQLAlchemy-like object.
18. Response does not expose `deleted_at`.

Only add tests relevant to actual model fields.

---

# 10. Verification Commands

Run from the `backend` folder with the virtual environment active:

```bash
python -m compileall app tests
```

Run expense-item schema tests:

```bash
pytest tests/test_expense_item_schemas.py
```

Run expense schema tests:

```bash
pytest tests/test_expense_schemas.py
```

Run the full suite:

```bash
pytest
```

---

# Do Not Implement Yet

Do not implement:

- Expense service
- Expense database queries
- `POST /api/expenses`
- Expense list/detail/update/delete routes
- Category existence checks
- Receipt ownership checks
- Automatic total calculation
- Receipt-to-expense linking logic
- Gemini extraction
- OCR
- Translation
- Excel export
- Frontend pages

---

# Expected Final Result

After this step, the project should have:

- Expense item create schema
- Expense item update schema
- Expense item response schema
- Expense create schema
- Expense update schema
- Expense response schema
- Money validation using `Decimal`
- Currency normalization and validation
- Nested item validation when appropriate
- Schema-only tests
- No database or route logic yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Actual `Expense` model fields found
3. Actual `ExpenseItem` model fields found
4. Schemas created
5. Validation rules implemented
6. Whether nested items are included in `ExpenseResponse`
7. Expense-item schema test result
8. Expense schema test result
9. Full test-suite result
10. Any model mismatch or issue found

Do not produce a long walkthrough unless an error occurs.
