/// <reference lib="dom" />
import { AxeBuilder } from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

import {
  ADMIN,
  OFFICER,
  OPERATOR,
  openCase,
  seedAwaitingClarification,
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

/** Every focusable control on the page must offer at least 44 x 44 px, the WCAG 2.2 enhanced target size
 * that the design system promises on the two screens filled on a tablet and a phone (US-088). */
async function smallTargets(page: Page, screen: string, minimum = 44): Promise<string[]> {
  return page.evaluate(
    ({ screen, minimum }) => {
      const out: string[] = []
      const controls = document.querySelectorAll<HTMLElement>(
        'main button, main a[href], main input, main textarea, main select, main [role="button"]',
      )
      for (const el of controls) {
        if (el.closest('[hidden], dialog:not([open])')) continue
        const type = el.getAttribute('type')
        if (type === 'file') continue
        // a checkbox's target is the label that wraps it; a plain link in running text is inline (WCAG 2.5.8)
        if ((type === 'checkbox' || type === 'radio') && el.closest('label')) continue
        if (el.tagName === 'A' && !el.className.includes('inline-flex') && !el.className.includes('pf-btn')) continue
        const r = el.getBoundingClientRect()
        if (r.width === 0 || r.height === 0) continue
        if (r.height < minimum || r.width < minimum) {
          const name = el.getAttribute('aria-label') ?? el.textContent?.trim().slice(0, 40) ?? el.tagName
          out.push(`${screen}: ${el.tagName.toLowerCase()} "${name}" is ${Math.round(r.width)} x ${Math.round(r.height)}`)
        }
      }
      return out
    },
    { screen, minimum },
  )
}

test('the checklist in both states, the respond page and the history have no axe violations at 1280 and 390 (US-088)', async ({ page }) => {
  const app = await seedAwaitingClarification()
  const found: string[] = []
  await signIn(page, OFFICER)
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto(`/officer/applications/${app.id}/checklist`)
    await page.getByText('The findings are final.').waitFor()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} submitted checklist`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await signOut(page)
  await signIn(page, OPERATOR)
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto(`${app.url}/clarification`)
    await page
      .getByLabel(/Your answer/)
      .first()
      .waitFor()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} respond page`)))
    await page.goto(`${app.url}/history`)
    await page
      .getByText(/Round 1/)
      .first()
      .waitFor()
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, `${width} history with visit and clarification rounds`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await signOut(page)
  expectNone(found)
})

test('every control on the checklist and the respond page measures at least 44 px (US-088)', async ({ page }) => {
  const app = await seedAwaitingClarification()
  const small: string[] = []
  await signIn(page, OPERATOR)
  for (const width of [390, 820]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto(`${app.url}/clarification`)
    await page
      .getByLabel(/Your answer/)
      .first()
      .waitFor()
    // answer one item so the file picker row (Choose a file, Remove) is on the page too
    await page
      .getByLabel(/Your answer/)
      .first()
      .fill('Regraded on 23 Sep.')
    await page
      .getByLabel(/Your answer/)
      .first()
      .blur()
    await page.getByRole('button', { name: 'Choose a file' }).first().waitFor()
    small.push(...(await smallTargets(page, `${width} respond page`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await signOut(page)
  const draft = await seedVisitConfirmed()
  await signIn(page, OFFICER)
  for (const width of [390, 820, 1024]) {
    await page.setViewportSize({ width, height: 1180 })
    await page.goto(`/officer/applications/${draft.id}/checklist`)
    await page.getByRole('group', { name: 'Result' }).first().waitFor()
    await page.getByRole('button', { name: 'Add a finding' }).click()
    await page.getByRole('textbox', { name: /^Other finding/ }).waitFor()
    small.push(...(await smallTargets(page, `${width} checklist`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  expect(small, small.join('\n')).toEqual([])
})

test('the checklist works from the keyboard alone (US-088)', async ({ page }) => {
  const app = await seedVisitConfirmed()
  await signIn(page, OFFICER)
  await page.goto(`/officer/applications/${app.id}/checklist`)
  const first = page.getByRole('group', { name: 'Result' }).first()
  await first.waitFor()
  // Tab into the first item's results; Space picks a result; the flag and the comment are the next stops.
  await first.getByRole('button', { name: 'Satisfactory', exact: true }).focus()
  await page.keyboard.press('Space')
  await expect(first.getByRole('button', { name: 'Satisfactory', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await page.keyboard.press('Tab')
  await page.keyboard.press('Enter')
  await expect(first.getByRole('button', { name: 'Unsatisfactory', exact: true })).toHaveAttribute('aria-pressed', 'true')
  // Not applicable is the third result; the flag follows, then the comment.
  await page.keyboard.press('Tab')
  await page.keyboard.press('Tab')
  const flag = page.getByLabel('Need further clarification').first()
  await expect(flag).toBeFocused()
  await page.keyboard.press('Space')
  await expect(flag).toBeChecked()
  await page.keyboard.press('Tab')
  await expect(page.getByLabel(/Comment/).first()).toBeFocused()
  await page.keyboard.type('Reachable by keyboard.')
  await expect(page.getByText('Saved just now')).toBeVisible({ timeout: 5000 })
  await signOut(page)
})
