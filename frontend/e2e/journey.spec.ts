import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

const PASSWORD = process.env.SEED_PASSWORD ?? 'PermitFlow!2026'
const OPERATOR = 'operator@permitflow.example.sg'
const OFFICER = 'officer@permitflow.example.sg'

const TXT =
  'Tenancy agreement between landlord and tenant. Business profile ACRA UEN. Floor plan kitchen. Food hygiene certificate. '.repeat(3)

async function signIn(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel(/Email address/).fill(email)
  await page.getByLabel(/^Password/).fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
}

async function signOut(page: Page) {
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
}

async function fillSection(page: Page, values: Record<string, string>, selects: Record<string, string> = {}) {
  for (const [name, value] of Object.entries(values)) await page.locator(`[name="${name}"]`).fill(value)
  for (const [name, value] of Object.entries(selects)) await page.locator(`select[name="${name}"]`).selectOption(value)
  await page.getByRole('button', { name: /Save and (continue|review)/ }).click()
}

async function upload(page: Page, slot: string, filename: string) {
  await page
    .locator(`#slot-${slot} input[type=file]`)
    .first()
    .setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(TXT) })
  await expect(page.locator(`#slot-${slot}`).getByText('Uploaded')).toBeVisible()
}

/**
 * The critical journey the brief describes: operator submits, officer flags, operator fixes only the
 * flagged parts, officer compares, resolves and decides. One test, in order, on a fresh application.
 */
