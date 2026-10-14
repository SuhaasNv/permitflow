import { expect, test } from '@playwright/test'

import { ADMIN, signIn } from '../helpers.js'

/** AI usage (US-100): the administrator opens it from the side rail, sees today against the daily cap and the
 * one-line totals, the filters travel in the address, and the CSV downloads with the current range. */
test('admin: AI usage page, filters in the address, CSV download', async ({ page }) => {
  await signIn(page, ADMIN)
  await page.getByRole('link', { name: 'AI usage' }).first().click()
  await expect(page).toHaveURL(/\/admin\/ai-usage$/)
  await expect(page.getByRole('heading', { level: 1, name: 'AI usage' })).toBeVisible()

  await expect(page.getByText('Today against the daily cap').first()).toBeVisible()
  await expect(page.getByText(/^of [\d,]+ checks$/).first()).toBeVisible()
  await expect(page.getByLabel('Totals for the selected range')).toContainText('US$')

  await page.getByRole('button', { name: '7 days' }).click()
  await expect(page).toHaveURL(/range=7/)
  await expect(page.getByRole('button', { name: '7 days' })).toHaveAttribute('aria-pressed', 'true')

  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export CSV' }).click()
  expect((await download).suggestedFilename()).toBe('ai-usage.csv')
})
