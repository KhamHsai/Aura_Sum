# Smart Receipt Project — Step 8: Protected Receipt File Upload

## Goal

Implement only the protected receipt file-upload feature.

Create:

```text
POST /api/receipts/upload
```

An authenticated user should be able to upload one receipt image or PDF. The backend must validate the file, save it safely on the server, create a `receipt_files` database record, and return safe receipt-file information.

Keep the code simple and human-readable.

Do not implement Gemini extraction, OCR, expense creation, receipt list/detail/delete routes, translation, Excel export, or frontend code yet.

---

## Project Status

The project already has:

- MySQL database and Alembic migrations
- SQLAlchemy models
- Authentication schemas, services, and routes
- JWT access and refresh tokens
- `get_current_user` dependency
- Protected `GET /api/auth/me`
- Protected category read endpoints
- Separate test database: `smart_receipt_db_test`
- 87 tests passing

Inspect the existing project before changing anything.

Do not rebuild completed authentication or category functionality.

---

## Feature Flow

```text
Authenticated user
→ Upload receipt image or PDF
→ Validate file name, type, and size
→ Generate a unique stored filename
→ Save file locally
→ Create receipt_files database record
→ Return safe receipt-file information
```

Every uploaded file must belong to the authenticated user:

```text
receipt_file.user_id = current_user.id
```

---

## Important Coding Style

Follow these rules:

1. Use simple functions instead of unnecessary classes.
2. Keep route functions thin.
3. Put file validation and filename helpers in a utility file.
4. Put database business logic in a service file.
5. Use clear variable and function names.
6. Use type hints.
7. Add only short, useful comments.
8. Do not create a repository layer.
9. Do not create generic storage abstractions.
10. Do not add cloud storage.
11. Do not add background jobs.
12. Do not add AI processing.
13. Do not change database models unless a real mismatch prevents implementation.
14. Do not create a migration unless the existing `ReceiptFile` table genuinely lacks a required field.
15. Reuse the existing database session and `get_current_user` dependency.

---

## Expected Files

Create or update only what is needed:

```text
backend/app/schemas/
├── __init__.py
└── receipt.py

backend/app/utils/
├── __init__.py
└── file_utils.py

backend/app/services/
├── __init__.py
└── receipt_service.py

backend/app/routes/
├── __init__.py
└── receipts.py

backend/app/config.py
backend/app/main.py
backend/.env.example
backend/requirements.txt

backend/tests/
├── test_file_utils.py
├── test_receipt_service.py
└── test_receipt_routes.py
```

If some files already exist as placeholders, update them instead of creating duplicates.

---

# 1. Inspect the Existing `ReceiptFile` Model

Before implementation, inspect the actual model, likely located at:

```text
backend/app/models/receipt_file.py
```

Use only fields that really exist.

Possible fields may include:

```text
id
user_id
original_filename
stored_filename
file_path
mime_type
file_size
processing_status
created_at
updated_at
deleted_at
```

Do not assume all of these names exist.

At completion, report the exact fields found.

Do not modify the model unless required.

---

# 2. File Upload Dependency

FastAPI file uploads require:

```text
python-multipart
```

Check whether it already exists in:

```text
backend/requirements.txt
```

If missing, add:

```text
python-multipart
```

Do not add unrelated dependencies.

---

# 3. Configuration

Add simple upload settings to `backend/app/config.py` and `backend/.env.example`.

Recommended settings:

```env
UPLOAD_DIR=uploads/receipts
MAX_RECEIPT_FILE_SIZE_MB=10
```

Use readable configuration names consistent with the current project.

The actual upload directory must come from configuration.

Do not hardcode an absolute path tied to one computer.

The application should create the directory when needed.

---

# 4. Allowed Receipt Files

Allow only:

```text
JPEG
PNG
WEBP
PDF
```

Allowed MIME types:

```text
image/jpeg
image/png
image/webp
application/pdf
```

Allowed extensions:

```text
.jpg
.jpeg
.png
.webp
.pdf
```

Validate both:

```text
MIME type
file extension
```

Reject the file when either one is unsupported.

This is basic validation for the first version. Do not build complex file-content scanning yet.

---

# 5. File Size Limit

Maximum file size:

```text
10 MB
```

Use the configuration value rather than hardcoding the byte count throughout the code.

Reject:

```text
Empty file
File larger than 10 MB
```

Use clear error messages.

Suggested messages:

```text
Receipt file is empty
Unsupported receipt file type
Receipt file is too large
Invalid receipt filename
```

---

# 6. Create `backend/app/utils/file_utils.py`

Create small reusable helpers.

Recommended functions:

```text
validate_receipt_file
generate_stored_filename
save_receipt_file
delete_saved_file
```

