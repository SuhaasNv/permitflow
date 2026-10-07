import { expect, test } from '@playwright/test'

import { ADMIN, SPARE, restoreSpareAccount, seedUnderReview, signIn, signOut } from '../helpers.js'

/** The administrator (US-070, US-072, US-073): the overview with live numbers, a case read without a
 * single control, the activity feed with a user row, and the spare account changed and restored. */
// Whatever happens between the change and the restore below, the spare account ends as seeded.
test.afterEach(async () => {
  await restoreSpareAccount()
})

test('admin: overview, read-only case, activity feed, user management restored at the end', async ({ page }) => {
  const app = await seedUnderReview()
  await signIn(page, ADMIN)

  // Overview: the strip, every status, the health block on the mock provider, today's numbers.
  await expect(page.getByRole('heading', { name: 'Operations overview' })).toBeVisible()
  await expect(page.getByRole('list', { name: 'Key numbers' })).toContainText('With the office')
  await expect(page.getByRole('row', { name: /Under Review/ })).toBeVisible()
  await expect(page.getByText('(not visible to officers)')).toBeVisible()
  await expect(page.getByText(/Provider: none \(mock\)/)).toBeVisible()
  await expect(page.getByText(/^Singapore calendar day, /)).toBeVisible()

  // The case, read-only: the banner, no action, the checklist card without a way to open a new one.
  await page.goto(`/admin/applications/${app.id}`)
  await expect(page.getByText('Read-only', { exact: true })).toBeVisible()
  await expect(page.getByText(app.reference).first()).toBeVisible()
  await expect(page.getByRole('button', { name: /Start review|Request resubmission|Reject|Approve/ })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Add feedback' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Re-run check' })).toHaveCount(0)
  await expect(page.getByText('Feedback is written by the licensing officer.')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Overview' }).first()).toBeVisible()

  // Activity: the seeded case's events, newest first, and the filters.
  await page.goto('/admin/activity')
  await expect(page.getByRole('heading', { name: 'Activity' })).toBeVisible()
  await expect(page.getByRole('link', { name: app.reference }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Status' }).click()
  await expect(page.getByText(/Application Received → Under Review/).first()).toBeVisible()

  // Users: the spare officer becomes an operator and back; the own row and the demo rows are locked.
  await page.goto('/admin/users')
  await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible()
  const own = page.locator('li', { hasText: '(you)' })
  await expect(own.getByRole('button', { name: 'Change role' })).toBeDisabled()
  const demo = page.locator('li', { hasText: 'officer@permitflow.example.sg' }).first()
  await expect(demo.getByRole('button', { name: 'Deactivate' })).toBeDisabled()
  const spare = page.locator('li', { hasText: SPARE })
  await spare.getByRole('button', { name: 'Change role' }).click()
  const dialog = page.getByRole('dialog', { name: /Change .* role\?/ })
  await dialog.getByRole('radio', { name: 'Operator' }).check()
  await dialog.getByRole('button', { name: 'Change role' }).click()
  await expect(spare).toContainText('Operator')
  await spare.getByRole('button', { name: 'Deactivate' }).click()
  await page
    .getByRole('dialog', { name: /Deactivate .*\?/ })
    .getByRole('button', { name: 'Deactivate' })
    .click()
  await expect(spare).toContainText('Deactivated')

  // The change is on the feed as a user row without a case.
  await page.goto('/admin/activity')
  await expect(page.getByText(/role changed from officer to operator/).first()).toBeVisible()
  await expect(page.getByText('no case').first()).toBeVisible()

  // Restore the spare account so the next run, and the next reviewer, find it as seeded.
  await page.goto('/admin/users')
  const spareAgain = page.locator('li', { hasText: SPARE })
  await spareAgain.getByRole('button', { name: 'Reactivate' }).click()
  await page
    .getByRole('dialog', { name: /Reactivate .*\?/ })
    .getByRole('button', { name: 'Reactivate' })
    .click()
  await expect(spareAgain).toContainText('Active')
  await spareAgain.getByRole('button', { name: 'Change role' }).click()
  const back = page.getByRole('dialog', { name: /Change .* role\?/ })
  await back.getByRole('radio', { name: 'Licensing officer' }).check()
  await back.getByRole('button', { name: 'Change role' }).click()
  await expect(spareAgain).toContainText('Licensing officer')
  await signOut(page)
})
