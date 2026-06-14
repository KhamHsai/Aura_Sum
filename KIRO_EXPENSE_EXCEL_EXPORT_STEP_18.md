# Smart Receipt Project — Step 18: Export Expenses to Excel

## Goal

Implement a protected backend endpoint that exports the authenticated user’s expenses to an Excel file.

Create:

```text
GET /api/expenses/export
```

The backend must generate a valid `.xlsx` workbook in memory and return it as a downloadable response.

The frontend will later add an Export button that calls this endpoint.

Write simple, human-readable code that is easy to understand and explain. Use clear names and straightforward logic. Avoid unnecessary abstractions, complex patterns, generic export frameworks, and overengineering.

---

## Project Status

The project already has:

- Authentication and current-user dependency
- Protected category endpoints
- Receipt upload, management, Gemini extraction, link, and unlink
- Expense create, list, detail, update, soft delete, and confirm
- English–Thai dynamic translation
- Expense items
- 578 tests passing

Inspect the existing files before changing anything:

```text
Expense model
ExpenseItem model
Category model
Expense service
Expense routes
Current-user dependency
Existing tests
requirements.txt
```

Do not rebuild completed features.

---

# Scope

Implement only:

```text
GET /api/expenses/export
Excel workbook generation
Authenticated-user filtering
Two worksheets
In-memory file response
Export tests
```

Do not implement:

```text
Frontend Export button
Date filters
Category filters
Batch jobs
CSV export
PDF export
Email delivery
Cloud storage
Temporary saved export files
```

---

# Important Coding Style

1. Write simple, human-readable code.
2. Make the code easy for a student to understand and explain.
3. Use clear function and variable names.
4. Keep route functions thin.
5. Put workbook generation in the service layer.
6. Do not add export classes or factories.
7. Do not add generic report frameworks.
8. Generate the workbook in memory.
9. Do not save export files permanently.
10. Enforce current-user ownership.
11. Exclude soft-deleted expenses and items.
12. Do not expose sensitive/internal fields.

---

# 1. Dependency

Inspect `requirements.txt`.

Use:

```text
openpyxl
```

If it is already installed, reuse it.

If it is not installed, add it to the project dependency file.

Do not add multiple Excel libraries.

---

# 2. Endpoint

Create:

```text
GET /api/expenses/export
```

Swagger summary:

```text
Export Expenses to Excel
```

The endpoint must require:

```python
db: Session = Depends(get_db)
current_user: User = Depends(get_current_user)
```

The route should only:

```text
1. Call the export service
2. Build the downloadable response
3. Return the file
```

Do not query the database directly in the route.

---

# 3. Route Ordering Warning

The project already has:

```text
GET /api/expenses/{expense_id}
```

Make sure:

```text
GET /api/expenses/export
```

is registered before:

```text
GET /api/expenses/{expense_id}
```

so FastAPI does not treat `export` as an `expense_id`.

Add a route test for this.

---

# 4. Service Function

Add a simple service function such as:

```python
def export_user_expenses_to_excel(
    db: Session,
    user_id: int,
) -> BytesIO:
    ...
```

Returning workbook bytes is also acceptable:

```python
def export_user_expenses_to_excel(
    db: Session,
    user_id: int,
) -> bytes:
    ...
```

Choose the simplest approach.

The function should:

```text
1. Query the authenticated user’s active expenses
2. Load active expense items
3. Create an openpyxl Workbook
4. Add Expenses worksheet
5. Add Expense Items worksheet
6. Apply simple formatting
7. Save workbook to BytesIO
8. Reset stream position to zero
9. Return the stream
```

---

# 5. Ownership and Filtering

Export only:

```text
Expense.user_id == user_id
Expense.deleted_at is null
```

For expense items, export only:

```text
ExpenseItem.deleted_at is null
```

Do not export another user’s data.

Do not export soft-deleted rows.

---

# 6. Ordering

Use stable ordering.

Recommended expense ordering:

```text
created_at ascending
id ascending
```

or:

```text
created_at descending
id descending
```

Choose one and test it.

Recommended item ordering:

```text
expense_id ascending
id ascending
```

Keep the output predictable.

---

# 7. Workbook Structure

Create two worksheets:

```text
Expenses
Expense Items
```

Remove the default empty worksheet if necessary.

---

# 8. Expenses Worksheet

Use these columns where the real model supports them:

```text
Expense ID
Receipt Date
Receipt Time
Title
Merchant Name
Category
Receipt Number
Document Type
Payment Method
Currency
Subtotal
Tax Amount
Discount Amount
Total Amount
Input Method
Language
Confirmed
Notes
Created At
Updated At
```

Do not export:

```text
user_id
ai_raw_response
deleted_at
local file path
API keys
password data
token data
```

For category, export a readable category name.

Preferred category display:

```text
name_en
```

If unavailable:

```text
name_th
```

If expense category is null:

```text
Uncategorized
```

Do not expose only the raw category ID unless useful.

---

# 9. Expense Items Worksheet

Use these columns where supported:

```text
Expense ID
Item ID
Original Name
English Name
Thai Name
Category
Quantity
Unit
Unit Price
Discount Amount
Total Price
Created At
Updated At
```

Do not include soft-deleted items.

For item category, use a readable category name.

If item category is null:

```text
Uncategorized
```

---

# 10. Data Formatting

## Money

Apply a two-decimal number format:

