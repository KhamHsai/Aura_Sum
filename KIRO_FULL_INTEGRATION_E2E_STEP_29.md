# Smart Receipt Project — Step 29: Full Frontend and Backend Integration Testing

## Goal

Verify the complete Smart Receipt application using the Vue frontend, FastAPI backend, and MySQL database together.

Add focused browser end-to-end tests for the most important user workflows.

Use:

```text
Frontend unit tests:
Vitest + Vue Test Utils

Backend tests:
Pytest

Browser end-to-end tests:
Playwright
```

Expected final verification:

```text
Backend tests pass
Frontend tests pass
Frontend production build passes
Playwright end-to-end tests pass
Main manual workflows are verified
```

Write simple, human-readable test code that is easy to understand and explain.

Use clear test names, small helpers, and straightforward setup.

Avoid unnecessary test frameworks, complex fixtures, generic automation layers, and overengineering.

---

## Current Project Status

Already completed:

- Vue 3 + TypeScript + Vite
- Pinia, Vue Router, Axios, Vue I18n
- Authentication and protected routes
- Expense list, detail, create, edit, delete, confirmation, translation, and Excel export
- Receipt list, upload, detail, and Gemini extraction
- Dashboard summary and UI cleanup
- SweetAlert2 notifications
- 400 frontend tests passing
- Clean frontend production build
- Complete FastAPI backend with 662 tests passing
- MySQL and Alembic database setup

Inspect the existing frontend tests, backend tests, environment configuration, scripts, and project structure before changing anything.

Do not rewrite existing unit tests.

Do not change working production code unless a real integration bug is found.

---

# Scope

Implement only:

```text
Playwright setup
Dedicated end-to-end environment configuration
Dedicated test database protection
Core browser workflows
API mocking for Gemini-dependent browser tests
Authentication integration checks
Manual expense integration checks
Receipt upload integration checks
Confirmation and translation checks
Excel download check
User isolation verification
Dashboard consistency verification
Error-handling smoke checks
Mobile-layout smoke test
Final backend/frontend/build test commands
Concise integration report
```

Do not implement:

```text
New product features
Visual redesign
Performance testing platform
Load testing
Production deployment
CI/CD unless already present
Cross-browser matrix beyond practical scope
Real Gemini calls in automated tests
```

---

# Important Testing Principles

1. Never run end-to-end tests against the production database.
2. Use a dedicated test database.
3. Reset test data between test runs.
4. Use unique test users.
5. Mock Gemini extraction and translation in automated browser tests.
6. Do not consume real Gemini quota.
7. Keep end-to-end tests focused on core workflows.
8. Do not repeat every small unit-test validation case.
9. Use stable selectors.
10. Avoid arbitrary long timeouts and `waitForTimeout`.
11. Wait for visible UI states or network responses instead.
12. Keep tests deterministic and repeatable.

---

# 1. Inspect Existing Scripts and Structure

Inspect:

```text
backend/
frontend/
frontend/package.json
frontend/vite.config.ts
backend/pytest.ini
backend/tests/
frontend/src/**/*.test.ts
.env.example files
```

Confirm:

```text
How backend tests use the test database
How frontend API base URL is configured
Whether Playwright is already installed
Whether a root-level test script exists
```

Reuse existing project conventions.

---

# 2. Install Playwright

Inside:

```text
frontend/
```

Install:

```bash
npm install -D @playwright/test
npx playwright install chromium
```

Use Chromium as the required browser for this project.

Do not install all browsers unless the project needs them.

Do not add Cypress.

---

# 3. Playwright Configuration

Create:

```text
frontend/playwright.config.ts
```

Configure:

```text
test directory
base URL
Chromium project
screenshots on failure
traces on first retry
reasonable timeout
```

Suggested base URL:

```text
http://127.0.0.1:5173
```

or:

```text
http://localhost:5173
```

Use one consistently.

Add `webServer` configuration only if it can reliably start the frontend.

Starting both frontend and backend through Playwright may be complicated. Choose the simplest reliable approach:

