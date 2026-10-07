import { expect, test } from '@playwright/test'

import {
  OFFICER,
  OPERATOR,
  auditSummaries,
  confirmDialog,
  openCase,
  seedUnderReview,
  signIn,
  signOut,
  status,
  workingDayAhead,
} from '../helpers.js'

/** Workflow 7 (US-084): the officer proposes a visit, the operator counters, the officer accepts the
 * operator's date, the operator asks to move it, the officer keeps the date, then marks the visit done. */
test('site visit: propose, counter, accept, reschedule request, keep, done', async ({ page }) => {
  const app = await seedUnderReview()
  const first = workingDayAhead(3)
  const second = workingDayAhead(5)
  const third = workingDayAhead(8)

  // ---- officer proposes ----
  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await page.getByRole('button', { name: 'Mark site visit scheduled' }).click()
  const dialog = page.locator('dialog[open]')
  await expect(dialog).toContainText('The case moves to Site Visit Scheduled now')
  await dialog.getByRole('button', { name: 'Propose visit' }).click()
  await expect(dialog).toContainText('Choose a date.')
  await dialog.getByLabel(/Date/).fill(first)
  await dialog.getByRole('button', { name: /Afternoon/ }).click()
  await dialog.getByLabel(/Note for the operator/).fill('Have the pest control contract on the premises.')
  await dialog.getByRole('button', { name: 'Propose visit' }).click()
  await expect(status(page)).toHaveText('Site Visit Scheduled')
  const rail = page.locator('section:has(#visit-title)')
  await expect(rail).toContainText('Waiting for the operator')
  await expect(rail).toContainText('afternoon (14:00 to 17:00)')
  await expect(rail.getByRole('button', { name: 'Confirm without a reply' })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Mark site visit done' })).toBeDisabled()
  await signOut(page)

  // ---- operator counters ----
  await signIn(page, OPERATOR)
  await page.goto(app.url)
  await expect(status(page)).toHaveText('Pending Site Visit')
  const card = page.locator('section:has(#visit-title)')
  await expect(card).toContainText('Waiting for your reply')
  await expect(card).toContainText('Note: Have the pest control contract on the premises.')
  await expect(card).not.toContainText('Waiting for the operator')
  await expect(card).toContainText('Reply by')
  const form = card.getByRole('form', { name: 'Propose this date' })
  await form.getByRole('button', { name: 'Propose this date' }).click()
  await expect(form).toContainText('Choose a date.')
  await expect(form).toContainText('Say why')
  await form.getByLabel(/Date/).fill(second)
  await form.getByLabel(/Reason/).fill('The shop is closed that afternoon.')
  await form.getByRole('button', { name: 'Propose this date' }).click()
  await expect(card).toContainText('Waiting for the officer')
  await expect(card).toContainText('You proposed')
  await expect(card.getByRole('button', { name: 'Accept this date' })).toHaveCount(0)
  await signOut(page)

  // ---- officer accepts the operator's date ----
  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await expect(rail).toContainText('Waiting for you')
  await expect(rail).toContainText('Operator proposes')
  await expect(rail).toContainText('"The shop is closed that afternoon."')
  await rail.getByRole('button', { name: /^Accept / }).click()
  await expect(rail).toContainText('Confirmed')
  await expect(page.getByRole('button', { name: 'Mark site visit done' })).toBeEnabled()
  await signOut(page)

  // ---- operator asks to move the confirmed visit; the officer keeps it ----
  await signIn(page, OPERATOR)
  await page.goto(app.url)
  await expect(card).toContainText('Confirmed')
  await card.getByRole('button', { name: 'Request a different date' }).click()
  const move = card.getByRole('form', { name: 'Send the request' })
  await move.getByLabel(/Date/).fill(third)
  await move.getByLabel(/Reason/).fill('Renovation that week.')
  await move.getByRole('button', { name: 'Send the request' }).click()
  await expect(card).toContainText('Waiting for the officer')
  await page.getByRole('link', { name: 'History' }).click()
  await expect(page.locator('section:has(#visit-history-title)')).toContainText('3 rounds')
  await signOut(page)

  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await rail.getByRole('button', { name: /^Keep / }).click()
  await expect(rail).toContainText('Confirmed')
  await expect(rail).toContainText('Round 3')
  await page.getByRole('button', { name: 'Mark site visit done' }).click()
  await confirmDialog(page, 'Mark done')
  await expect(status(page)).toHaveText('Site Visit Done')
  await expect(rail).toContainText('Done')
  const trail = await auditSummaries(page)
  expect(trail.some((t) => t.startsWith('Site visit proposed:'))).toBe(true)
  expect(trail).toContain('Operator proposed another visit date (round 2)')
  expect(trail.some((t) => t.includes("(the operator's date)"))).toBe(true)
  expect(trail.some((t) => t.includes('(original date kept)'))).toBe(true)
  expect(trail).toContain('Status: Site Visit Scheduled → Site Visit Done')
  await signOut(page)

  // ---- the operator was told at every step ----
  await signIn(page, OPERATOR)
  await page.getByRole('button', { name: /Notifications/ }).click()
  const notifications = page.getByRole('dialog', { name: 'Notifications' })
  await expect(notifications).toContainText(`${app.reference}: Site visit proposed`)
  await expect(notifications).toContainText(`${app.reference}: Site visit confirmed`)
})
