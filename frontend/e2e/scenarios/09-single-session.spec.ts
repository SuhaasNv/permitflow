import { expect, test } from '@playwright/test'

import { OFFICER, PASSWORD, openCase, seedVisitConfirmed, signIn } from '../helpers.js'

/** US-093: one live session per account. The officer records a finding on one device (the checklist
 * autosaves), signs in on a second device, takes the session over, and continues from the saved draft;
 * the first device lands on the sign-in page with the reason and the time. */
test('single session: the second device takes over and continues from the last save', async ({ browser }) => {
  const app = await seedVisitConfirmed()

  const ipad = await browser.newContext({ viewport: { width: 820, height: 1180 } })
  const first = await ipad.newPage()
  await signIn(first, OFFICER)
  await openCase(first, app.reference)
  await first.getByRole('link', { name: 'Open checklist' }).click()
  const groups = first.getByRole('group', { name: 'Result' })
  await expect(groups).toHaveCount(17)
  await groups.nth(0).getByRole('button', { name: 'Unsatisfactory', exact: true }).click()
  await first.getByLabel(/Comment/).fill('Recorded on the first device before the hand-over.')
  await expect(first.getByText('Saved just now')).toBeVisible({ timeout: 5000 })

  // Second device: the plain sign-in is refused and names the first device; the take-over continues.
  const laptop = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const second = await laptop.newPage()
  await second.goto('/login')
  await second.getByLabel(/Email address/).fill(OFFICER)
  await second.getByLabel(/^Password/).fill(PASSWORD)
  await second.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(second.getByText(/This account is signed in on Chrome on (Mac|Linux|Windows), last active/)).toBeVisible()
  await expect(second.getByLabel(/^Password/)).toHaveValue(PASSWORD)
  await second.getByRole('button', { name: 'Sign out the other device and continue' }).click()
  await expect(second.getByRole('button', { name: 'Sign out', exact: true })).toBeVisible()

  // Continuity: the draft the first device saved is what the second device opens.
  await openCase(second, app.reference)
  await second.getByRole('link', { name: 'Continue checklist' }).click()
  await expect(second.getByRole('group', { name: 'Result' })).toHaveCount(17)
  await expect(second.getByLabel(/Comment/)).toHaveValue('Recorded on the first device before the hand-over.')
  await expect(second.getByText('1 of 17 assessed, 0 flagged').first()).toBeVisible()

  // The first device's next request ends its session, and the sign-in page says why and when.
  await first.reload()
  await expect(first.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible()
  await expect(first.getByText(/Your session ended: this account signed in on another device at \d{1,2} \w{3}, \d{2}:\d{2}\./)).toBeVisible()

  // Signing out on the second device frees the account: the first device signs in again without a take-over.
  await second.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(second.getByRole('button', { name: 'Sign in', exact: true })).toBeVisible()
  await first.getByLabel(/Email address/).fill(OFFICER)
  await first.getByLabel(/^Password/).fill(PASSWORD)
  await first.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(first.getByRole('button', { name: 'Sign out', exact: true })).toBeVisible()

  await ipad.close()
  await laptop.close()
})
