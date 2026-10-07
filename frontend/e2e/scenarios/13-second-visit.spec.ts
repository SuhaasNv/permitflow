import { expect, test } from '@playwright/test'

import {
  OFFICER,
  OPERATOR,
  confirmDialog,
  openCase,
  proposeVisit,
  seedReturnedAfterClarification,
  signIn,
  signOut,
  status,
} from '../helpers.js'

/** UAT run 5 (24 Sep 2026): a case returned to review after the post-site clarification is a review again, the
 * operator answers the second visit's appointment, the second visit starts blank and the first stays readable. */
test('second visit: review again, the operator answers the new date, visit 1 kept as history', async ({ page }) => {
  const app = await seedReturnedAfterClarification()

  // ---- F15: back in review the officer can give feedback; F17 and F18: visit 1 is history ----
  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await expect(status(page)).toHaveText('Under Review')
  await expect(page.getByRole('button', { name: 'Add feedback' })).toBeVisible()
  const earlier = page.locator('section:has(#earlier-visits-title)')
  await expect(earlier).toContainText('Visit 1')
  await earlier.getByText('Show').click()
  await expect(earlier).toContainText('Fixed on site; photo on file.')
  await earlier.getByRole('link', { name: 'View visit 1 checklist' }).click()
  await expect(page.getByText('Visit 1, an earlier visit')).toBeVisible()
  await expect(page.getByRole('button', { name: /submit/i })).toHaveCount(0)
  await page.goBack()

  // ---- F16: the second visit is proposed and the operator answers it ----
  await proposeVisit(page)
  await signOut(page)
  await signIn(page, OPERATOR)
  await page.goto(app.url)
  const card = page.locator('section:has(#visit-title)')
  await expect(card.getByRole('button', { name: 'Accept this date' })).toBeVisible()
  await card.getByRole('button', { name: 'Accept this date' }).click()
  await confirmDialog(page, 'Accept the date')
  await expect(card).toContainText('Confirmed')
  await page.getByRole('link', { name: 'History' }).click()
  await expect(page.locator('section:has(#visit-history-title)')).toContainText('Visit 2')
  await expect(page.locator('section:has(#clar-history-title-1)')).toContainText('Fixed on site; photo on file.')
  await expect(page.locator('section:has(#visit-history-title-1)')).toContainText('Visit 1')
  await signOut(page)

  // ---- F17: the officer opens a blank checklist for visit 2 ----
  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await page.getByRole('link', { name: 'Open checklist' }).click()
  await expect(page.getByText('0 of 17 assessed, 0 flagged').first()).toBeVisible()
  await expect(page.getByText(/Visit 2/).first()).toBeVisible()
  await signOut(page)
})
