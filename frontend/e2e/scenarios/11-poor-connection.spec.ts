import { expect, test } from '@playwright/test'

import { OPERATOR, seedAwaitingClarification, signIn } from '../helpers.js'

/** US-087: the respond page on a poor connection. Typed input survives the connection dropping, the notice
 * appears within a second, and the answer is saved on reconnect; the first paint stays under 2.5 s on a
 * throttled 4G profile (the number is recorded in TEST_STRATEGY.md). */
test('the respond page keeps an answer while offline and saves it on reconnect', async ({ page, context }) => {
  const app = await seedAwaitingClarification()
  await signIn(page, OPERATOR)
  await page.goto(`${app.url}/clarification`)
  const field = page.getByLabel(/Your answer/).first()
  await field.waitFor()

  await context.setOffline(true)
  await field.fill('Regraded on 23 Sep; photo to follow.')
  await field.blur()
  // the notice within a second, the text kept, no error toast
  await expect(page.getByText('You are offline: answers and files wait here until you reconnect')).toBeVisible({ timeout: 1000 })
  await expect(page.getByText(/You are offline; your answer is kept here/)).toBeVisible()
  await expect(field).toHaveValue('Regraded on 23 Sep; photo to follow.')
  await expect(page.getByText('Could not save your answer')).toHaveCount(0)

  await context.setOffline(false)
  await expect(page.getByText('You are offline: answers and files wait here until you reconnect')).toHaveCount(0)
  await expect(page.getByText('Saved. Sent with the round when you press Send responses.').first()).toBeVisible({ timeout: 5000 })
  // the server has it: a fresh load shows the answer
  await page.reload()
  await expect(page.getByLabel(/Your answer/).first()).toHaveValue('Regraded on 23 Sep; photo to follow.')
})

test('the respond page paints within 2.5 s on a throttled 4G profile', async ({ page, context }) => {
  const app = await seedAwaitingClarification()
  await signIn(page, OPERATOR)
  // Chrome DevTools' "Fast 4G": 4 Mbps down, 3 Mbps up, 20 ms latency, applied to a cold load of the route.
  const cdp = await context.newCDPSession(page)
  await cdp.send('Network.enable')
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 20,
    downloadThroughput: (4 * 1024 * 1024) / 8,
    uploadThroughput: (3 * 1024 * 1024) / 8,
  })
  await page.goto(`${app.url}/clarification`, { waitUntil: 'load' })
  await page
    .getByLabel(/Your answer/)
    .first()
    .waitFor()
  const fcp = await page.evaluate(() => {
    const paint = performance.getEntriesByType('paint').find((e) => e.name === 'first-contentful-paint')
    return paint ? paint.startTime : null
  })
  console.log(`first contentful paint on Fast 4G: ${fcp === null ? 'n/a' : Math.round(fcp)} ms`)
  expect(fcp).not.toBeNull()
  expect(fcp ?? Infinity).toBeLessThan(2500)
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 })
})
