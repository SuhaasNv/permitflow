import { defineConfig, devices } from '@playwright/test'

/**
 * Critical-journey E2E (US-005) and one scenario per workflow (US-042, `e2e/scenarios`). Runs against
 * the Vite dev server on :3000 and a backend with the mock AI provider (E2E_API_URL, default :8000; the
 * scenarios seed data through it). Locally: `npm run e2e` (expects both servers up, as in README).
 * In CI the workflow starts both before this config runs (see .github/workflows/ci.yml).
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
