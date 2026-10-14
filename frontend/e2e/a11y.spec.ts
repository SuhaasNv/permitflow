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
  seedDraft,
  seedPendingResubmission,
  seedResubmitted,
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

// The US-095 and US-096 tests only read what they seed, so they share one application of each kind:
// every seed is four document checks against the demonstration operator's daily quota.
let pendingOnce: ReturnType<typeof seedPendingResubmission> | undefined
let visitOnce: ReturnType<typeof seedVisitConfirmed> | undefined
let resubmittedOnce: ReturnType<typeof seedResubmitted> | undefined
const sharedPending = () => (pendingOnce ??= seedPendingResubmission())
const sharedVisit = () => (visitOnce ??= seedVisitConfirmed())
const sharedResubmitted = () => (resubmittedOnce ??= seedResubmitted())

/** Collects one line per violation so a run reports every screen, not only the first broken one. */
async function violations(page: Page, screen: string): Promise<string[]> {
  // Scan the loaded screen, never a skeleton: under load a page can still be fetching after networkidle,
  // and a skeleton has no h1 (found on 21 Sep when the whole suite ran on one machine). The skeleton may not
  // have mounted yet either, so wait until a heading is on the page and nothing is loading, together
  // (US-095: the officer case flaked 1 run in 3).
  await expect
    .poll(() => page.evaluate(() => Boolean(document.querySelector('h1')) && !document.querySelector('[aria-busy="true"]')), { timeout: 15_000 })
    .toBe(true)
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
  for (const path of ['/', '/login', '/privacy', '/terms', '/cookies', '/releases', '/releases/v0.3.0']) {
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
    `${app.url}/form/operations`,
    `${app.url}/documents`,
    `${app.url}/review`,
    `${app.url}/history`,
    '/releases',
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
  await page.waitForURL(/\/officer\/applications\//)
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
  for (const path of ['/', '/login', '/privacy', '/releases']) {
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

/** Tabs through the page from the skip link and returns every stop the sticky header, the phone tab bar or a
 * sticky submit card hid completely (WCAG 2.4.11 Focus Not Obscured, US-095). */
async function hiddenFocusStops(page: Page, screen: string, presses = 60): Promise<string[]> {
  const hidden: string[] = []
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.locator('main#main').focus()
  for (let i = 0; i < presses; i++) {
    await page.keyboard.press('Tab')
    const stop = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null
      if (!el || el === document.body) return null
      const r = el.getBoundingClientRect()
      const points = [
        [r.left + 2, r.top + 2],
        [r.right - 2, r.top + 2],
        [r.left + 2, r.bottom - 2],
        [r.right - 2, r.bottom - 2],
        [(r.left + r.right) / 2, (r.top + r.bottom) / 2],
      ]
      const covered = points.every(([x, y]) => {
        const hit = document.elementFromPoint(x, y)
        return !hit || (!el.contains(hit) && !hit.contains(el))
      })
      return covered ? (el.getAttribute('aria-label') ?? el.textContent ?? el.tagName).trim().slice(0, 40) : null
    })
    if (stop) hidden.push(`${screen}: "${stop}" hidden after Tab ${i + 1}`)
  }
  return hidden
}

test('no focused control is hidden behind a sticky bar on the checklist or the respond page (US-095)', async ({ page }) => {
  const visit = await sharedVisit()
  const clarification = await seedAwaitingClarification()
  const hidden: string[] = []
  await signIn(page, OFFICER)
  for (const [width, height] of [[390, 844], [820, 1180], [1280, 800]] as const) {
    await page.setViewportSize({ width, height })
    await page.goto(`/officer/applications/${visit.id}/checklist`)
    await page.getByRole('group', { name: 'Result' }).first().waitFor()
    hidden.push(...(await hiddenFocusStops(page, `${width} checklist`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await signOut(page)
  await signIn(page, OPERATOR)
  for (const [width, height] of [[390, 844], [1280, 800]] as const) {
    await page.setViewportSize({ width, height })
    await page.goto(`${clarification.url}/clarification`)
    await page.getByLabel(/Your answer/).first().waitFor()
    hidden.push(...(await hiddenFocusStops(page, `${width} respond page`)))
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  expect(hidden, hidden.join('\n')).toEqual([])
})

/** Paints the focused control and the same control blurred, each with room for its ring, and says whether
 * anything changed. With Windows High Contrast emulated, a ring drawn only with box-shadow or a border colour
 * is stripped by the browser, so identical pictures mean a keyboard user cannot see where they are (US-096). */
async function focusIsPainted(page: Page, control: ReturnType<Page['locator']>, label: string): Promise<string[]> {
  await control.scrollIntoViewIfNeeded()
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur())
  const box = await control.boundingBox()
  if (!box) return [`${label}: not on screen`]
  const clip = { x: Math.max(0, box.x - 8), y: Math.max(0, box.y - 8), width: box.width + 16, height: box.height + 16 }
  const blurred = await page.screenshot({ clip })
  await page.keyboard.press('Shift')
  await control.focus()
  const focused = await page.screenshot({ clip })
  return blurred.equals(focused) ? [`${label}: focus is not painted in forced-colours mode`] : []
}

test('keyboard focus stays visible in Windows High Contrast on inputs, checkboxes, result buttons and search (US-096)', async ({ page }) => {
  await page.emulateMedia({ forcedColors: 'active', reducedMotion: 'reduce' })
  const app = await sharedPending()
  const visit = await sharedVisit()
  const missing: string[] = []
  await signIn(page, OPERATOR)
  await page.goto(`${app.url}/form/premises`)
  await page.locator('[name="address_line_1"]').waitFor()
  missing.push(...(await focusIsPainted(page, page.locator('[name="address_line_1"]'), 'text input')))
  await signOut(page)
  await signIn(page, OFFICER)
  await page.goto('/officer/queue')
  await page.getByRole('searchbox').waitFor()
  missing.push(...(await focusIsPainted(page, page.getByRole('searchbox'), 'search box')))
  await page.goto(`/officer/applications/${visit.id}/checklist`)
  const first = page.getByRole('group', { name: 'Result' }).first()
  await first.waitFor()
  missing.push(...(await focusIsPainted(page, first.getByRole('button', { name: 'Satisfactory', exact: true }), 'result button')))
  missing.push(...(await focusIsPainted(page, page.getByLabel('Need further clarification').first(), 'checkbox')))
  expect(missing, missing.join('\n')).toEqual([])
})

test('a control that shows text is named with that text, so voice control can say what it sees (US-096, WCAG 2.5.3)', async ({ page }) => {
  const app = await sharedPending()
  const mismatched: string[] = []
  const scan = (screen: string) =>
    page.evaluate((screen) => {
      const squash = (s: string) => s.replace(/\s+/g, '').toLowerCase()
      const out: string[] = []
      for (const el of document.querySelectorAll<HTMLElement>('a[href], button, [role="button"]')) {
        const label = el.getAttribute('aria-label')
        if (!label || el.getClientRects().length === 0) continue
        // each visible line of letters (a line of digits or a symbol is an index or a badge, checked in unit tests)
        for (const line of el.innerText.split('\n').map((l) => l.trim()).filter((l) => (l.match(/[a-z]/gi) ?? []).length >= 3)) {
          if (!squash(label).includes(squash(line))) out.push(`${screen}: "${label}" does not contain its visible text "${line}"`)
        }
      }
      return out
    }, screen)
  for (const path of ['/', '/login']) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    mismatched.push(...(await scan(path)))
  }
  await signIn(page, OPERATOR)
  for (const path of ['/app/dashboard', `${app.url}/form/premises`]) {
    await page.goto(path)
    await page.waitForLoadState('networkidle')
    mismatched.push(...(await scan(path.replace(app.id, ':id'))))
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/app/dashboard')
  await page.waitForLoadState('networkidle')
  mismatched.push(...(await scan('390 /app/dashboard')))
  expect([...new Set(mismatched)], [...new Set(mismatched)].join('\n')).toEqual([])
})

test('nothing is cut off or overlaps at 200% text size: the rail, the application cards and the form buttons (US-096, WCAG 1.4.4)', async ({ page }) => {
  const app = await sharedPending()
  const problems: string[] = []
  await signIn(page, OPERATOR)
  const measure = (screen: string, checkScroll: boolean) =>
    page.evaluate(([screen, checkScroll]) => {
      const out: string[] = []
      for (const el of document.querySelectorAll<HTMLElement>('nav[aria-label="Main"] a span.truncate, main button, main nav .truncate, main aside .truncate')) {
        if (el.getClientRects().length === 0 || el.closest('.sr-only')) continue
        if (el.scrollWidth > el.clientWidth + 1) out.push(`${screen}: "${el.textContent?.trim().slice(0, 30)}" is cut off`)
      }
      // Sideways scrolling is judged where it is a fair test: 200% text on a desktop, and the 320 px reflow width.
      // A phone with every rem-based size doubled is stricter than any real zoom (it behaves like a 195 px screen).
      if (checkScroll && document.documentElement.scrollWidth > document.documentElement.clientWidth + 1) out.push(`${screen}: the page scrolls sideways`)
      for (const card of document.querySelectorAll<HTMLElement>('main a[href^="/app/applications/"]')) {
        const ref = card.querySelector<HTMLElement>('.font-mono')
        const badge = card.querySelector<HTMLElement>('[data-tone]')
        if (!ref || !badge) continue
        const a = ref.getBoundingClientRect(), b = badge.getBoundingClientRect()
        if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) out.push(`${screen}: a status badge covers the reference "${ref.textContent}"`)
      }
      return out
    }, [screen, checkScroll] as const)
  for (const [w, fs] of [[1280, 100], [1280, 200], [390, 100], [390, 200], [320, 100]] as const) {
    await page.setViewportSize({ width: w, height: 900 })
    for (const path of ['/app/dashboard', `${app.url}/form/premises`]) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')
      await page.evaluate((f) => { document.documentElement.style.fontSize = `${(15 * f) / 100}px` }, fs)
      await page.waitForTimeout(250)
      problems.push(...(await measure(`${w}px at ${fs}% ${path.replace(app.id, ':id')}`, fs === 100 || w >= 1280)))
    }
  }
  expect(problems, problems.join('\n')).toEqual([])
})

/** Everything a person can see that spills out of its box on a signed-in screen: a box wider than the viewport,
 * clipped text without an ellipsis, or a child wider than its parent. Elements that scroll on purpose or carry a
 * negative margin (the case sidebar's scrollbar gutter) are left out (US-096). */
const overflowProblems = () => {
  const out: string[] = []
  const iw = document.documentElement.clientWidth
  if (document.documentElement.scrollWidth > iw + 1) out.push(`the page scrolls sideways (${document.documentElement.scrollWidth} > ${iw})`)
  const name = (el: Element) => `${el.tagName.toLowerCase()} "${(el.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 30)}"`
  for (const el of document.querySelectorAll<HTMLElement>('body *')) {
    if (el.getClientRects().length === 0 || el.closest('.sr-only, [hidden], dialog:not([open]), svg, aside.pf-scroll, [aria-live]')) continue
    const cs = getComputedStyle(el)
    const r = el.getBoundingClientRect()
    if (r.width === 0 || r.height === 0 || !(el.textContent ?? '').trim()) continue
    if (cs.overflowX === 'auto' || cs.overflowX === 'scroll' || parseFloat(cs.marginLeft) < 0 || parseFloat(cs.marginRight) < 0) continue
    let scrolled = false
    for (let p = el.parentElement; p; p = p.parentElement) if (getComputedStyle(p).overflowX !== 'visible') { scrolled = true; break }
    if (!scrolled && r.right > iw + 1) out.push(`${name(el)} is beyond the right edge of the screen`)
    if ((cs.overflowX === 'hidden' || cs.overflowX === 'clip') && cs.textOverflow !== 'ellipsis' && el.scrollWidth > el.clientWidth + 1) out.push(`${name(el)} is clipped`)
    const par = el.parentElement
    if (par && getComputedStyle(par).overflowX === 'visible' && cs.position !== 'absolute' && cs.position !== 'fixed') {
      const pr = par.getBoundingClientRect()
      if (pr.width > 0 && (r.right > pr.right + 2 || r.left < pr.left - 2)) out.push(`${name(el)} sticks out of its container by ${Math.round(Math.max(r.right - pr.right, pr.left - r.left))}px`)
    }
  }
  return [...new Set(out)]
}

test('no screen spills out of its box from 320 to 1440 px for any role (US-096)', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  const app = await sharedPending()
  const visit = await sharedVisit()
  const found: string[] = []
  const sweep = async (screen: string, path: string) => {
    for (const w of [320, 390, 768, 1024, 1280, 1440]) {
      await page.setViewportSize({ width: w, height: 900 })
      await page.goto(path)
      await page.waitForLoadState('networkidle')
      await page.locator('[aria-busy="true"]').first().waitFor({ state: 'detached', timeout: 15_000 }).catch(() => undefined)
      await page.waitForTimeout(250)
      for (const p of await page.evaluate(overflowProblems)) found.push(`${screen} at ${w}px: ${p}`)
    }
  }
  await signIn(page, OPERATOR)
  for (const [s, p] of [['dashboard', '/app/dashboard'], ['applications', '/app/applications'], ['application', app.url], ['form', `${app.url}/form/premises`], ['documents', `${app.url}/documents`], ['review', `${app.url}/review`], ['history', `${app.url}/history`]] as const) await sweep(s, p)
  await page.setViewportSize({ width: 1280, height: 900 })
  await signOut(page)
  await signIn(page, OFFICER)
  for (const [s, p] of [['queue', '/officer/queue'], ['case', `/officer/applications/${visit.id}`], ['checklist', `/officer/applications/${visit.id}/checklist`]] as const) await sweep(s, p)
  await page.setViewportSize({ width: 1280, height: 900 })
  await signOut(page)
  await signIn(page, ADMIN)
  for (const [s, p] of [['overview', '/admin/overview'], ['activity', '/admin/activity'], ['users', '/admin/users']] as const) await sweep(s, p)
  expect(found, found.join('\n')).toEqual([])
})

test("a resubmitted case's compare view is a table with no axe violations, for the officer at 1280 and 390 and the administrator (WCAG 1.3.1)", async ({ page }) => {
  const app = await sharedResubmitted()
  const found: string[] = []
  const compare = async (screen: string, path: string) => {
    await page.goto(path)
    const table = page.getByRole('table', { name: /^Fields changed in / }).first()
    await table.waitFor()
    // Column headers name the two revisions, the field heads its row, and no definition list is left over.
    await expect(table.getByRole('columnheader')).toHaveText(['Field', 'Revision 1', 'Revision 2'])
    await expect(table.getByRole('rowheader').first()).toBeVisible()
    expect(await table.locator('dl, dt, dd').count()).toBe(0)
    await page.waitForLoadState('networkidle')
    found.push(...(await violations(page, screen)))
  }
  await signIn(page, OFFICER)
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 844 })
    await compare(`${width} officer compare view`, `/officer/applications/${app.id}`)
  }
  await page.setViewportSize({ width: 1280, height: 844 })
  await signOut(page)
  await signIn(page, ADMIN)
  await compare('1280 admin read-only compare view', `/admin/applications/${app.id}`)
  await signOut(page)
  expectNone(found)
})

