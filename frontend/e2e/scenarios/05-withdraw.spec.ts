import { expect, test } from '@playwright/test'

import { OFFICER, OPERATOR, auditSummaries, confirmDialog, openCase, seedUnderReview, signIn, signOut, status } from '../helpers.js'

/** Workflow 5: the operator withdraws while the officer is reviewing; the officer is told and nothing can follow. */
test('operator withdraws with a reason; officer sees it, the record shows the operator as actor', async ({ page }) => {
  const app = await seedUnderReview()

  await signIn(page, OPERATOR)
  await page.goto(app.url)
  await page.getByRole('button', { name: 'Withdraw application' }).click()
  await page
    .locator('dialog[open]')
    .getByLabel(/Reason/)
    .fill('We are not opening this outlet after all.')
  await confirmDialog(page, 'Withdraw application')
  await expect(status(page)).toHaveText('Withdrawn')
  await expect(page.getByRole('heading', { name: 'You withdrew this application' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Withdraw application' })).toHaveCount(0)
  await signOut(page)

  await signIn(page, OFFICER)
  await page.getByRole('button', { name: /Notifications/ }).click()
  await expect(page.getByRole('dialog', { name: 'Notifications' })).toContainText(`${app.reference}: Withdrawn`)
  await page.keyboard.press('Escape')
  await page.goto('/officer/queue')
  await page.getByRole('tab', { name: /Decided/ }).click()
  await page.getByRole('searchbox').fill(app.reference)
  await expect(page.locator('main ul li').first()).toContainText('Withdrawn')
  await openCase(page, app.reference)
  await expect(page.locator('main')).toContainText('Withdrawn by the operator: We are not opening this outlet after all.')
  await expect(page.locator('aside')).toContainText('The operator withdrew this application')
  await expect(page.locator('aside').getByRole('button', { name: /Start review|Reject|Add feedback/ })).toHaveCount(0)
  const trail = await auditSummaries(page)
  expect(trail).toContain('Status: Under Review → Withdrawn')
  const section = page.locator('section:has(#audit-title)')
  await expect(section.locator('ol li').filter({ hasText: 'Withdrawn' }).first()).toContainText('(operator)')
})
