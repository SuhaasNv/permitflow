import { expect, test } from '@playwright/test'

import { ADMIN, ADMIN_PASSWORD, signIn, signOut } from '../helpers.js'

/** The administrator's settings (US-101): the page from the side rail, a change refused for a wrong password and
 * then made, the history entry, and the revert that puts the setting back on its default. */
test('admin settings: change with step-up, see it in the history, revert it', async ({ page }) => {
  await signIn(page, ADMIN)
  await page.getByRole('link', { name: 'Settings' }).first().click()
  await expect(page.getByRole('heading', { name: 'Settings', level: 1 })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Traffic' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'AI checks' })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Uploads' })).toBeVisible()

  const row = page.locator('li', { hasText: 'max_drafts_per_user' })
  await expect(row).toContainText('Default in force')
  await row.getByRole('button', { name: 'Change Drafts per person' }).click()
  const dialog = page.getByRole('dialog', { name: 'Change drafts per person?' })
  await expect(dialog.getByLabel(/New value/)).toBeFocused()

  // Outside the range: the server's own sentence, nothing sent.
  await dialog.getByLabel(/New value/).fill('0')
  await dialog.getByLabel(/Reason/).fill('End to end check of the settings page')
  await dialog.getByLabel(/Your password/).fill(ADMIN_PASSWORD)
  await dialog.getByRole('button', { name: 'Save change' }).click()
  await expect(dialog.getByText(/Drafts per person cannot go below 1/)).toBeVisible()

  // A wrong password changes nothing.
  await dialog.getByLabel(/New value/).fill('19')
  await dialog.getByLabel(/Your password/).fill('not-the-password')
  await dialog.getByRole('button', { name: 'Save change' }).click()
  await expect(dialog.getByText(/Your password is incorrect/)).toBeVisible()

  await dialog.getByLabel(/Your password/).fill(ADMIN_PASSWORD)
  await dialog.getByRole('button', { name: 'Save change' }).click()
  await expect(dialog).toBeHidden()
  await expect(row).toContainText('Overridden')
  await expect(row).toContainText('End to end check of the settings page')

  // The history lists it first, and Revert sets the default back.
  const history = page.getByRole('list', { name: 'Changes and reverts' })
  await expect(history.getByRole('listitem').first()).toContainText('Drafts per person')
  await history.getByRole('button', { name: /^Revert Drafts per person change/ }).first().click()
  const revert = page.getByRole('dialog', { name: 'Revert this change?' })
  await revert.getByLabel(/Reason/).fill('End to end check done')
  await revert.getByLabel(/Your password/).fill(ADMIN_PASSWORD)
  await revert.getByRole('button', { name: 'Revert change' }).click()
  await expect(revert).toBeHidden()
  await expect(row).toContainText('Default in force')
  await expect(history.getByRole('listitem').first()).toContainText('Revert')
  await signOut(page)
})
