import { describe, expect, it } from 'vitest'

import type { OfficerApplication, OfficerVerification } from '@/api/officer'
import { CHECK_STALE_MS } from '@/features/operator/queries'
import { officerView } from '@/test/fixtures'
import { hasLiveCheck } from './queries'

function withCheck(status: OfficerVerification['status'], requestedAt: string): OfficerApplication {
  const view = officerView()
  const first = view.documents[0]!
  return {
    ...view,
    documents: [{ ...first, verification: { ...first.verification!, status, requested_at: requestedAt, finished_at: null } }],
  }
}

describe('hasLiveCheck', () => {
  const now = Date.parse('2026-09-19T10:00:00Z')

  it('is true for a pending or running check inside the window', () => {
    expect(hasLiveCheck(withCheck('running', new Date(now - 30_000).toISOString()), now)).toBe(true)
    expect(hasLiveCheck(withCheck('pending', new Date(now - 30_000).toISOString()), now)).toBe(true)
  })

  it('is false once the check is older than the window, so the case page stops polling', () => {
    expect(hasLiveCheck(withCheck('running', new Date(now - CHECK_STALE_MS - 1_000).toISOString()), now)).toBe(false)
  })

  it('is false for a finished check', () => {
    expect(hasLiveCheck(withCheck('verified', new Date(now - 30_000).toISOString()), now)).toBe(false)
  })
})
