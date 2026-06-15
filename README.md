# Aura Sum — Smart Receipt & Expense Tracker

## Objective

Aura Sum is a full-stack web application that helps users track their personal expenses by uploading receipt images. The app uses AI (via OpenRouter) to automatically extract key information from receipts — merchant name, date, line items, and total — and organises them into categorised expense records. Users can also create and edit expenses manually, export their data to Excel, and view a dashboard summary of their spending.

---

## Features

- **AI Receipt Extraction** — Upload a photo of a receipt (JPG, PNG, WebP, PDF) and let the AI read and parse it automatically
- **Manual Expense Entry** — Create and edit expenses with full line-item support
- **Category Management** — Auto-categorise expenses; custom categories are created on the fly
- **Dashboard** — Spending summary and recent expense overview
- **Excel Export** — Download all expenses and items as a formatted `.xlsx` file
- **Bilingual UI** — Full English and Thai language support (i18n)
- **JWT Authentication** — Secure login with access + refresh token rotation

---

## Tools & Technologies

### Backend
| Tool | Purpose |
|---|---|
| Python 3.11+ | Primary language |
| FastAPI | REST API framework |
| SQLAlchemy | ORM |
| Alembic | Database migrations |
| MySQL (PyMySQL) | Database |
| Pydantic v2 | Data validation and settings |
| python-jose | JWT token handling |
| openpyxl | Excel export |
| uvicorn | ASGI server |

### Frontend
| Tool | Purpose |
|---|---|
| Vue 3 | UI framework (Composition API) |
| TypeScript | Type-safe JavaScript |
| Vite | Build tool and dev server |
| Vue Router 4 | Client-side routing |
| Pinia | State management |
| vue-i18n | English / Thai localisation |
| Axios | HTTP client |
| SweetAlert2 | Alerts and confirmation dialogs |
| Vitest | Unit testing |
| Playwright | End-to-end testing |

---

## AI Model Used

| Setting | Value |
|---|---|
| Provider | [OpenRouter](https://openrouter.ai) |
| Model | `nvidia/nemotron-nano-12b-v2-vl:free` |
| API | OpenAI-compatible (`/chat/completions`) |

The AI is used in a two-step pipeline:
1. **Read** — The model transcribes all visible text from the receipt image (OCR)
2. **Parse** — Python code extracts structured fields (merchant, date, items, total) from the transcribed text

---

## Project Structure

```
Aura_Sum/
├── backend/
│   ├── app/
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic request/response schemas
│   │   ├── routes/        # FastAPI route handlers
│   │   ├── services/      # Business logic
│   │   ├── dependencies/  # Auth dependencies
│   │   ├── utils/         # Helpers (tokens, passwords, files)
│   │   ├── config.py      # Settings from .env
│   │   ├── database.py    # DB engine and session
│   │   └── main.py        # FastAPI app entry point
│   ├── migrations/        # Alembic migration scripts
│   ├── .env               # Local environment variables (not committed)
│   ├── .env.example       # Template for .env
│   └── alembic.ini
└── frontend/
    ├── src/
│   │   ├── api/           # Axios API calls
│   │   ├── components/    # Reusable Vue components
│   │   ├── views/         # Page-level Vue components
│   │   ├── stores/        # Pinia state stores
│   │   ├── types/         # TypeScript interfaces
│   │   ├── utils/         # Formatters, helpers
│   │   └── locales/       # en.json / th.json translations
    ├── index.html
    └── package.json
```

---

## Running Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- An [OpenRouter](https://openrouter.ai) API key (free tier available)

---

### 1. Clone the repository

```bash
git clone <repository-url>
cd Aura_Sum
```

---

### 2. Backend setup

```bash
cd backend
```

**Create and activate a virtual environment:**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Configure environment variables:**

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```env
DATABASE_URL=mysql+pymysql://your_user:your_password@localhost:3306/smart_receipt_db
JWT_SECRET_KEY=your-long-random-secret-key
OPENROUTER_API_KEY=your-openrouter-api-key
FRONTEND_URL=http://localhost:5173
```

**Create the database** (in MySQL):

```sql
CREATE DATABASE smart_receipt_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Run database migrations:**

```bash
alembic upgrade head
```

**Start the backend server:**

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

### 3. Frontend setup

```bash
cd frontend
```

**Install dependencies:**

```bash
npm install
```

**Start the development server:**

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

### 4. Running tests

**Backend** — from the `backend/` directory:

```bash
pytest
```

**Frontend unit tests** — from the `frontend/` directory:

```bash
npm run test
```

**Frontend end-to-end tests:**

```bash
npm run test:e2e
```

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | MySQL connection string |
| `JWT_SECRET_KEY` | ✅ | Secret key for signing JWT tokens |
| `OPENROUTER_API_KEY` | ✅ | API key from openrouter.ai |
| `OPENROUTER_MODEL` | — | AI model (default: `nvidia/nemotron-nano-12b-v2-vl:free`) |
| `FRONTEND_URL` | — | Frontend origin for CORS (e.g. `http://localhost:5173`) |
| `UPLOAD_DIR` | — | Path to store uploaded receipt files (default: `uploads/receipts`) |
| `MAX_RECEIPT_FILE_SIZE_MB` | — | Max upload size in MB (default: `10`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | JWT access token lifetime (default: `30`) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | JWT refresh token lifetime (default: `7`) |
