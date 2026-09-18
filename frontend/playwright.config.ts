import { defineConfig, devices } from '@playwright/test'

/**
 * Critical-journey E2E (US-005). Runs against a backend on :8000 with the mock AI provider and the Vite
 * dev server on :3000. Locally: `npm run e2e` (expects both servers up, as in README "Run locally").
 * In CI the workflow starts both before this config runs (see .github/workflows/ci.yml).
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
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