test('the hours toggles, quick links and checkbox show the 2px focus outline, not the faint halo (WCAG 2.4.7, 1.4.11)', async ({ page }) => {
  const app = await seedDraft()
  await signIn(page, OPERATOR)
  await page.goto(`${app.url}/form/operations`)
  await page.getByRole('group', { name: 'Open on' }).waitFor()
  const weak: string[] = []
  for (const [label, control] of [
    ['day toggle', page.getByRole('button', { name: 'Mon', exact: true })],
    ['quick link', page.getByRole('button', { name: 'Mon to Fri', exact: true })],
    ['Open 24 hours', page.getByRole('checkbox', { name: 'Open 24 hours' })],
  ] as const) {
    // Arrive by keyboard (away and back), so the browser treats the focus as :focus-visible.
    await control.focus()
    await page.keyboard.press('Shift+Tab')
    await page.keyboard.press('Tab')
    await expect(control).toBeFocused()
    // The outline may still be easing in (the global transition), so wait for it to reach full width.
    await expect
      .poll(() => control.evaluate((el) => parseFloat(getComputedStyle(el).outlineWidth)), { message: `${label}: no 2px outline on focus` })
      .toBeGreaterThanOrEqual(2)
    const paint = await control.evaluate((el) => {
      const cs = getComputedStyle(el)
      return { width: parseFloat(cs.outlineWidth), style: cs.outlineStyle, color: cs.outlineColor, shadow: cs.boxShadow }
    })
    if (paint.style === 'none' || paint.width < 2) weak.push(`${label}: outline is ${paint.style} ${paint.width}px`)
    if (paint.color !== 'rgb(23, 92, 211)') weak.push(`${label}: outline colour is ${paint.color}`)
    if (paint.shadow.includes('rgba(23, 92, 211, 0.2)')) weak.push(`${label}: the faint halo is back (${paint.shadow})`)
  }
  // Every day pressed shows seven check marks; at 320 px none of them may spill out of its box or off the page.
  await page.setViewportSize({ width: 320, height: 800 })
  await page.getByRole('button', { name: 'Every day', exact: true }).click()
  const spill = await page.getByRole('group', { name: 'Open on' }).getByRole('button').evaluateAll((buttons) =>
    buttons.filter((b) => b.scrollWidth > b.clientWidth + 1).map((b) => `${b.textContent}: ${b.scrollWidth} > ${b.clientWidth}`),
  )
  if (spill.length) weak.push(`pressed days spill out of their boxes at 320 px: ${spill.join(', ')}`)
  const page320 = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)
  if (page320) weak.push('the hours picker makes the page scroll sideways at 320 px')
  expect(weak, weak.join('\n')).toEqual([])
})

test('focus follows the action: into the feedback box, back to Add feedback, and a failed sign-in keeps the button (WCAG 2.4.3)', async ({ page }) => {
  const app = await seedUnderReview()
  await signIn(page, OFFICER)
  await openCase(page, app.reference)
  const add = page.getByRole('button', { name: 'Add feedback' })
  await add.click()
  await expect(page.getByLabel(/Feedback for the operator/)).toBeFocused()
  await page.getByRole('button', { name: 'Cancel' }).first().click()
  await expect(add).toBeFocused()
  await signOut(page)

  await page.goto('/login')
  await page.getByLabel(/Email address/).fill('nobody@permitflow.example.sg')
  await page.getByLabel(/^Password/).fill('not-the-password')
  const signInButton = page.getByRole('button', { name: 'Sign in', exact: true })
  await signInButton.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('alert').first()).toBeVisible()
  await expect(signInButton).toBeFocused()
  await expect(signInButton).not.toHaveAttribute('aria-disabled', 'true')
})
