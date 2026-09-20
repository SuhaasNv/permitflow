import { AxeBuilder } from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

import {
  ADMIN,
  OFFICER,
  OPERATOR,
  openCase,
  seedPendingResubmission,
  seedUnderReview,
  seedVisitConfirmed,
  seedVisitProposed,
  signIn,
  signOut,
} from './helpers.js'

/**
 * Accessibility gate (US-057): axe-core (WCAG 2.0/2.1/2.2 A and AA rules) on every screen a person can
 * reach, public and signed in, plus a keyboard walk of the sign-in form. Any violation fails the run
 * and is printed with its target selector, so the fix is one grep away.
 */
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']

/** Collects one line per violation so a run reports every screen, not only the first broken one. */
async function violations(page: Page, screen: string): Promise<string[]> {
  const results = await new AxeBuilder({ page }).withTags(TAGS).analyze()
  return results.violations.map(
    (v) =>
      `${screen}: [${v.impact}] ${v.id} (${v.help}) at ${v.nodes
        .slice(0, 4)
        .map((n) => n.target.join(' '))
        .join(' | ')}${v.nodes.length > 4 ? ` and ${v.nodes.length - 4} more` : ''}`,
  )
}

// Page-enter fades would put every element mid-transition under the contrast rule; measure the resting state.
test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
})

function expectNone(lines: string[]) {
  expect(lines, lines.join('\n')).toEqual([])
}

test('public screens have no axe violations', async ({ page }) => {
  const found: string[] = []
  for (const path of ['/', '/login', '/privacy', '/terms', '/cookies']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, path)))
  }
  expectNone(found)
})

test('the sign-in form works from the keyboard alone, and the skip link reaches the content', async ({ page }) => {
  await page.goto('/')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page.locator('main#main')).toBeFocused()

  await page.goto('/login')
  await page.getByLabel('Email').focus()
  await page.keyboard.type(OPERATOR)
  await page.keyboard.press('Tab')
  await page.keyboard.type(process.env.SEED_PASSWORD ?? 'PermitFlow!2026')
  await page.keyboard.press('Enter')
  // A session left live by an earlier run (US-093): the take-over is reachable by keyboard as well.
  const takeOver = page.getByRole('button', { name: 'Sign out the other device and continue' })
  await expect(takeOver.or(page.getByRole('button', { name: 'Sign out', exact: true }))).toBeVisible()
  if (await takeOver.isVisible()) {
    await takeOver.focus()
    await page.keyboard.press('Enter')
  }
  await expect(page).toHaveURL(/\/app\/dashboard/)
  await signOut(page)
})

test('operator screens have no axe violations', async ({ page }) => {
  const app = await seedPendingResubmission()
  const found: string[] = []
  await signIn(page, OPERATOR)
  for (const path of [
    '/app/dashboard',
    '/app/applications',
    app.url,
    `${app.url}/form/premises`,
    `${app.url}/documents`,
    `${app.url}/review`,
    `${app.url}/history`,
  ]) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, path)))
  }
  expectNone(found)
  await signOut(page)
})

test('officer screens have no axe violations', async ({ page }) => {
  const app = await seedUnderReview()
  await signIn(page, OFFICER)
  const found: string[] = []
  await page.goto('/officer/queue')
  await page.waitForLoadState('networkidle')
  found.push(...(await violations(page, '/officer/queue')))
  await openCase(page, app.reference)
  await page.waitForLoadState('networkidle')
  found.push(...(await violations(page, 'officer case')))
  await page.getByRole('button', { name: 'Add feedback' }).click()
  found.push(...(await violations(page, 'officer case, feedback composer open')))
  await page.getByRole('button', { name: 'Cancel' }).first().click()
  await page.getByRole('button', { name: 'Reject' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  found.push(...(await violations(page, 'officer case, confirmation dialog open')))
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expectNone(found)
  await signOut(page)
})

test('phone width (390) keeps the same standard, tap targets included', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const app = await seedPendingResubmission()
  const found: string[] = []
  for (const path of ['/', '/login', '/privacy']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `390 ${path}`)))
  }
  await signIn(page, OPERATOR)
  for (const path of ['/app/dashboard', app.url, `${app.url}/form/premises`, `${app.url}/documents`]) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `390 ${path}`)))
  }
  expectNone(found)
})

test('site visit screens (US-084) have no axe violations at 1280 and 390', async ({ page }) => {
  const app = await seedVisitProposed()
  const found: string[] = []
  await signIn(page, OPERATOR)
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto(app.url)
    await page.locator('section[aria-labelledby="visit-title"]').waitFor()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} operator visit card`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await signOut(page)
  await signIn(page, OFFICER)
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto(`/officer/applications/${app.id}`)
    await page.locator('section[aria-labelledby="visit-title"]').waitFor()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} officer visit panel`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await page.getByRole('button', { name: 'Confirm without a reply' }).waitFor()
  expectNone(found)
})

test('the checklist (US-060) has no axe violations at 1024, 820 and 390', async ({ page }) => {
  const app = await seedVisitConfirmed()
  const found: string[] = []
  await signIn(page, OFFICER)
  for (const [width, height] of [
    [1024, 820],
    [820, 1180],
    [390, 844],
  ] as const) {
    await page.setViewportSize({ width, height })
    await page.goto(`/officer/applications/${app.id}/checklist`)
    await page.getByRole('heading', { name: 'Site visit checklist' }).waitFor()
    await page.getByRole('group', { name: 'Result' }).nth(1).getByRole('button', { name: 'Unsatisfactory', exact: true }).click()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} checklist`)))
  }
  expectNone(found)
})

test('the admin screens (US-070 to US-073) have no axe violations at 1280 and 390, the read-only case included', async ({ page }) => {
  const app = await seedUnderReview()
  const found: string[] = []
  await signIn(page, ADMIN)
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto('/admin/overview')
    await page.getByRole('list', { name: 'Key numbers' }).waitFor()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} admin overview`)))
    await page.goto('/admin/activity')
    await page.getByRole('button', { name: 'Show older activity' }).or(page.getByText('That is everything.')).waitFor()
    found.push(...(await violations(page, `${width} admin activity`)))
    await page.goto('/admin/users')
    await page.getByRole('button', { name: 'Add an account' }).waitFor()
    await page.locator('li', { hasText: '(you)' }).waitFor()
    found.push(...(await violations(page, `${width} admin users`)))
    await page.getByRole('button', { name: 'Add an account' }).click()
    await page.getByRole('dialog', { name: 'Add an account' }).waitFor()
    found.push(...(await violations(page, `${width} add-account dialog`)))
    await page.keyboard.press('Escape')
    await page.goto(`/admin/applications/${app.id}`)
    await page.getByText('Read-only', { exact: true }).waitFor()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} admin read-only case`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await signOut(page)
  expectNone(found)
})
