# Smart Receipt Project — Step 15A: Gemini Extraction Schemas and Client

## Goal

Prepare the AI extraction layer for English and Thai receipts.

This step must implement:

```text
Gemini configuration
Pydantic extraction schemas
Gemini receipt-extraction client/service
Prompt construction
Structured response parsing
Validation and error handling
Mocked unit tests
```

Do not create the public extraction API endpoint yet.

Do not create an Expense or ExpenseItem from AI output yet.

Do not link a receipt to an expense yet.

The next step will connect this extraction layer to:

```text
POST /api/receipts/{receipt_id}/extract
```

Keep the code simple, readable, and easy for a student to explain.

---

## Project Status

The project already has:

- FastAPI
- MySQL
- SQLAlchemy
- Alembic
- Pydantic
- Authentication and current-user dependency
- Protected category endpoints
- Receipt upload, list, detail, and soft delete
- Expense create, list, detail, update, and soft delete
- Receipt-to-expense link and unlink
- English and Thai support requirement
- Separate MySQL test database
- 370 tests passing

Inspect the existing settings/configuration, receipt schemas, expense schemas, models, services, and test structure before changing anything.

Do not rebuild completed features.

---

## Scope of This Step

Implement only:

```text
1. Gemini settings
2. AI extraction schemas
3. Gemini client wrapper
4. Receipt extraction prompt
5. Structured JSON parsing
6. Validation and normalization
7. Mocked tests
```

Do not implement:

```text
POST /api/receipts/{receipt_id}/extract
Database creation from Gemini output
Receipt linking after extraction
Review and confirmation workflow
Standalone translation endpoint
Excel export
Frontend code
```

---

# 1. Dependency and SDK Inspection

Before writing the integration:

1. Inspect `requirements.txt` or the project dependency file.
2. Check whether a Google Gemini SDK is already installed.
3. Use the SDK style compatible with the installed package.
4. If no Gemini SDK is installed, add the current official Google Gemini Python package used by the project environment.
5. Do not install multiple competing Gemini SDK packages.
6. Keep all SDK-specific code inside one client module so it can be changed later without affecting business logic.

Do not hard-code assumptions about the SDK before inspecting the environment.

---

# 2. Environment Configuration

Add settings for:

```env
GEMINI_API_KEY=
GEMINI_MODEL=
```

Recommended development model value may be placed in `.env.example`, but do not hard-code the model throughout the application.

Use the project's existing settings system.

Examples of acceptable setting names:

```python
gemini_api_key: str | None = None
gemini_model: str = "configured-model-name"
```

Requirements:

- Never commit a real API key.
- Add placeholders to `.env.example`.
- Do not print the API key.
- Do not include the API key in exceptions.
- Tests must not require a real key.
- A missing key must produce a clear application error only when extraction is attempted.

---

# 3. Suggested File Structure

Inspect the current structure first.

A simple structure is preferred:

```text
backend/app/schemas/ai_extraction.py
backend/app/services/gemini_service.py
```

or:

```text
backend/app/integrations/gemini_client.py
backend/app/schemas/ai_extraction.py
```

Use the option that best matches the existing project organization.

Do not create unnecessary layers such as:

```text
AI repository
provider factory
plugin registry
abstract provider hierarchy
generic LLM framework
```

One small Gemini wrapper is enough.

---

# 4. Extraction Schemas

Create Pydantic schemas for raw structured AI output.

Suggested schemas:

```text
ExtractedReceiptItem
ExtractedReceiptData
```

Optionally create:

```text
GeminiExtractionResult
```

only if useful.

---

## `ExtractedReceiptItem`

Suggested fields:

```python
original_name: str | None = None
name_en: str | None = None
name_th: str | None = None
quantity: Decimal | None = None
unit: str | None = None
unit_price: Decimal | None = None
discount_amount: Decimal | None = None
total_price: Decimal | None = None
category_name: str | None = None
```

Rules:

- At least one of `original_name`, `name_en`, or `name_th` should contain useful text.
- Trim strings.
- Convert empty strings to `None`.
- Decimal fields must not be NaN or infinite.
- Negative quantity should be rejected.
- Negative monetary values should be rejected unless the existing business rules explicitly allow them.
- Do not require category IDs from Gemini.
- Gemini may suggest a category name only.
- Category IDs will be matched later by application logic.

---

## `ExtractedReceiptData`

Suggested fields:

```python
title: str | None = None
merchant_name: str | None = None
receipt_number: str | None = None
receipt_date: date | None = None
receipt_time: time | None = None
document_type: str | None = None
payment_method: str | None = None
currency: str | None = None
subtotal: Decimal | None = None
tax_amount: Decimal | None = None
discount_amount: Decimal | None = None
total_amount: Decimal
language_detected: str
ai_confidence: Decimal | None = None
items: list[ExtractedReceiptItem] = []
```

Use field names that match the existing Expense model and schemas where possible.

---

## Required Validation

### Language

Only allow:

```text
en
th
```

Normalize values such as:

```text
English → en
Thai → th
EN → en
TH → th
```

Reject unsupported detected languages or normalize them to the safest behavior agreed with the existing project.

Do not support Myanmar language.

---

### Currency

Normalize currency to an uppercase code when possible:

```text
thb → THB
usd → USD
```

If Gemini returns a symbol:

```text
฿ → THB
$ → USD
```

Support only simple known mappings.

Do not build a large currency-conversion system.

---

### Amounts

- `total_amount` is required.
- `total_amount` must be zero or greater.
- Other monetary fields must be zero or greater when present.
- Reject NaN and infinite values.
- Keep `Decimal`; do not convert monetary values to float.

---

### Confidence

If included:

```text
0 <= ai_confidence <= 1
```

Reject values outside the range or normalize percentages only if clearly documented.

A simple normalization may support:

```text
85 → 0.85
```

but only if implemented clearly and tested.

---

### Items

- Default to an empty list.
- Validate every item.
- Do not fail only because no items were detected.
- Do not calculate database category IDs yet.
- Do not save anything to the database in this step.

---

# 5. Gemini Service Errors

Create a lightweight exception such as:

```python
class GeminiServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
```

Use clear messages.

Suggested cases:

```text
Gemini API key is not configured
Receipt file not found
Unsupported receipt file type
Gemini extraction failed
Gemini returned an empty response
Gemini returned invalid JSON
Gemini response validation failed
```

Do not include sensitive provider response details in public messages.

The original exception may be preserved internally using exception chaining:

```python
raise GeminiServiceError(...) from exc
```

---

# 6. Supported File Types

The existing receipt upload feature supports:

```text
JPEG
PNG
WEBP
PDF
```

The Gemini client should accept these existing uploaded file types.

Use MIME types:

```text
image/jpeg
image/png
image/webp
application/pdf
```

Reject anything else with a clear error.

Do not add OCR libraries.

Do not convert PDFs to images in this step unless the chosen official SDK requires it and the implementation remains simple.

Do not use OCR as a fallback.

---

# 7. Gemini Prompt

Create one focused extraction prompt.

The prompt must tell Gemini:

```text
You are extracting data from a receipt.
The receipt language is English or Thai.
Return structured JSON only.
Do not include Markdown.
Do not include code fences.
Do not invent values.
Use null when a value is unavailable.
Use ISO date format YYYY-MM-DD.
Use 24-hour time HH:MM:SS when available.
Use uppercase currency codes.
Use decimal numbers without currency symbols or commas.
Detect language as en or th only.
Provide both English and Thai item names when possible.
```

The requested JSON structure should match the Pydantic schemas.

Example conceptual structure:

```json
{
  "title": null,
  "merchant_name": null,
  "receipt_number": null,
  "receipt_date": null,
  "receipt_time": null,
  "document_type": null,
  "payment_method": null,
  "currency": "THB",
  "subtotal": null,
  "tax_amount": null,
  "discount_amount": null,
  "total_amount": "0.00",
  "language_detected": "th",
  "ai_confidence": "0.90",
  "items": [
    {
      "original_name": null,
      "name_en": null,
      "name_th": null,
      "quantity": null,
      "unit": null,
      "unit_price": null,
      "discount_amount": null,
      "total_price": null,
      "category_name": null
    }
  ]
}
```

Do not use this example as a fixed response.

Do not ask Gemini for database IDs.

---

# 8. Structured Output

Prefer the official SDK's supported structured-output or JSON-response configuration if available in the installed SDK.

The service must still validate the final result using Pydantic.

Required flow:

```text
File bytes/path
→ Gemini request
→ Provider response
→ Extract text or structured payload
→ Remove harmless surrounding whitespace
→ Parse JSON when needed
→ Validate with ExtractedReceiptData
→ Return validated Pydantic object
```

Do not return an unvalidated provider dictionary.

Do not directly trust Gemini output.

---

# 9. JSON Cleaning

Gemini is instructed to return JSON only, but add small defensive handling.

Acceptable cleaning:

```text
Trim whitespace
Remove one surrounding ```json ... ``` code fence if present
```

Do not write a complicated AI-response repair engine.

Do not silently invent missing fields.

Invalid JSON must produce:

```text
Gemini returned invalid JSON
```

---

# 10. Main Service Function

Create a function similar to:

```python
def extract_receipt_data(
    file_path: Path | str,
    mime_type: str,
) -> ExtractedReceiptData:
    ...
```

or an async version if the chosen SDK and existing application style use async calls:

```python
async def extract_receipt_data(
    file_path: Path | str,
    mime_type: str,
) -> ExtractedReceiptData:
    ...
```

Choose one style and use it consistently.

The function should:

```text
1. Validate API configuration
2. Validate MIME type
3. Confirm the file exists
4. Read or upload the file using the official SDK approach
5. Send the extraction prompt
6. Parse the response
7. Validate with Pydantic
8. Return ExtractedReceiptData
```

It must not:

