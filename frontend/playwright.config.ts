/**
 * Playwright configuration for Smart Receipt E2E tests.
 *
 * Browser: Bundled Playwright Chromium (build v1117, Chrome 125).
 *   - `npm run dev`, `npm run test`, and `npm run build` do NOT require Playwright
 *     or any browser — they are pure Node/Vite/Vitest operations.
 *   - Only `npm run test:e2e` needs the browser.
 *   - To install the bundled Chromium:  npx playwright install chromium
 *   - If you prefer to use an installed Google Chrome instead, add
 *     `channel: 'chrome'` inside the chromium project's `use` block and
 *     remove the `npx playwright install chromium` step.
 *
 * Approach: Option A — manual startup (documented)
 *   Playwright does NOT start the backend or frontend automatically.
 *   Start both services before running E2E tests:
 *
 *   Terminal 1 (backend):
 *     cd backend
 *     .\venv\Scripts\Activate.ps1          # Windows
 *     alembic upgrade head
 *     uvicorn app.main:app --reload
 *
 *   Terminal 2 (frontend):
 *     cd frontend && npm run dev
 *
 *   Terminal 3 (tests):
 *     cd frontend && npm run test:e2e
 */

import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  // All E2E test files live in frontend/e2e/
  testDir: './e2e',

  // Give each test up to 30 seconds before failing
  timeout: 30_000,

  // Retry once on CI, never locally
  retries: process.env.CI ? 1 : 0,

  // Run tests sequentially — the shared E2E database requires predictable state
  workers: 1,

  // Screenshot on failure, trace on first retry
  use: {
    baseURL: 'http://127.0.0.1:5173',
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    // Accept the SweetAlert2 dialogs through the DOM rather than native browser dialogs
    actionTimeout: 10_000,
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Output directories (added to .gitignore)
  outputDir: 'test-results/',
})