test('submit, flag, fix only flagged, resubmit, compare, resolve, approve', async ({ page }) => {
  // ---- Operator: apply ----
  await signIn(page, OPERATOR)
  await page.getByRole('button', { name: 'New application' }).first().click()
  await expect(page).toHaveURL(/\/app\/applications\/[0-9a-f-]+$/)
  const appUrl = page.url()
  const reference = await page.locator('main span.font-mono').first().innerText()
  expect(reference).toMatch(/^PF-\d{4}-\d{6}$/)

  await page.goto(`${appUrl}/form/business`)
  await fillSection(
    page,
    {
      business_name: 'E2E Kopi House Pte. Ltd.',
      uen: '202355555E',
      contact_name: 'Tan Wei Ling',
      contact_email: 'weiling@e2e.sg',
      contact_phone: '+65 9123 4567',
    },
    { entity_type: 'private_limited' },
  )
  await expect(page).toHaveURL(/\/form\/premises$/)
  await fillSection(
    page,
    { address_line_1: '10 Jalan Besar #01-12', postal_code: '208787', floor_area_sqm: '48', tenancy_expiry: '2027-10-31' },
    { premises_type: 'shophouse' },
  )
  await expect(page).toHaveURL(/\/form\/operations$/)
  await fillSection(page, {
    cuisine_description: 'Kaya toast, soft-boiled eggs, kopi and teh.',
    seating_capacity: '24',
    operating_hours: 'Mon-Sun 7am-9pm',
    food_handlers_count: '4',
  })
  await expect(page).toHaveURL(/\/form\/declarations$/)
  await page.locator('[name="information_accurate"]').check()
  await page.locator('[name="consent_to_inspection"]').check()
  await page.getByRole('button', { name: /Save and review/ }).click()
  await expect(page).toHaveURL(/\/documents$/)

  // ---- Operator: upload four documents; the mock check runs in the background and lands without a reload ----
  for (const slot of ['business_profile', 'floor_plan', 'tenancy_agreement', 'food_hygiene_certificate'])
    await upload(page, slot, `${slot}.txt`)
  await expect(page.locator('[data-verification]').first()).toHaveAttribute('data-verification', /verified|issues_found|needs_review/, {
    timeout: 30_000,
  })

  // ---- Operator: review and submit ----
  await page.goto(`${appUrl}/review`)
  await page.getByRole('button', { name: 'Submit application' }).click()
  await page.locator('dialog[open]').getByRole('button', { name: 'Submit application' }).click()
  await expect(page).toHaveURL(/\/submitted$/)
  await expect(page.getByRole('heading', { name: 'Application submitted' })).toBeVisible()
  await signOut(page)

  // ---- Officer: review, feedback, request resubmission ----
  await signIn(page, OFFICER)
  await page
    .getByRole('link', { name: new RegExp(reference) })
    .first()
    .click()
  await expect(page.locator('main span[data-tone]').first()).toHaveText('Application Received')
  await page.getByRole('button', { name: 'Start review' }).click()
  await page.locator('dialog[open]').getByRole('button', { name: 'Start review' }).click()
  await expect(page.locator('main span[data-tone]').first()).toHaveText('Under Review')

  await page.getByRole('button', { name: 'Add feedback' }).click()
  await page.getByLabel(/About/).selectOption('section:premises')
  await page.getByLabel(/Feedback for the operator/).fill('Please confirm the premises unit number against your tenancy agreement.')
  await page.locator('form').getByRole('button', { name: 'Add feedback' }).click()
  await expect(page.getByText('Draft, not sent yet')).toBeVisible()
  await expect(page.locator('#target-section-premises').getByText('1 open feedback')).toBeVisible()

  await page.getByRole('button', { name: 'Request resubmission' }).click()
  await page.locator('dialog[open]').getByRole('button', { name: 'Request resubmission' }).click()
  await expect(page.locator('main span[data-tone]').first()).toHaveText('Pending Pre-Site Resubmission')
  await expect(page.getByText('Sent to the operator')).toBeVisible()
  await signOut(page)

  // ---- Operator: only the flagged section is editable; fix it and resubmit ----
  await signIn(page, OPERATOR)
  await page.goto(appUrl)
  await expect(page.getByText('The licensing office asked for 1 change')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Resubmit' })).toBeDisabled()
  await page.goto(`${appUrl}/form/business`)
  await expect(page.getByText('did not ask for changes here')).toBeVisible()
  await expect(page.locator('[name="business_name"]')).toBeDisabled()
  await page.goto(`${appUrl}/form/premises`)
  await expect(page.getByText('asked for a change here')).toBeVisible()
  await page.locator('[name="address_line_1"]').fill('10 Jalan Besar #01-21')
  await page.getByRole('button', { name: 'Save section' }).click()
  await expect(page.getByText('Saved just now')).toBeVisible()
  await page.goto(appUrl)
  await page.getByRole('button', { name: 'Resubmit' }).click()
  await page.locator('dialog[open]').getByRole('button', { name: 'Resubmit' }).click()
  await expect(page.getByRole('heading', { name: 'Changes resubmitted' })).toBeVisible()
  await page.goto(`${appUrl}/history`)
  await expect(page.getByText('Revision 2', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'What changed from Revision 1' }).click()
  await expect(page.getByText('10 Jalan Besar #01-21').first()).toBeVisible()
  await signOut(page)

  // ---- Officer: see what changed, resolve, route to a decision ----
  await signIn(page, OFFICER)
  await page
    .getByRole('link', { name: new RegExp(reference) })
    .first()
    .click()
  await expect(page.getByText('Revision 2 resubmitted')).toBeVisible()
  await expect(page.getByText('Changed in Revision 2').first()).toBeVisible()
  await expect(page.locator('section:has(#compare-title)').getByText('1 section')).toBeVisible()
  await expect(page.getByText('Addressed in Revision 2').first()).toBeVisible()
  await page.getByRole('button', { name: 'Start review' }).click()
  await page.locator('dialog[open]').getByRole('button', { name: 'Start review' }).click()
  await page.getByRole('button', { name: 'Mark resolved' }).click()
  await expect(page.locator('aside').getByText('Resolved', { exact: true }).first()).toBeVisible()
  for (const [action, confirm] of [
    ['Mark site visit scheduled', 'Mark scheduled'],
    ['Mark site visit done', 'Mark done'],
    ['Route to approval', 'Route to approval'],
  ] as const) {
    await page.getByRole('button', { name: action }).click()
    await page.locator('dialog[open]').getByRole('button', { name: confirm }).click()
    await page.waitForTimeout(300)
  }
  await page.getByRole('button', { name: 'Approve' }).click()
  await page
    .locator('dialog[open]')
    .getByLabel(/Note to the operator/)
    .fill('Premises meet the requirements.')
  await page.locator('dialog[open]').getByRole('button', { name: 'Approve' }).click()
  await expect(page.locator('main span[data-tone]').first()).toHaveText('Approved')
  await page.locator('section:has(#audit-title)').getByRole('button', { name: 'Show' }).click()
  await expect(page.getByText('Status: Route to Approval → Approved')).toBeVisible()
  await signOut(page)

  // ---- Operator: outcome ----
  await signIn(page, OPERATOR)
  await page.goto(appUrl)
  await expect(page.getByText('Your licence application was approved')).toBeVisible()
  await expect(page.getByText('Premises meet the requirements.')).toBeVisible()
})