```text
Query ReceiptFile from the database
Create Expense records
Create ExpenseItem records
Link a receipt
Confirm an expense
```

Those belong to the next step.

---

# 11. Testability

The Gemini SDK call must be easy to mock.

Acceptable approaches:

```text
A small private client-construction function
Dependency injection through one optional client parameter
Mocking the SDK call at the module boundary
```

Do not perform real Gemini requests in automated tests.

Do not require internet access in tests.

Do not require a real API key in tests.

---

# 12. Tests

Create focused tests, for example:

```text
backend/tests/test_ai_extraction_schemas.py
backend/tests/test_gemini_service.py
```

Follow the existing naming style.

---

## Schema Tests

Test at least:

1. Valid English extraction payload.
2. Valid Thai extraction payload.
3. Language normalization from `English` to `en`.
4. Language normalization from `Thai` to `th`.
5. Unsupported language is rejected.
6. Currency normalization to uppercase.
7. Thai baht symbol maps to `THB`.
8. Dollar symbol maps to `USD`.
9. Decimal strings are parsed as `Decimal`.
10. `total_amount` is required.
11. Negative total is rejected.
12. NaN amount is rejected.
13. Infinite amount is rejected.
14. Confidence below zero is rejected.
15. Confidence above one is rejected.
16. Empty items defaults to `[]`.
17. Valid nested items are accepted.
18. Empty item strings become `None`.
19. Negative item quantity is rejected.
20. Negative item amount is rejected.

---

## Gemini Service Tests

Mock the provider.

Test at least:

1. Valid mocked Gemini JSON returns `ExtractedReceiptData`.
2. English receipt output is parsed.
3. Thai receipt output is parsed.
4. Missing API key raises clear service error.
5. Missing file raises clear service error.
6. Unsupported MIME type raises clear service error.
7. Empty Gemini response raises clear service error.
8. Invalid JSON raises clear service error.
9. Markdown JSON fence is handled.
10. Schema-invalid JSON raises validation error.
11. Provider exception becomes `GeminiServiceError`.
12. Provider exception does not leak API key.
13. JPEG MIME type is accepted.
14. PNG MIME type is accepted.
15. WEBP MIME type is accepted.
16. PDF MIME type is accepted.
17. Prompt requires JSON-only output.
18. Prompt mentions English and Thai only.
19. Prompt requires `en` or `th`.
20. No database rows are created during extraction tests.
21. No real network request occurs.
22. Existing full test suite remains green.

Use temporary files for test inputs.

---

# 13. Configuration Tests

Add or update tests to confirm:

```text
GEMINI_API_KEY can be absent during application startup
GEMINI_MODEL has a usable configured/default value
Real key is not required for unrelated endpoints
```

The application must still start when no Gemini key is configured.

Only extraction attempts should fail because of the missing key.

---

# 14. Public Exports

Export only what later steps need:

```text
ExtractedReceiptData
ExtractedReceiptItem
GeminiServiceError
extract_receipt_data
```

Do not export private parsing helpers.

---

# 15. Security and Privacy

1. Do not log the API key.
2. Do not include the API key in errors.
3. Do not log complete receipt contents by default.
4. Do not expose local file paths.
5. Do not send files anywhere except the configured Gemini provider.
6. Do not save raw provider responses in this step.
7. Do not create database records.
8. Do not use real API calls in tests.

---

# 16. Verification Commands

Run from the backend folder with the virtual environment active:

```bash
python -m compileall app tests
```

Run schema tests:

```bash
pytest tests/test_ai_extraction_schemas.py
```

Run Gemini service tests:

```bash
pytest tests/test_gemini_service.py
```

Run the full suite:

```bash
pytest
```

Confirm that no automated test contacts Gemini.

---

# Do Not Implement Yet

Do not implement:

- `POST /api/receipts/{receipt_id}/extract`
- Receipt ownership lookup for extraction
- Expense creation from AI output
- Expense-item creation from AI output
- Automatic category-ID matching
- Receipt-to-expense linking after AI extraction
- Review and confirmation endpoint
- Standalone English–Thai translation endpoint
- Excel export
- Frontend code

---

# Expected Final Result

After this step, the project should have:

- Gemini environment settings
- English/Thai extraction schemas
- Decimal and language validation
- A small Gemini receipt-extraction wrapper
- A JSON-only extraction prompt
- Structured response parsing
- Safe provider error handling
- Fully mocked tests
- No API endpoint yet
- No database writes yet
- No real API usage in tests

---

# Required Completion Report

At the end, provide a concise report containing:

1. Changed file list
2. Gemini package/SDK used
3. Configuration fields added
4. Extraction schemas added
5. Language rules implemented
6. Currency and Decimal normalization
7. Main Gemini service function
8. Structured-output or JSON parsing approach
9. Supported MIME types
10. Error handling
11. Schema test result
12. Gemini service test result
13. Full test-suite result
14. Confirmation that tests use no real Gemini requests
15. Any SDK, model, or project mismatch found

Do not produce a long walkthrough unless an error occurs.