```text
Option A:
Playwright starts frontend only.
Backend must be started separately.

Option B:
Use a root script to start both backend and frontend before Playwright.
```

Document the chosen approach clearly.

Do not hide setup complexity.

---

# 4. Environment Configuration

Create:

```text
frontend/.env.e2e.example
```

Possible values:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
E2E_BASE_URL=http://127.0.0.1:5173
```

Create backend E2E guidance using a dedicated database:

```env
DATABASE_URL=mysql+pymysql://USER:PASSWORD@localhost:3306/smart_receipt_db_e2e
```

Do not commit real passwords or API keys.

Do not use the normal development database for automated E2E data.

---

# 5. Dedicated E2E Database Safety

Use a dedicated database:

```text
smart_receipt_db_e2e
```

Before tests:

```text
Apply Alembic migrations
Seed required default categories
Clear prior E2E test records safely
```

Do not drop or truncate the normal development database.

Add an explicit safety check before cleanup:

```text
Database name must end with `_e2e` or `_test`
```

If not:

```text
Fail immediately
```

Do not continue cleanup against an unsafe database name.

---

# 6. Test Data Strategy

Use unique data for each run:

```text
e2e-user-<timestamp>@example.com
e2e-user-b-<timestamp>@example.com
```

Use predictable expense titles:

```text
E2E Manual Expense
E2E Edited Expense
E2E AI Draft Expense
```

Clean up through API or database-safe test helpers after tests where practical.

Tests must not depend on execution order.

---

# 7. Stable Selectors

Prefer:

```text
getByRole
getByLabel
getByText
```

Add `data-testid` only when semantic selectors are unreliable.

Suggested test IDs only where needed:

```text
expense-card
receipt-card
dashboard-total-expenses
dashboard-confirmed-expenses
dashboard-draft-expenses
dashboard-total-receipts
```

Do not add test IDs to every element.

---

# 8. Package Scripts

Update:

```text
frontend/package.json
```

Add scripts such as:

```json
{
  "test:e2e": "playwright test",
  "test:e2e:headed": "playwright test --headed",
  "test:e2e:ui": "playwright test --ui"
}
```

Keep existing scripts unchanged.

Optionally add a root documentation command, but do not introduce a complex task runner.

---

# 9. Authentication E2E Workflow

Create a test for:

```text
Register
→ Login
→ Dashboard
→ Refresh browser
→ User remains authenticated
→ Logout
→ Protected page redirects to login
```

Also verify:

```text
Invalid login shows safe error
Duplicate registration shows safe error
```

Do not inspect localStorage passwords.

Verify only the access token is stored.

---

# 10. Manual Expense E2E Workflow

Test:

```text
Login
→ Add Expense
→ Select category
→ Fill title, merchant, currency, total
→ Add at least one item
→ Save
→ View detail
→ Edit
→ Change title and item
→ Save
→ Confirm updated values
→ Export Excel
→ Delete expense
→ Confirm it disappears from active list
```

Use real backend API and test database.

Do not mock normal expense CRUD in this workflow.

---

# 11. Receipt Upload E2E Workflow

Use a small safe test fixture:

```text
frontend/e2e/fixtures/test-receipt.png
```

The fixture may be a simple generated receipt-like image.

Do not include real personal receipt data.

Test:

```text
Open Upload Receipt
→ Select valid image
→ See preview
→ Upload
```

For extraction:

```text
Mock POST /api/receipts/{id}/extract
```

or use a backend test-mode stub.

Do not call real Gemini.

The mocked response must match the real `ExpenseResponse` schema.

Then verify redirect to:

```text
/expenses/{expense_id}/edit
```

---

# 12. AI Draft Confirmation E2E Workflow

Test:

```text
Open AI-created draft expense
→ Correct data
→ Click Confirm Expense
→ Confirm SweetAlert2 dialog
→ Save then confirm
→ Open detail
→ Confirmed badge appears
→ Confirm button disappears
```

Use a seeded or mocked AI draft expense.

The confirm endpoint itself can use the real backend because it does not call Gemini.

---

# 13. Translation E2E Workflow

Test:

```text
Open expense detail
→ Choose Thai
→ Click Translate
→ Show loading state
→ Display translated title and item names
→ Original values remain visible
```

Mock:

```text
POST /api/expenses/{id}/translate
```

The mock response must match the real translation schema.

Do not call real Gemini.

Also test English target if practical.

---

# 14. Excel Export E2E Workflow

Test:

```text
Open Expenses
→ Click Export Excel
→ Browser download begins
→ Filename ends with .xlsx
```

Use Playwright download handling:

```ts
const downloadPromise = page.waitForEvent('download')
```

Verify:

```text
Suggested filename
File extension
Downloaded file is not empty
```

Do not require Microsoft Excel to be installed.

Do not inspect every workbook cell in Playwright if backend unit tests already cover workbook content.

---

# 15. User Isolation Verification

Use two real test users:

```text
User A
User B
```

Create an expense and receipt for User A.

Login as User B and verify User B cannot:

```text
View User A expense
Edit User A expense
Delete User A expense
Confirm User A expense
Translate User A expense
View User A receipt
Extract User A receipt
```

Expected results:

```text
404 or safe authorization behavior
No private data displayed
```

Test direct URL access, not only hidden buttons.

Do not expose whether another user's private record exists.

---

# 16. Dashboard Consistency E2E Check

After creating test data, verify:

```text
Total expenses
Confirmed expenses
Draft expenses
Total receipts
Linked receipts
Unlinked receipts
Spending grouped by currency
Recent expense list
```

Use known seeded data so expected values are deterministic.

Verify:

```text
THB and USD remain separate
Deleted expense is excluded
Only five recent expenses appear
```

---

# 17. Error Handling Smoke Tests

Add focused browser checks for:

```text
Invalid expense ID
Invalid receipt ID
Unsupported file
Oversized file using mocked File where practical
Backend API 500 response
Gemini not configured response
Gemini quota response
Translation service failure
```

Use route interception to simulate server errors where appropriate.

Verify:

```text
Safe user-facing message
No stack trace
No API key
No internal filesystem path
No raw database error
```

Do not try to make the real database unavailable during automated tests.

Database-unavailable behavior can remain a documented manual check.

---

# 18. Mobile Layout Smoke Test

Use a mobile viewport, for example:

```ts
page.setViewportSize({
  width: 390,
  height: 844,
})
```

Verify:

```text
Navigation is usable
Dashboard cards are visible
Quick actions are accessible
Expense form is usable
No important horizontal overflow
```

This is a smoke test, not visual pixel comparison.

Do not add screenshot-diff infrastructure.

---

# 19. API Mocking Rules

Mock only Gemini-dependent endpoints in automated browser tests:

```text
POST /api/receipts/{id}/extract
POST /api/expenses/{id}/translate
```

Normal workflows should use the real backend for:

```text
Authentication
Categories
Expense CRUD
Expense confirmation
Expense delete
Receipt upload
Receipt list/detail
Excel export
```

If extraction creates a linked expense in the real backend, choose a backend test stub or seed the required draft expense before fulfilling the intercepted response.

Do not return an expense ID that does not exist if the frontend immediately loads it from the real backend.

Keep mocked and real state consistent.

---

# 20. Suggested E2E Structure

Use a simple structure:

```text
frontend/
├── e2e/
│   ├── fixtures/
│   │   └── test-receipt.png
│   ├── helpers/
│   │   ├── auth.ts
│   │   └── testData.ts
│   ├── auth.spec.ts
│   ├── expense.spec.ts
│   ├── receipt.spec.ts
│   ├── confirmation.spec.ts
│   ├── translation.spec.ts
│   ├── export.spec.ts
│   ├── isolation.spec.ts
│   ├── dashboard.spec.ts
│   └── mobile.spec.ts
└── playwright.config.ts
```

Combine files when that keeps the suite simpler.

Avoid too many helper layers.

---

# 21. Backend Test Verification

Run:

```bash
cd backend
source venv/bin/activate
pytest
```

Expected current baseline:

```text
662 passed
```

If the result differs, report the exact change.

Do not change backend tests merely to make them pass.

---

# 22. Frontend Test and Build Verification

Run:

```bash
cd frontend
npm run test
npm run build
```

Expected current baseline:

```text
400 frontend tests passing
Zero TypeScript errors
Clean Vite build
```

If new supporting unit tests are added, report the new total.

---

# 23. Playwright Verification

Run:

```bash
cd frontend
npm run test:e2e
```

Also verify headed mode once:

```bash
npm run test:e2e:headed
```

Report:

```text
Number of Playwright tests
Passed
Failed
Skipped
Browser used
Total runtime
```

Do not claim manual verification if it was not actually performed.

---

# 24. Manual Integration Checklist

Manually verify at least once:

```text
Register and login
Create manual expense
Edit expense
Delete expense
Upload receipt
Run one real extraction only if Gemini quota is intentionally available
Confirm draft expense
Run one real translation only if Gemini quota is intentionally available
Export Excel
Switch English/Thai
Refresh protected pages
Logout
```

If real Gemini is not tested:

```text
State clearly that Gemini behavior was verified through mocks only
```

Do not consume quota without intentional approval.

---

# 25. Security and Privacy Checks

Verify:

```text
Passwords are never stored in localStorage
Tokens are not logged
API keys are not exposed in frontend files
Uploaded receipt paths are not exposed
Other users' records are inaccessible
Raw stack traces are hidden
Production secrets are not committed
```

Check:

```text
.gitignore
frontend/.env
backend/.env
```

Do not print secret values in the report.

---

# 26. Test Artifact Cleanup

Add to `.gitignore` if needed:

```text
frontend/test-results/
frontend/playwright-report/
frontend/blob-report/
frontend/.playwright/
```

Keep:

```text
Playwright config
E2E tests
Safe test fixture
```

Do not commit generated reports unless the course specifically requires them.

---

# 27. Documentation Update

Update the project README with:

```text
How to create the E2E database
How to apply migrations
How to start backend
How to start frontend
How to run backend tests
How to run frontend tests
How to run Playwright tests
Gemini mocking note
Dedicated database warning
```

Keep instructions for:

```text
macOS
Windows PowerShell
```

Do not place real credentials in documentation.

---

# 28. Final Commands

Document a clear run order.

Terminal 1:

```bash
cd backend
source venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload
```

Windows PowerShell equivalent:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --reload
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Terminal 3:

```bash
cd frontend
npm run test:e2e
```

For unit verification:

```bash
cd backend
pytest
```

```bash
cd frontend
npm run test
npm run build
```

---

# Do Not Implement

Do not implement:

- New application features
- Production deployment
- CI/CD pipeline unless already requested
- Load testing
- Real Gemini usage in automated tests
- Full visual-regression testing
- Cross-browser testing beyond Chromium
- Destructive cleanup of development or production databases

---

# Expected Result

After this step:

- Playwright installed and configured
- Dedicated safe E2E environment
- Core browser workflows tested
- Gemini-dependent calls mocked
- Authentication integration verified
- Manual expense workflow verified
- Receipt upload workflow verified
- Confirmation and translation verified
- Excel download verified
- User isolation verified
- Dashboard consistency verified
- Mobile smoke test completed
- Backend tests passing
- Frontend tests passing
- Production build passing
- E2E documentation added

---

# Required Completion Report

Provide:

1. Changed and created files
2. Playwright package and configuration
3. E2E environment setup
4. Test database safety behavior
5. Test-data strategy
6. Authentication workflow result
7. Manual expense workflow result
8. Receipt upload/extraction workflow result
9. Confirmation workflow result
10. Translation workflow result
11. Excel download result
12. User isolation result
13. Dashboard consistency result
14. Error-handling smoke result
15. Mobile-layout smoke result
16. Gemini mocking behavior
17. Backend pytest result
18. Frontend unit-test result
19. Frontend build result
20. Playwright result
21. Manual verification actually completed
22. README/documentation changes
23. Any integration bugs found and fixed
24. Any untested limitations

Be honest about anything not manually tested.

Do not produce a long walkthrough unless an error occurs.
