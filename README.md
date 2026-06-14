# Smart Receipt

An AI-powered receipt and expense management application. Upload receipts, extract data with Google Gemini, manage expenses, translate between English and Thai, and export to Excel.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Vue I18n |
| Backend | Python · FastAPI · SQLAlchemy · Alembic · PyJWT |
| Database | MySQL 8 |
| AI | Google Gemini API |
| Frontend tests | Vitest + Vue Test Utils |
| Backend tests | pytest |
| E2E tests | Playwright (Chromium) |

---

## Quick Start

You need three terminals running before the E2E tests can work.

### Terminal 1 — Backend

**macOS / Linux**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in DATABASE_URL and JWT_SECRET_KEY
alembic upgrade head
python scripts/seed_categories.py
uvicorn app.main:app --reload
```

**Windows PowerShell**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # fill in DATABASE_URL and JWT_SECRET_KEY
alembic upgrade head
python scripts/seed_categories.py
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.
Swagger UI: `http://127.0.0.1:8000/docs`

### Terminal 2 — Frontend

```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_BASE_URL=http://127.0.0.1:8000/api
npm run dev
```

The app will be available at `http://127.0.0.1:5173`.

---

## Running Tests

### Backend pytest

```bash
cd backend
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # macOS / Linux

# The test database must exist and have migrations applied:
# CREATE DATABASE smart_receipt_db_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
# Set TEST_DATABASE_URL in backend/.env, then:
# $env:DATABASE_URL = "mysql+pymysql://root:@localhost:3306/smart_receipt_db_test"  # Windows
# DATABASE_URL=... alembic upgrade head                                             # macOS / Linux

pytest
```

Expected: **662 passed**

### Frontend unit tests

```bash
cd frontend
npm run test
```

Expected: **400 passed**

### Frontend production build

```bash
cd frontend
npm run build
```

Expected: zero TypeScript errors, clean Vite build.

---

## E2E Tests (Playwright)

### Prerequisites

1. Backend running on `http://127.0.0.1:8000` (Terminal 1 above)
2. Frontend running on `http://127.0.0.1:5173` (Terminal 2 above)
3. Playwright Chromium installed

```bash
cd frontend
npx playwright install chromium
```

### Dedicated E2E database (recommended)

Create a separate MySQL database for E2E tests:

```sql
CREATE DATABASE smart_receipt_db_e2e CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Apply migrations and seed categories targeting it:

**macOS / Linux**
```bash
cd backend
DATABASE_URL=mysql+pymysql://root:@localhost:3306/smart_receipt_db_e2e alembic upgrade head
DATABASE_URL=mysql+pymysql://root:@localhost:3306/smart_receipt_db_e2e python scripts/seed_categories.py
```

**Windows PowerShell**
```powershell
cd backend
$env:DATABASE_URL = "mysql+pymysql://root:@localhost:3306/smart_receipt_db_e2e"
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe scripts/seed_categories.py
```

Point the backend at the E2E database by setting `DATABASE_URL` in `backend/.env` before starting it for E2E runs. The `smart_receipt_db_e2e` name passes the safety guard in `scripts/setup_e2e_db.py`.

> **Safety note:** The cleanup script in `backend/scripts/setup_e2e_db.py` will refuse to
> run unless the database name ends with `_e2e` or `_test`. This prevents accidental
> destruction of your development or production data.

### Run E2E tests (Terminal 3)

```bash
cd frontend
npm run test:e2e
```

Headed mode (visible browser):
```bash
npm run test:e2e:headed
```

Interactive Playwright UI:
```bash
npm run test:e2e:ui
```

### What is mocked in E2E tests

Only Gemini-dependent endpoints are mocked in automated browser tests:

| Endpoint | Reason |
|---|---|
| `POST /api/receipts/{id}/extract` | Calls Gemini — mocked to avoid quota usage |
| `POST /api/expenses/{id}/translate` | Calls Gemini — mocked to avoid quota usage |

All other flows (auth, categories, expense CRUD, confirmation, receipt upload/list, delete, Excel export) use the **real backend** and **real E2E database**.

---

## E2E Test Coverage

| Spec file | Workflow |
|---|---|
| `auth.spec.ts` | Register, login, refresh, logout, protected redirects |
| `expense.spec.ts` | Create, edit, delete, Excel export |
| `receipt.spec.ts` | File selection preview, upload + mocked extract |
| `confirmation.spec.ts` | Confirm draft from detail and edit pages |
| `translation.spec.ts` | Translate to Thai and English (mocked) |
| `export.spec.ts` | Excel download from list and dashboard |
| `isolation.spec.ts` | User B cannot access User A data |
| `dashboard.spec.ts` | Summary counts, currency split, deleted exclusion |
| `errors.spec.ts` | Safe error messages, no stack traces or API keys |
| `mobile.spec.ts` | Mobile viewport smoke test |

---

## Environment Files

| File | Purpose |
|---|---|
| `backend/.env` | Real backend secrets — never commit |
| `backend/.env.example` | Safe template — commit this |
| `frontend/.env` | Frontend env (API base URL) — never commit |
| `frontend/.env.example` | Safe template |
| `frontend/.env.e2e.example` | E2E-specific template |

---

## Database Safety

**Never run E2E tests against your development or production database.**

The test database name must end with `_e2e` or `_test`. The cleanup helper in
`backend/scripts/setup_e2e_db.py` enforces this check and will exit with an error
if the safety condition is not met.

---

## Gemini API

`GEMINI_API_KEY` is required only for live extraction and translation.
Automated tests (both pytest and Playwright) mock Gemini calls and do not consume quota.

If you want to test real Gemini behavior manually:
1. Set `GEMINI_API_KEY` in `backend/.env`
2. Upload a receipt in the browser and click "Upload & Extract"
3. Open an expense detail page and click "Translate"

Do not consume quota in automated test runs.

---

## Project Structure

```
Aura_Sum/
├── backend/               FastAPI backend
│   ├── app/               Application code
│   │   ├── models/        SQLAlchemy models
│   │   ├── routes/        API route handlers
│   │   ├── schemas/       Pydantic schemas
│   │   ├── services/      Business logic
│   │   └── utils/         Helpers
│   ├── migrations/        Alembic migration files
│   ├── scripts/           Setup and seed scripts
│   └── tests/             pytest test suite (662 tests)
└── frontend/              Vue 3 frontend
    ├── src/
    │   ├── api/           Axios API clients
    │   ├── components/    Shared components
    │   ├── layouts/       App layout
    │   ├── locales/       i18n translations (en, th)
    │   ├── stores/        Pinia stores
    │   ├── types/         TypeScript types
    │   ├── utils/         Helper utilities
    │   ├── views/         Page components
    │   └── tests/         Vitest unit tests (400 tests)
    └── e2e/               Playwright E2E tests
        ├── fixtures/      Test files (safe, no real data)
        ├── helpers/       Shared helpers
        └── *.spec.ts      Test specs
```
