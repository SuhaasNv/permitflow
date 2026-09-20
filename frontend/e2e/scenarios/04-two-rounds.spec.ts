import { expect, test } from '@playwright/test'

import {
  OFFICER,
  OPERATOR,
  acceptVisit,
  auditSummaries,
  confirmDialog,
  openCase,
  proposeVisit,
  seedPendingResubmission,
  signIn,
  signOut,
  status,
} from '../helpers.js'

/** Workflow 4: two consecutive resubmission rounds, each compared and resolved, then the outcome. */
test('two resubmission rounds: fix, resubmit, compare, resolve, again, then approve', async ({ page }) => {
  const app = await seedPendingResubmission()

  // ---- round 1: operator fixes the premises and resubmits ----
  await signIn(page, OPERATOR)
  await page.goto(`${app.url}/form/premises`)
  await page.locator('[name="address_line_1"]').fill('10 Jalan Besar #01-21')
  await page.getByRole('button', { name: 'Save and go to resubmit' }).click()
  await expect(page).toHaveURL(new RegExp(`${app.url}$`))
  await expect(page.locator('main')).toContainText('Ready to resubmit: 1 of 1 flagged item changed')
  await page.getByRole('button', { name: 'Resubmit' }).click()
  await confirmDialog(page, 'Resubmit')
  await expect(page.getByRole('heading', { name: 'Changes resubmitted' })).toBeVisible()
  await signOut(page)

  // ---- officer reviews round 1: the premises change is not good enough (Not fixed), plus a second item ----
  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await expect(page.getByText('Revision 2 resubmitted')).toBeVisible()
  await expect(page.getByText('Addressed in Revision 2').first()).toBeVisible()
  await page.getByRole('button', { name: 'Start review' }).click()
  await confirmDialog(page, 'Start review')
  await page.getByRole('button', { name: 'Not fixed' }).click()
  await expect(page.locator('aside')).toContainText('Draft, not sent yet')
  await page.getByRole('button', { name: 'Add feedback' }).click()
  await page.getByLabel(/About/).selectOption('section:operations')
  await page.getByLabel(/Feedback for the operator/).fill('State the opening hours per day.')
  await page.locator('form').getByRole('button', { name: 'Add feedback' }).click()
  await page.getByRole('button', { name: 'Request resubmission' }).click()
  await confirmDialog(page, 'Request resubmission')
  await expect(status(page)).toHaveText('Pending Pre-Site Resubmission')
  await signOut(page)

  // ---- round 2: premises (reopened, same text) and operations are open; business is locked ----
  await signIn(page, OPERATOR)
  await page.goto(app.url)
  await expect(page.getByText('The licensing office asked for 2 changes')).toBeVisible()
  await page.goto(`${app.url}/form/business`)
  await expect(page.getByText('did not ask for changes here')).toBeVisible()
  await page.goto(`${app.url}/form/premises`)
  await expect(page.getByText('Please confirm the premises unit number.')).toBeVisible()
  await page.locator('[name="address_line_1"]').fill('10 Jalan Besar #01-12')
  await page.getByRole('button', { name: 'Save and continue' }).click()
  await expect(page).toHaveURL(/\/form\/operations$/)
  await page.locator('[name="operating_hours"]').fill('Mon-Sun 7:00am to 9:00pm')
  await page.getByRole('button', { name: 'Save and go to resubmit' }).click()
  await page.getByRole('button', { name: 'Resubmit' }).click()
  await confirmDialog(page, 'Resubmit')
  await expect(page.getByRole('heading', { name: 'Changes resubmitted' })).toBeVisible()
  await page.goto(`${app.url}/history`)
  await expect(page.getByText('Revision 3', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'What changed from Revision 2' }).click()
  await expect(page.getByText('Mon-Sun 7:00am to 9:00pm').first()).toBeVisible()
  await signOut(page)

  // ---- officer: compare 2 to 3, resolve, decide ----
  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  await expect(page.getByText('Revision 3 resubmitted')).toBeVisible()
  await expect(page.locator('section:has(#compare-title)').getByText('Operations').first()).toBeVisible()
  await page.getByRole('button', { name: 'Start review' }).click()
  await confirmDialog(page, 'Start review')
  await page.getByRole('button', { name: 'Mark resolved' }).first().click()
  await expect(page.locator('aside').getByText('Resolved', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Mark resolved' }).click()
  // The visit is arranged first (US-084): the officer proposes, the operator accepts, then it can be marked done.
  await proposeVisit(page)
  await expect(page.getByRole('button', { name: 'Mark site visit done' })).toBeDisabled()
  await acceptVisit(app.id)
  await page.reload()
  for (const [action, confirm] of [
    ['Mark site visit done', 'Mark done'],
    ['Route to approval', 'Route to approval'],
  ] as const) {
    await page.getByRole('button', { name: action }).click()
    await confirmDialog(page, confirm)
    await page.waitForTimeout(300)
  }
  await page.getByRole('button', { name: 'Approve' }).click()
  await confirmDialog(page, 'Approve')
  await expect(status(page)).toHaveText('Approved')
  const trail = await auditSummaries(page)
  expect(trail.filter((s: string) => /^Revision \d resubmitted/.test(s))).toHaveLength(2)
  expect(trail.filter((s: string) => s.startsWith('Feedback on') && s.endsWith('addressed in Revision 2'))).toHaveLength(1)
  expect(trail.filter((s: string) => s.startsWith('Feedback on') && s.endsWith('addressed in Revision 3'))).toHaveLength(2)
  expect(trail.filter((s: string) => s.includes('not fixed'))).toHaveLength(1)
  expect(trail.filter((s: string) => s.endsWith('resolved'))).toHaveLength(2)
  expect(trail).toContain('Status: Route to Approval → Approved')
})
