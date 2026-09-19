import { expect, test } from '@playwright/test'

import { OFFICER, OPERATOR, auditSummaries, confirmDialog, openCase, seedUnderReview, signIn, signOut, status } from '../helpers.js'

/** Workflow 6: a rejection needs a note, the operator sees the outcome and the note, the record shows who decided. */
test('officer rejects with a required note; operator sees the outcome', async ({ page }) => {
  const app = await seedUnderReview()

  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await page.getByRole('button', { name: 'Reject' }).click()
  const dialog = page.locator('dialog[open]')
  await expect(dialog.getByText('your note, which is required')).toBeVisible()
  await dialog.getByRole('button', { name: 'Reject' }).click()
  await expect(dialog).toContainText('Write a note for the operator')
  await expect(status(page)).toHaveText('Under Review')
  await dialog.getByLabel(/Note to the operator/).fill('The premises are not licensed for food preparation.')
  await confirmDialog(page, 'Reject')
  await expect(status(page)).toHaveText('Rejected')
  await expect(page.locator('main')).toContainText('Note: The premises are not licensed for food preparation.')
  await expect(page.locator('aside')).toContainText('No further action is available')
  const trail = await auditSummaries(page)
  expect(trail).toContain('Status: Under Review → Rejected')
  await signOut(page)

  await signIn(page, OPERATOR)
  await page.goto(app.url)
  await expect(status(page)).toHaveText('Rejected')
  await expect(page.getByRole('heading', { name: 'Your licence application was not approved' })).toBeVisible()
  await expect(page.getByText('The premises are not licensed for food preparation.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Withdraw application' })).toHaveCount(0)
  await page.getByRole('button', { name: /Notifications/ }).click()
  await expect(page.getByRole('dialog', { name: 'Notifications' })).toContainText(`${app.reference}: Rejected`)
})
