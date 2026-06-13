# Project Structure

This document outlines the directory structure of the Smart Receipt Project and the responsibilities of each directory.

```text
smart-receipt-project/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── expense.py
│   │   │   └── expense_item.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── category.py
│   │   │   ├── expense.py
│   │   │   ├── receipt.py
│   │   │   └── report.py
│   │   │
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── receipts.py
│   │   │   ├── expenses.py
│   │   │   ├── categories.py
│   │   │   └── reports.py
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── gemini_service.py
│   │   │   ├── receipt_service.py
│   │   │   ├── expense_service.py
│   │   │   ├── translation_service.py
│   │   │   └── excel_service.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── file_utils.py
│   │       └── validators.py
│   │
│   ├── migrations/
│   │   └── .gitkeep
│   │
│   ├── uploads/
│   │   └── receipts/
│   │       └── .gitkeep
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py
│   │
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── frontend/
│   ├── api/
│   │   ├── README.md
│   │   └── api_client_placeholder.txt
│   │
│   └── README.md
│
├── docs/
│   ├── project-structure.md
│   ├── api-plan.md
│   └── database-plan.md
│
├── screenshots/
│   └── .gitkeep
│
├── .gitignore
├── README.md
└── PROJECT_STRUCTURE.md
```

## Folder Responsibilities

### Root Level
- `backend/`: Fast API server codebase, migrations, dependencies, and settings.
- `frontend/`: Frontend application code and placeholders.
- `docs/`: Design documentation, API route plans, and DB schema plans.
- `screenshots/`: Project screenshot storage.

### Backend Level
- `backend/app/main.py`: Entrypoint for the FastAPI application.
- `backend/app/config.py`: Environment configuration management.
- `backend/app/database.py`: SQLAlchemy session and connection setup.
- `backend/app/models/`: SQLAlchemy data models (categories, expenses, items).
- `backend/app/schemas/`: Pydantic schema validation models for requests/responses.
- `backend/app/routes/`: Route modules grouping endpoints logically.
- `backend/app/services/`: Core business logic layers (Gemini processing, Excel generation, translation, database operations).
- `backend/app/utils/`: Common helpers like validators and file management.
- `backend/migrations/`: Alembic migrations configuration and revisions.
- `backend/uploads/receipts/`: Temporary directory for local storage of uploaded files.
- `backend/tests/`: Package containing unit and integration tests.
