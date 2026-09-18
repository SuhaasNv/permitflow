import { expect, test } from '@playwright/test'

import { OFFICER, OPERATOR, auditSummaries, confirmDialog, openCase, seedSubmitted, signIn, signOut, status } from '../helpers.js'

/** Workflow 2: a submission reaches the officer queue with the right next action, and the review starts. */
test('submission appears in the queue, the officer starts the review, the operator is told', async ({ page }) => {
  const app = await seedSubmitted()

  await signIn(page, OFFICER)
  await page.getByRole('button', { name: /Notifications/ }).click()
  await expect(page.getByRole('dialog', { name: 'Notifications' })).toContainText(app.reference)
  await page.keyboard.press('Escape')

  await page.goto('/officer/queue')
  await page.getByRole('searchbox').fill(app.reference)
  const row = page.locator('main ul li').first()
  await expect(row).toContainText('Application Received')
  await expect(row).toContainText('Start review')
  await expect(row).toContainText('Scenario Kopi House')

  await openCase(page, app.reference)
  await expect(page.getByText('Submission · Revision 1')).toBeVisible()
  await expect(page.locator('main')).toContainText('4 of 4 sections complete')
  await expect(page.locator('main')).toContainText('4 attached')
  await page.getByRole('button', { name: 'Start review' }).click()
  await confirmDialog(page, 'Start review')
  await expect(status(page)).toHaveText('Under Review')
  const trail = await auditSummaries(page)
  expect(trail).toContain('Status: Application Received → Under Review')
  await signOut(page)

  await signIn(page, OPERATOR)
  await page.goto(app.url)
  await expect(status(page)).toHaveText('Under Review')
  await page.getByRole('button', { name: /Notifications/ }).click()
  await expect(page.getByRole('dialog', { name: 'Notifications' })).toContainText(`${app.reference}: Under Review`)
})
