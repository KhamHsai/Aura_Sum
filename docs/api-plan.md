# API Route Plan

This document maps out the planned FastAPI endpoints.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health Check |
| POST | `/api/receipts/analyze` | Upload and analyze a receipt using Gemini API |
| POST | `/api/expenses` | Create a new manual expense |
| GET | `/api/expenses` | List all expenses |
| GET | `/api/expenses/{id}` | Retrieve details of a specific expense |
| PUT | `/api/expenses/{id}` | Update an existing expense |
| DELETE | `/api/expenses/{id}` | Delete an expense |
| GET | `/api/categories` | List all available categories |
| GET | `/api/reports/monthly` | Retrieve aggregated monthly report data |
| GET | `/api/reports/monthly/export` | Export monthly reports to Excel |
