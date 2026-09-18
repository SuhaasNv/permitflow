import { CHECK_STALE_MS, isCheckStale } from './queries'

describe('isCheckStale', () => {
  it('flags a check older than the ceiling', () => {
    const now = Date.now()
    expect(isCheckStale(new Date(now - 1000).toISOString(), now)).toBe(false)
    expect(isCheckStale(new Date(now - CHECK_STALE_MS - 1).toISOString(), now)).toBe(true)
  })
})
