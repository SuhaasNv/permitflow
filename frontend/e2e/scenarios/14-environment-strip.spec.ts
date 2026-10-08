import { expect, test } from '@playwright/test'

import { OPERATOR, signIn } from '../helpers.js'

/** Environment strip (US-109): while the API runs outside production (these suites run it as development),
 * a thin amber notice sits above every page, the landing page and the signed-in shell included, and never
 * pushes the page sideways on a phone. */

const strip = (page: import('@playwright/test').Page) => page.getByRole('region', { name: 'Environment notice' })

test('landing page: the strip says this is not the live service', async ({ page }) => {
  await page.goto('/')
  await expect(strip(page)).toBeVisible()
  await expect(strip(page)).toContainText('Development environment: test data only, not the live service')
})

test('signed-in shell: the strip sits above the portal masthead', async ({ page }) => {
  await signIn(page, OPERATOR)
  await page.goto('/app/dashboard')
  await expect(strip(page)).toBeVisible()
  const stripBox = await strip(page).boundingBox()
  const mastheadBox = await page.getByRole('region', { name: 'Portal notice' }).boundingBox()
  expect(stripBox).not.toBeNull()
  expect(mastheadBox).not.toBeNull()
  expect((stripBox?.y ?? 0) + (stripBox?.height ?? 0)).toBeLessThanOrEqual((mastheadBox?.y ?? 0) + 1)
})

test('phone: shorter text on one line, no horizontal scroll at 320 px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 })
  for (const path of ['/', '/login', '/privacy', '/releases', '/no/such/page']) {
    await page.goto(path)
    await expect(strip(page)).toBeVisible()
    // innerText leaves out the part hidden below the sm breakpoint
    expect(await strip(page).innerText()).toBe('Development environment: test data only')
    const box = await strip(page).boundingBox()
    expect(box?.height ?? 99).toBeLessThanOrEqual(29)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
  }
})