Use only functions that keep the code clear.

---

## `validate_receipt_file`

### Purpose

Validate:

```text
Original filename exists
Extension is allowed
MIME type is allowed
File is not empty
File size is within the configured limit
```

The function should not access the database.

It may receive:

```text
filename
content_type
file_bytes
max_size_bytes
```

Keep the signature simple.

Raise a small clear custom error or `ValueError` for invalid files.

Do not raise `HTTPException` from the utility layer.

---

## `generate_stored_filename`

### Purpose

Generate a safe unique filename.

Recommended format:

```text
UUID + original lowercase extension
```

Example:

```text
4cb1b7a9-1bd1-4da0-a731-a76c33345f87.pdf
```

Rules:

- Never use the original filename as the stored filename.
- Preserve only the validated lowercase extension.
- Prevent filename collisions.
- Do not include the user's email or username.

---

## `save_receipt_file`

### Purpose

Save validated bytes into the configured receipt upload directory.

Return useful stored information such as:

```text
stored_filename
file_path
```

Use normal Python file handling or `pathlib`.

Ensure the upload directory exists.

Do not save outside the configured upload directory.

---

## `delete_saved_file`

### Purpose

Remove a saved file if database creation fails after the file was written.

Behavior:

- If the file exists, delete it.
- If it does not exist, do nothing.
- Keep it small and safe.

This is cleanup logic, not a public delete-receipt feature.

---

# 7. Create `backend/app/schemas/receipt.py`

Create:

```text
ReceiptFileResponse
```

Use the actual model fields found.

Recommended safe fields, when available:

```text
id: int
user_id: int
original_filename: str
stored_filename: str
mime_type: str
file_size: int
processing_status: str
created_at: datetime
updated_at: datetime
```

Do not expose:

```text
deleted_at
absolute server file path
internal relationships
```

If `file_path` contains an internal server path, do not return it.

Configure Pydantic v2 for SQLAlchemy objects:

```python
model_config = ConfigDict(from_attributes=True)
```

Update `schemas/__init__.py` with a simple import.

---

# 8. Create `backend/app/services/receipt_service.py`

Create one main function:

```text
upload_receipt
```

A small service-specific exception is acceptable.

Recommended signature concept:

```python
def upload_receipt(
    db: Session,
    user_id: int,
    original_filename: str,
    content_type: str,
    file_bytes: bytes,
) -> ReceiptFile:
    ...
```

Adapt the signature to the existing project style.

---

## Required Upload Process

Use this order:

```text
1. Validate the file
2. Generate a unique stored filename
3. Save the file locally
4. Create the ReceiptFile database model
5. Set user_id to the authenticated user's ID
6. Set original and stored filename fields
7. Set MIME type and file size
8. Set initial processing status if the model supports it
9. Add and commit database record
10. Refresh and return the record
```

Suggested initial processing status:

```text
uploaded
```

Use the exact allowed value expected by the current model.

If the model has a different default or enum, follow it instead of inventing a new value.

---

## Database Failure Cleanup

If saving the database record fails after the physical file was saved:

```text
Rollback database transaction
Delete the saved physical file
Re-raise the error
```

Do not leave orphaned files.

Do not silently ignore database errors.

---

## Service Error Handling

If the project already has a simple service-error pattern, follow it.

Otherwise, a small exception is acceptable:

```python
class ReceiptServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
```

Do not build a large exception hierarchy.

Suggested statuses:

```text
Invalid file: 400
File too large: 413
Unsupported file type: 415
```

Keep behavior consistent and easy to explain.

---

# 9. Create `backend/app/routes/receipts.py`

Create:

```text
POST /api/receipts/upload
```

Router setup:

```python
router = APIRouter(
    prefix="/api/receipts",
    tags=["Receipts"],
)
```

---

## Upload Route

### Endpoint

```text
POST /api/receipts/upload
```

### Authentication

Require:

```python
current_user: User = Depends(get_current_user)
```

### Input

Use FastAPI:

```python
file: UploadFile = File(...)
```

### Response Model

```text
ReceiptFileResponse
```

### Success Status

```text
201 Created
```

### Route Responsibilities

The route should only:

```text
1. Receive UploadFile
2. Read file bytes once
3. Call upload_receipt(...)
4. Convert ReceiptServiceError to HTTPException
5. Return the created receipt-file record
```

Do not put database queries in the route.

Do not generate filenames in the route.

Do not perform AI processing in the route.

Close the uploaded file safely after reading.

---

# 10. Update Router Registration

Update:

```text
backend/app/routes/__init__.py
backend/app/main.py
```

Expose and include the receipts router.

Do not remove or change:

```text
Health routes
Authentication routes
Category routes
```

After implementation, Swagger should show:

```text
POST /api/receipts/upload
```

---

# 11. File Utility Tests

Create:

```text
backend/tests/test_file_utils.py
```

Use a temporary directory.

Do not write test files into the real upload directory.

Include tests for:

1. Valid JPEG accepted.
2. Valid PNG accepted.
3. Valid WEBP accepted.
4. Valid PDF accepted.
5. Unsupported extension rejected.
6. Unsupported MIME type rejected.
7. Missing filename rejected.
8. Empty file rejected.
9. Oversized file rejected.
10. Generated stored filename is unique.
11. Generated filename preserves the valid extension.
12. File saves inside the configured temporary directory.
13. Cleanup deletes an existing saved file.
14. Cleanup safely ignores a missing file.

Keep test files tiny.

---

# 12. Receipt Service Tests

Create:

```text
backend/tests/test_receipt_service.py
```

Use:

```text
smart_receipt_db_test
```

Use a temporary upload directory configured for tests.

Never write tests to the development upload directory.

Include tests for:

1. Successful receipt upload creates a database record.
2. Created record belongs to the correct user.
3. Original filename is stored.
4. Stored filename is different from the original.
5. File size and MIME type are stored.
6. Physical file exists after successful upload.
7. Unsupported file is rejected.
8. Oversized file is rejected.
9. No database record is created for an invalid file.
10. Saved physical file is cleaned up when database commit fails.

Use the existing test user/auth setup where practical.

Do not create a large fixture framework.

---

# 13. Receipt Route Tests

Create:

```text
backend/tests/test_receipt_routes.py
```

Use FastAPI `TestClient`.

Tests must use:

```text
smart_receipt_db_test
temporary upload directory
```

Override configuration or patch the upload directory simply for tests.

Include tests for:

1. Authenticated JPEG upload returns `201`.
2. Authenticated PDF upload returns `201`.
3. Response contains safe receipt-file fields.
4. Response does not expose an absolute internal file path.
5. Uploaded record belongs to the authenticated user.
6. Missing access token returns `401`.
7. Invalid access token returns `401`.
8. Missing file returns `422`.
9. Unsupported extension returns the expected error.
10. Unsupported MIME type returns the expected error.
11. Empty file returns the expected error.
12. Oversized file returns the expected error.
13. Existing auth, health, and category routes still work through the full suite.

Use small in-memory byte content for tests.

---

# 14. Security Requirements

1. Every receipt file must have the authenticated user's ID.
2. Never trust the original filename for storage.
3. Never allow path traversal such as `../../file.pdf`.
4. Generate the stored filename using UUID.
5. Validate both extension and MIME type.
6. Enforce the configured size limit.
7. Do not expose an absolute internal file path in the response.
8. Do not make uploaded files publicly accessible yet.
9. Do not store files in the database as binary data.
10. Do not log file contents.
11. Do not run or execute uploaded files.

---

# 15. Verification Commands

Run from the `backend` folder with the virtual environment active:

```bash
python -m pip install -r requirements.txt
python -m compileall app tests
```

Run file utility tests:

```bash
pytest tests/test_file_utils.py
```

Run receipt service tests:

```bash
pytest tests/test_receipt_service.py
```

Run receipt route tests:

```bash
pytest tests/test_receipt_routes.py
```

Run the complete test suite:

```bash
pytest
```

Optionally run:

```bash
uvicorn app.main:app --reload
```

Check Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# Do Not Implement Yet

Do not implement:

- `GET /api/receipts`
- `GET /api/receipts/{id}`
- `PUT /api/receipts/{id}`
- `DELETE /api/receipts/{id}`
- Public file download
- Gemini receipt extraction
- OCR
- Expense creation
- Expense items
- Translation
- Excel export
- Cloud storage
- Background jobs
- Virus scanning system
- Frontend upload page

---

# Expected Final Result

After this step, the project should have:

- Protected receipt upload endpoint
- JPEG, PNG, WEBP, and PDF support
- 10 MB configurable limit
- Safe UUID stored filenames
- Local file storage
- `receipt_files` database record creation
- User ownership
- Cleanup on database failure
- File utility tests
- Receipt service tests
- Receipt route tests
- No AI processing yet
- No receipt CRUD yet

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Actual `ReceiptFile` model fields found
3. Dependency added, if any
4. Upload settings added
5. Schema fields exposed
6. Utility functions implemented
7. Service function implemented
8. Route implemented
9. File-validation rules
10. File utility test result
11. Receipt service test result
12. Receipt route test result
13. Full test-suite result
14. Any model mismatch found
15. Any issue that could not be completed

Do not produce a long walkthrough unless an error occurs.