```text
0.00
```

Use numeric Excel cells for Decimal values.

Do not convert all money values into formatted strings.

## Dates

Use readable Excel date formatting:

```text
yyyy-mm-dd
```

## Times

Use:

```text
hh:mm:ss
```

## Date and time values

Use native Python date, time, or datetime values where openpyxl supports them.

## Boolean

Export confirmation as a readable value:

```text
Yes
No
```

or native boolean values.

Choose one consistent approach.

## Null values

Use an empty cell for missing optional values, except category where `Uncategorized` is clearer.

---

# 11. Simple Worksheet Styling

Apply simple formatting:

```text
Bold header row
Freeze first row
Auto-filter on header row
Reasonable column widths
```

Optional:

```text
Center some short columns
Wrap long notes cells
```

Do not create complex colors, charts, logos, merged cells, or print layouts.

Keep it clean and understandable.

---

# 12. Empty Export

When the user has no expenses:

```text
Return a valid workbook
Include both worksheets
Include header rows
Include no data rows
```

Do not return `404`.

Do not return an empty byte response.

---

# 13. Download Response

Return a streaming or normal response with the correct Excel MIME type:

```text
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

Use a filename such as:

```text
smart_receipt_expenses_YYYY-MM-DD.xlsx
```

Example:

```text
smart_receipt_expenses_2026-06-14.xlsx
```

Set:

```text
Content-Disposition: attachment; filename="..."
```

Use the project’s current UTC/local-date convention consistently.

---

# 14. Suggested Route Shape

Conceptually:

```python
@router.get(
    "/export",
    summary="Export Expenses to Excel",
)
def export_expenses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_stream = export_user_expenses_to_excel(db, current_user.id)

    filename = ...

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
```

Use the existing project style.

---

# 15. Error Handling

If workbook generation fails unexpectedly:

```text
Roll back only if the service made database writes
Return a safe server error
Do not expose internal paths or database details
```

The export service should not write to the database.

Do not create export-history records in this step.

---

# 16. Service Tests

Create or update tests for:

1. Export returns a `BytesIO` or bytes object.
2. Returned workbook can be opened by openpyxl.
3. Workbook contains `Expenses`.
4. Workbook contains `Expense Items`.
5. Expenses sheet contains expected headers.
6. Expense Items sheet contains expected headers.
7. Only the current user’s expenses are exported.
8. Another user’s expenses are excluded.
9. Soft-deleted expenses are excluded.
10. Soft-deleted items are excluded.
11. Active items are included.
12. Null expense category displays `Uncategorized`.
13. Null item category displays `Uncategorized`.
14. Category name is readable.
15. Decimal values are written as numeric values.
16. Money cells use two-decimal formatting.
17. Dates use the expected format.
18. Header rows are frozen.
19. Auto-filter exists.
20. Empty user export returns a valid workbook with headers.
21. `ai_raw_response` is not exported.
22. `deleted_at` is not exported.
23. Local receipt paths are not exported.
24. Stable ordering is used.
25. No database rows are created or modified.

Use `smart_receipt_db_test`.

---

# 17. Route Tests

Add tests for:

1. Authenticated user can export.
2. Export returns `200`.
3. Response MIME type is correct.
4. Content-Disposition contains `.xlsx`.
5. Response body is a valid Excel workbook.
6. Workbook contains both worksheets.
7. Only current user data appears.
8. Another user’s data does not appear.
9. Soft-deleted data does not appear.
10. Empty export returns a valid workbook.
11. Missing token returns `401`.
12. Invalid token returns `401`.
13. `/api/expenses/export` is not treated as `{expense_id}`.
14. Sensitive/internal fields are not included.
15. Existing full test suite remains green.

---

# 18. Test Isolation

All database tests must use:

```text
smart_receipt_db_test
```

Do not use the development database.

Override `get_db`.

Clean dependent data in foreign-key-safe order.

Do not create permanent files during tests.

Load workbook data directly from response bytes.

---

# 19. Verification Commands

Run from the backend folder:

```bash
python -m compileall app tests
```

Run export service tests:

```bash
pytest tests/test_expense_export_service.py
```

Run export route tests:

```bash
pytest tests/test_expense_export_routes.py
```

Run the full suite:

```bash
pytest
```

Optionally verify in Swagger:

```text
GET /api/expenses/export
```

Confirm the browser downloads a valid `.xlsx` file.

---

# Do Not Implement Yet

Do not implement:

- Frontend Export button
- Export filters
- CSV export
- PDF export
- Emailing exports
- Export history
- Cloud storage
- Charts
- Dashboard reports
- Background export jobs

---

# Expected Result

After this step, the backend should have:

- Protected Excel export endpoint
- Current-user-only export
- Two clean worksheets
- Active expenses and items only
- Readable categories
- Money and date formatting
- In-memory workbook generation
- Valid empty export
- Service tests
- Route tests
- No frontend export button yet

---

# Required Completion Report

Provide:

1. Changed file list
2. Excel library used
3. Service function added
4. Route added
5. Worksheet names
6. Expense columns
7. Expense-item columns
8. Ownership and soft-delete filtering
9. Ordering used
10. Formatting applied
11. Empty-export behavior
12. Response MIME type and filename
13. Service test result
14. Route test result
15. Full test-suite result
16. Any model or dependency mismatch

Do not produce a long walkthrough unless an error occurs.
