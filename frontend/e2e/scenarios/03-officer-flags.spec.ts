import { expect, test } from '@playwright/test'

import { OFFICER, OPERATOR, auditSummaries, confirmDialog, openCase, seedUnderReview, signIn, signOut, status } from '../helpers.js'

/** Workflow 3: the officer points something out (template and free text), changes their mind once, and asks for a resubmission. */
test('officer adds feedback, undoes a withdraw, requests resubmission; operator sees it on top', async ({ page }) => {
  const app = await seedUnderReview()

  await signIn(page, OFFICER)
  await openCase(page, app.reference)

  // free text on a section
  await page.getByRole('button', { name: 'Add feedback' }).click()
  await page.getByLabel(/About/).selectOption('section:premises')
  await page.getByLabel(/Feedback for the operator/).fill('Please confirm the premises unit number against your tenancy agreement.')
  await page.locator('form').getByRole('button', { name: 'Add feedback' }).click()
  await expect(page.getByText('draft, not sent yet').first()).toBeVisible()

  // a template on a document
  await page.getByRole('button', { name: 'Add feedback' }).click()
  await page.getByLabel(/Template/).selectOption({ index: 1 })
  await page.getByLabel(/About/).selectOption('document:floor_plan')
  await page.locator('form').getByRole('button', { name: 'Add feedback' }).click()
  await expect(page.locator('aside')).toContainText('2 open')

  // an unsent item offers Withdraw only; withdraw, then undo within the window
  await expect(page.getByRole('button', { name: 'Mark resolved' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Withdraw' }).last().click()
  await expect(page.locator('aside')).toContainText('1 open')
  await page.getByRole('button', { name: 'Undo' }).click()
  await expect(page.locator('aside')).toContainText('2 open')

  await page.getByRole('button', { name: 'Request resubmission' }).click()
  await confirmDialog(page, 'Request resubmission')
  await expect(status(page)).toHaveText('Pending Pre-Site Resubmission')
  await expect(page.getByText('sent to operator').first()).toBeVisible()
  const trail = await auditSummaries(page)
  expect(trail.filter((s: string) => s.startsWith('Feedback added'))).toHaveLength(2)
  expect(trail.filter((s: string) => s.startsWith('Feedback withdrawn'))).toHaveLength(1)
  expect(trail.filter((s: string) => s.includes('restored to open (undo)'))).toHaveLength(1)
  expect(trail).toContain('2 feedback items sent to the operator')
  expect(trail).toContain('Status: Under Review → Pending Pre-Site Resubmission')
  await signOut(page)

  await signIn(page, OPERATOR)
  await page.goto(app.url)
  await expect(page.getByText('The licensing office asked for 2 changes')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Resubmit' })).toBeDisabled()
  await expect(page.locator('main')).toContainText('Nothing has changed yet')
  await page.goto(`${app.url}/form/business`)
  await expect(page.getByText('did not ask for changes here')).toBeVisible()
  await expect(page.locator('[name="business_name"]')).toBeDisabled()
  await page.goto(`${app.url}/form/premises`)
  await expect(page.getByText('asked for a change here')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save and go to documents' })).toBeVisible()
})
