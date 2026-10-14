import { AxeBuilder } from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

import { BUSINESS, OPERATIONS, OPERATOR, pickHours, signIn } from '../helpers.js'

const PHONE_MESSAGE = 'Enter a Singapore number: 8 digits starting with 3, 6, 8 or 9, for example +65 9123 4567.'
const UEN_MESSAGE = 'Enter a valid UEN, for example 202312345K.'

/** US-108: Singapore formats are checked as the operator types, values are stored normalised, and the operating
 * hours are picked (days, then times) and read back as one line. */
test('formats are checked while typing, hours are picked and read back', async ({ page }) => {
  await signIn(page, OPERATOR)
  await page.goto('/app/dashboard')
  await page.getByRole('button', { name: 'New application' }).first().click()
  await expect(page).toHaveURL(/\/app\/applications\/[0-9a-f-]+$/)
  const appUrl = new URL(page.url()).pathname

  // ---- phone and UEN: the message appears on the keystroke, not on blur or save ----
  await page.goto(`${appUrl}/form/business`)
  const phone = page.getByLabel(/Contact phone/)
  await expect(phone).toHaveAttribute('inputmode', 'tel')
  await expect(phone).toHaveAttribute('autocomplete', 'tel')
  await phone.pressSequentially('+65 1234')
  await expect(page.getByText(PHONE_MESSAGE)).toBeVisible()
  await phone.fill('9123-4567')
  await expect(page.getByText(PHONE_MESSAGE)).toHaveCount(0)

  const uen = page.getByLabel(/UEN/)
  await uen.pressSequentially('abc')
  await expect(page.getByText(UEN_MESSAGE)).toBeVisible()
  await uen.fill('t08ll0001a')
  await expect(page.getByText(UEN_MESSAGE)).toHaveCount(0)

  // ---- saved normalised: +65 XXXX XXXX and an upper-case UEN ----
  await page.locator('[name="business_name"]').fill('  Scenario   Kopi House  ')
  await page.locator('[name="contact_name"]').fill(BUSINESS.contact_name)
  await page.locator('[name="contact_email"]').fill('WeiLing@Scenario.SG')
  await page.locator('select[name="entity_type"]').selectOption('private_limited')
  await page.getByRole('button', { name: /Save and continue/ }).click()
  await expect(page).toHaveURL(/\/form\/premises$/)
  await page.goto(`${appUrl}/form/business`)
  await expect(page.locator('[name="contact_phone"]')).toHaveValue('+65 9123 4567')
  await expect(page.locator('[name="uen"]')).toHaveValue('T08LL0001A')
  await expect(page.locator('[name="contact_email"]')).toHaveValue('weiling@scenario.sg')
  await expect(page.locator('[name="business_name"]')).toHaveValue('Scenario Kopi House')

  // ---- hours: pick, cross midnight, 24 hours hides the times and unticking brings them back ----
  await page.goto(`${appUrl}/form/operations`)
  await page.locator('[name="cuisine_description"]').fill(OPERATIONS.cuisine_description)
  await page.locator('[name="seating_capacity"]').fill(OPERATIONS.seating_capacity)
  await page.locator('[name="food_handlers_count"]').fill(OPERATIONS.food_handlers_count)
  await pickHours(page, { quick: 'Mon to Fri', opens: '18:00', closes: '02:00' })
  await expect(page.getByText('Closes after midnight, at 02:00 the next day.')).toBeVisible()
  await expect(page.getByText('Mon to Fri, 18:00 to 02:00 (next day)')).toBeVisible()
  await page.getByRole('checkbox', { name: 'Open 24 hours' }).check()
  await expect(page.getByLabel('Opens', { exact: true })).toHaveCount(0)
  await expect(page.getByText('Mon to Fri, open 24 hours')).toBeVisible()
  await page.getByRole('checkbox', { name: 'Open 24 hours' }).uncheck()
  await expect(page.getByLabel('Opens', { exact: true })).toHaveValue('18:00')

  // saving with the same time twice is refused with the picker's own message
  await page.getByLabel('Closes', { exact: true }).selectOption('18:00')
  await page.getByRole('button', { name: /Save and continue/ }).click()
  await expect(page.getByText('Opening and closing time cannot be the same.')).toBeVisible()
  // the picker with its error showing passes the accessibility gate (WCAG 2.2 AA); the error is only just on the
  // page (it waits for the save), so measure its resting colour, as the accessibility gate does
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const axe = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'])
    .analyze()
  expect(axe.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`)).toEqual([])
  await page.getByLabel('Closes', { exact: true }).selectOption('02:00')
  await page.getByRole('button', { name: /Save and continue/ }).click()
  await expect(page).toHaveURL(/\/form\/declarations$/)

  // ---- it comes back as picked, and the review step reads it as words ----
  await page.goto(`${appUrl}/form/operations`)
  await expect(page.getByRole('button', { name: 'Mon', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.getByRole('button', { name: 'Sat', exact: true })).toHaveAttribute('aria-pressed', 'false')
  await expect(page.getByLabel('Closes', { exact: true })).toHaveValue('02:00')
  await page.goto(`${appUrl}/review`)
  await expect(page.getByText('Mon to Fri, 18:00 to 02:00 (next day)')).toBeVisible()

  // ---- phone, tablet and desktop: no horizontal scroll, and a picture to look at ----
  for (const [name, width, height] of [
    ['phone', 375, 812],
    ['tablet', 768, 1024],
    ['desktop', 1280, 900],
  ] as const) {
    await page.setViewportSize({ width, height })
    await page.goto(`${appUrl}/form/operations`)
    await expect(page.getByRole('button', { name: 'Mon', exact: true })).toBeVisible()
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow, `${name} ${width}px scrolls sideways`).toBeLessThanOrEqual(0)
    await page.screenshot({ path: test.info().outputPath(`hours-${name}-${width}.png`), fullPage: true })
  }
})
