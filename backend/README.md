# Smart Receipt — Backend API

Smart Receipt is a backend API for uploading receipts, extracting receipt data with
Google Gemini, managing expenses, translating dynamic expense content between English
and Thai, and exporting expenses to Excel.

---

## Technology Stack

| Component | Tool |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI |
| Database | MySQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Data validation | Pydantic v2 |
| Authentication | PyJWT + Argon2 (pwdlib) |
| AI extraction | Google Gemini API |
| Excel export | openpyxl |
| Testing | pytest |

---

## Features

- **User registration and login** — JWT access tokens and refresh tokens
- **Category read endpoints** — authenticated read-only access to expense categories
- **Receipt upload and management** — JPEG, PNG, WEBP, and PDF up to 10 MB
- **Manual expense management** — create, read, update, and soft-delete expenses with line items
- **Gemini receipt extraction** — AI reads a receipt image and creates a draft expense
- **AI draft review and confirmation** — user reviews the draft and confirms it when ready
- **English–Thai dynamic translation** — translates live expense titles, notes, and item names
- **Excel export** — downloads an `.xlsx` file with Expenses and Expense Items worksheets
- **Soft deletion** — deleted records are hidden from the API but kept in the database
- **Ownership protection** — every record is scoped to the authenticated user

> **Translation note:** The backend translates live user data (expense titles, notes, item
> names). Fixed frontend labels such as "Dashboard" or "Save" are not handled here — those
> will be translated in the frontend using standard language files.

---

## Requirements

- Python 3.12 (or 3.11+)
- MySQL 8 (or compatible)
- A virtual environment tool (`venv` is built into Python)
- A Google Gemini API key for live AI features (not needed for tests)

---

## Setup

### 1. Create and activate a virtual environment

```bash
cd backend
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Copy and fill in the environment file

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

- `DATABASE_URL` — your development MySQL connection string
- `JWT_SECRET_KEY` — a long random secret (never commit the real value)
- `GEMINI_API_KEY` — required only for live receipt extraction and translation

---

## Database Setup

1. Start MySQL and create a development database:

```sql
CREATE DATABASE smart_receipt_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Set `DATABASE_URL` in `.env`.

3. Run Alembic migrations — this creates all tables:

```bash
alembic upgrade head
```

A clean database must be set up entirely through Alembic migrations.
Do not apply manual `ALTER TABLE` commands.

---

## Running the API

```bash
uvicorn app.main:app --reload
```

| URL | Description |
|---|---|
| `http://127.0.0.1:8000/docs` | Swagger UI — interactive API explorer |
| `http://127.0.0.1:8000/redoc` | ReDoc documentation |

---

## Running Tests

Tests use a separate database (`smart_receipt_db_test`).
Set `TEST_DATABASE_URL` in `.env` before running tests.

```bash
pytest
```

All Gemini calls in automated tests are mocked — no real API credits are used.

---

## Main API Workflows

### AI Receipt Flow

```
Register → Login → Upload receipt → Extract receipt (Gemini)
→ Review/update draft expense → Confirm expense
→ Translate if needed (Gemini) → Export to Excel
```

### Manual Expense Flow

```
Register → Login → Create expense
→ View / update / delete expense → Export to Excel
```

---

## API Summary

### Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Log in and receive tokens |
| POST | `/api/auth/refresh` | Refresh an access token |
| POST | `/api/auth/logout` | Revoke a refresh token |
| GET | `/api/auth/me` | Get the current user |

### Categories

| Method | Path | Description |
|---|---|---|
| GET | `/api/categories` | List all active categories |
| GET | `/api/categories/{id}` | Get one category |

### Receipts

| Method | Path | Description |
|---|---|---|
| POST | `/api/receipts/upload` | Upload a receipt file |
| GET | `/api/receipts` | List your receipts |
| GET | `/api/receipts/{id}` | Get receipt details |
| DELETE | `/api/receipts/{id}` | Soft-delete a receipt |
| POST | `/api/receipts/{id}/extract` | Extract data with Gemini (creates draft expense) |

### Expenses

| Method | Path | Description |
|---|---|---|
| POST | `/api/expenses` | Create an expense |
| GET | `/api/expenses` | List your expenses |
| GET | `/api/expenses/export` | Download expenses as Excel |
| GET | `/api/expenses/{id}` | Get expense details |
| PUT | `/api/expenses/{id}` | Update an expense |
| DELETE | `/api/expenses/{id}` | Soft-delete an expense |
| POST | `/api/expenses/{id}/confirm` | Confirm an AI draft expense |
| POST | `/api/expenses/{id}/translate` | Translate dynamic text |
| POST | `/api/expenses/{id}/receipts/{rid}` | Link a receipt to an expense |
| DELETE | `/api/expenses/{id}/receipts/{rid}` | Unlink a receipt from an expense |

---

## Gemini Configuration and Cost

`GEMINI_API_KEY` is required only for real extraction and translation requests.
Automated tests use mocks and do not call Gemini.

Real API requests may use free quota or may cost money depending on your Google
project billing configuration. Check [Google AI pricing](https://ai.google.dev/pricing)
before enabling in production.

---

## English–Thai Translation

The backend translates live dynamic data — expense titles, notes, and receipt item
names — using Gemini. Fixed frontend labels are not translated by the backend.

Existing translations are cached in the `translations` table and reused to avoid
unnecessary Gemini calls.

---

## Excel Export

`GET /api/expenses/export`

- Exports only the authenticated user's active (non-deleted) expenses
- Creates two worksheets: **Expenses** and **Expense Items**
- Returns an `.xlsx` file with the current date in the filename

---

## Alembic Migration History

| Revision | Description |
|---|---|
| `cbb57baabb25` | Initial schema — all tables |
| `a1b2c3d4e5f6` | Make `expenses.category_id` nullable for AI drafts |

---

## Security Notes

- Passwords are hashed with Argon2 and are never returned by the API.
- JWT secrets must be set in `.env` and never committed to version control.
- The `.env` file is excluded by `.gitignore`.
- `file_path`, `deleted_at`, `ai_raw_response`, and other internal fields
  are excluded from all API responses.
- All expense and receipt endpoints are scoped to the authenticated user.
  Accessing another user's records returns 404 (no information leakage).
