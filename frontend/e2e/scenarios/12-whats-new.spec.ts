import { expect, test } from '@playwright/test'

import { ADMIN, OFFICER, OPERATOR, signIn, signOut } from '../helpers.js'

/** What's new (US-094): the version chip opens the page for a visitor and for each role; the reader's own
 * block comes first, the other audiences fold, the administrator sees everything; the "New" mark clears
 * on the first read; the phone keeps the chip in the top strip. */

const chip = (page: import('@playwright/test').Page) => page.getByRole('link', { name: /^Version .*, what's new$/ })

test('signed out: the landing footer chip opens the page with every block open and the build line', async ({ page }) => {
  await page.goto('/')
  await expect(chip(page)).toContainText('New')
  await chip(page).click()
  await expect(page).toHaveURL(/\/releases$/)
  await expect(page.getByRole('heading', { level: 1, name: "What's new" })).toBeVisible()
  await expect(page.getByTestId('build-line')).toContainText(/v\d+\.\d+\.\d+/)
  await expect(page.getByTestId('build-line')).toContainText('development environment')
  await expect(page.getByRole('heading', { level: 3, name: 'New for licensing officers' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 3, name: 'New for operators' })).toBeVisible()
  await expect(page.getByText('Also in this release')).toHaveCount(0)
  await expect(page.getByRole('navigation', { name: 'Releases' }).getByText('This build')).toBeVisible()
  // read once: the chip in this page's footer now says What's new, not New
  await expect(chip(page)).toContainText("What's new")
  // an earlier release from the list
  await page.getByRole('navigation', { name: 'Releases' }).getByRole('link', { name: /v0\.3\.0/ }).click()
  await expect(page).toHaveURL(/\/releases\/v0\.3\.0$/)
  await expect(page.getByRole('heading', { level: 2 })).toContainText('Production')
})

test('operator: own block first, officer and office blocks folded, in the shell', async ({ page }) => {
  await signIn(page, OPERATOR)
  await chip(page).first().click()
  await expect(page).toHaveURL(/\/releases$/)
  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible()
  await expect(page.getByText('For you')).toBeVisible()
  await expect(page.getByRole('heading', { level: 3, name: 'New for operators' })).toBeVisible()
  await expect(page.getByText('Also in this release')).toBeVisible()
  const folded = page.locator('details', { hasText: 'New for licensing officers' })
  await expect(folded).not.toHaveAttribute('open', '')
  await folded.locator('summary').click()
  await expect(folded).toHaveAttribute('open', '')
  await expect(folded.getByText(/Arrange the site visit/)).toBeVisible()
  await expect(page.getByText('For everyone')).toBeVisible()
  await signOut(page)
})

test('officer: own block first, the operator block folded', async ({ page }) => {
  await signIn(page, OFFICER)
  await chip(page).first().click()
  await expect(page.getByText('For you')).toBeVisible()
  await expect(page.getByRole('heading', { level: 3, name: 'New for licensing officers' })).toBeVisible()
  await expect(page.locator('details', { hasText: 'New for operators' })).not.toHaveAttribute('open', '')
  await signOut(page)
})

test('admin: every block open, and the build line', async ({ page }) => {
  await signIn(page, ADMIN)
  // the overview names the build too, with a link to the page
  await expect(page.getByTestId('admin-build-line')).toContainText(/Build.*v\d+\.\d+\.\d+/)
  await expect(page.getByTestId('admin-build-line')).toContainText('development')
  await chip(page).first().click()
  await expect(page.getByText('For you')).toHaveCount(0)
  await expect(page.getByText('Also in this release')).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 3, name: 'New for the licensing office (administrators)' })).toBeVisible()
  await expect(page.getByTestId('build-line')).toContainText('development environment')
  await signOut(page)
})

test('phone: the chip sits in the top strip and opens the page; the release chips scroll', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await signIn(page, OPERATOR)
  const strip = page.getByRole('region', { name: 'Portal notice' })
  await expect(strip.getByRole('link', { name: /what's new/ })).toBeVisible()
  await strip.getByRole('link', { name: /what's new/ }).click()
  await expect(page).toHaveURL(/\/releases$/)
  await expect(page.getByRole('navigation', { name: 'Releases' }).getByRole('link', { name: /v0\.1\.0/ })).toBeVisible()
  await expect(page.getByRole('heading', { level: 3, name: 'New for operators' })).toBeVisible()
  await signOut(page)
})
