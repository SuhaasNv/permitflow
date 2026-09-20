import { expect, test } from '@playwright/test'

import { OFFICER, openCase, seedVisitConfirmed, signIn, status } from '../helpers.js'

/** Workflow 8 (US-060): the officer opens the checklist from the case, records findings, saves the draft,
 * and the case shows the summary. Submit (US-063) extends this scenario. */
test('checklist: open from the case, assess items, save the draft, see the summary', async ({ page }) => {
  const app = await seedVisitConfirmed()

  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await expect(page.getByRole('button', { name: 'Mark site visit done' })).toBeEnabled()
  await page.getByRole('link', { name: 'Open checklist' }).click()
  await expect(page.getByRole('heading', { name: 'Site visit checklist' })).toBeVisible()
  await expect(page.getByText('Draft, not submitted')).toBeVisible()
  const groups = page.getByRole('group', { name: 'Result' })
  await expect(groups).toHaveCount(17)
  await expect(page.getByText('0 of 17 assessed, 0 flagged').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Mark visit done and submit' })).toBeDisabled()

  await groups.nth(0).getByRole('button', { name: 'Satisfactory', exact: true }).click()
  await groups.nth(1).getByRole('button', { name: 'Unsatisfactory', exact: true }).click()
  await expect(page.getByText('A comment is required for an unsatisfactory or flagged item.')).toBeVisible()
  await expect(page.getByText('1 comment missing')).toBeVisible()
  await page.getByLabel(/Comment/).fill('Floor slopes away from the trap; water pools by the wok station.')
  await page.getByLabel('Need further clarification').nth(1).check()
  await groups.nth(16).getByRole('button', { name: 'Not applicable' }).click()
  await expect(page.getByText('3 of 17 assessed, 1 flagged').first()).toBeVisible()
  await expect(page.getByText('Assess 14 more items to submit.')).toBeVisible()
  // pressing the selected result again clears it; autosave fires 1.5 s after the last touch (US-061)
  await groups.nth(16).getByRole('button', { name: 'Not applicable' }).click()
  await expect(groups.nth(16).getByRole('button', { name: 'Not applicable' })).toHaveAttribute('aria-pressed', 'false')
  await groups.nth(16).getByRole('button', { name: 'Not applicable' }).click()
  await expect(page.getByText('Saved just now')).toBeVisible({ timeout: 5000 })

  // the draft survives a reload and the case summarises it
  await page.reload()
  await expect(page.getByText('3 of 17 assessed, 1 flagged').first()).toBeVisible()
  await expect(groups.nth(1).getByRole('button', { name: 'Unsatisfactory', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByLabel(/Comment/)).toHaveValue('Floor slopes away from the trap; water pools by the wok station.')
  await page.getByRole('link', { name: 'Back to the case' }).click()
  await expect(status(page)).toHaveText('Site Visit Scheduled')
  await expect(page.locator('section:has(#checklist-title)')).toContainText('Visit 1: 3 of 17 assessed, 1 flagged')
  await expect(page.getByRole('link', { name: 'Continue checklist' })).toBeVisible()
  // with a checklist on record the transitional route to approval is closed after the visit
  await page.getByRole('button', { name: 'Mark site visit done' }).click()
  await page.locator('dialog[open]').getByRole('button', { name: 'Mark done' }).click()
  await expect(status(page)).toHaveText('Site Visit Done')
  await expect(page.getByRole('button', { name: 'Route to approval' })).toBeDisabled()
})
