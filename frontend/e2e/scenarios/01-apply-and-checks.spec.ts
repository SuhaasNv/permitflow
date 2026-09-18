import { expect, test } from '@playwright/test'

import {
  BUSINESS,
  DOCUMENT_TYPES,
  OFFICER,
  OPERATIONS,
  OPERATOR,
  PREMISES,
  auditSummaries,
  fillSection,
  openCase,
  signIn,
  signOut,
  status,
  uploadTxt,
} from '../helpers.js'

/** Workflow 1: the operator applies through the UI and every document check lands before submission. */
test('operator applies, every AI check lands, submission is recorded', async ({ page }) => {
  await signIn(page, OPERATOR)
  await page.goto('/app/dashboard')
  await page.getByRole('button', { name: 'New application' }).click()
  await expect(page).toHaveURL(/\/app\/applications\/[0-9a-f-]+$/)
  const appUrl = new URL(page.url()).pathname
  const reference = await page.locator('main span.font-mono').first().innerText()
  await expect(page.getByRole('link', { name: 'Start application' })).toBeVisible()

  await page.goto(`${appUrl}/form/business`)
  await fillSection(page, BUSINESS, { entity_type: 'private_limited' })
  await expect(page).toHaveURL(/\/form\/premises$/)
  await fillSection(page, PREMISES, { premises_type: 'shophouse' })
  await fillSection(page, OPERATIONS)
  await page.locator('[name="information_accurate"]').check()
  await page.locator('[name="consent_to_inspection"]').check()
  await page.getByRole('button', { name: /Save and continue/ }).click()
  await expect(page).toHaveURL(/\/documents$/)

  for (const slot of DOCUMENT_TYPES) await uploadTxt(page, slot, `${slot}.txt`)
  // every check reaches a final state without a reload (the slot polls)
  for (const slot of DOCUMENT_TYPES)
    await expect(page.locator(`#slot-${slot} [data-verification]`)).toHaveAttribute(
      'data-verification',
      /verified|issues_found|needs_review|unreadable/,
      {
        timeout: 60_000,
      },
    )

  await page.goto(`${appUrl}/review`)
  await expect(page.getByText('100%')).toBeVisible()
  await page.getByRole('button', { name: 'Submit application' }).click()
  await page.locator('dialog[open]').getByRole('button', { name: 'Submit application' }).click()
  await expect(page).toHaveURL(/\/submitted$/)
  await expect(page.getByRole('heading', { name: 'Application submitted' })).toBeVisible()
  await page.goto(appUrl)
  await expect(status(page)).toHaveText('Submitted')
  await expect(page.getByRole('button', { name: 'Withdraw application' })).toBeVisible()
  await signOut(page)

  // the record: creation, four sections, four uploads, four checks, revision 1, status change
  await signIn(page, OFFICER)
  await openCase(page, reference)
  const trail = await auditSummaries(page)
  expect(trail.filter((s: string) => s.startsWith('Application') && s.endsWith('created'))).toHaveLength(1)
  expect(trail.filter((s: string) => s.startsWith('Section'))).toHaveLength(4)
  expect(trail.filter((s: string) => s.startsWith('Document uploaded'))).toHaveLength(4)
  expect(trail.filter((s: string) => s.startsWith('Check finished'))).toHaveLength(4)
  expect(trail).toContain('Revision 1 submitted')
  expect(trail).toContain('Status: Draft → Application Received')
})
