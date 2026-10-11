import type { ClarificationView } from '@/api/clarification'
import type { ScanState } from '@/api/documents'
import { hasLiveCheck } from '@/features/officer/queries'
import { officerView, slotView } from '@/test/fixtures'
import { CHECK_STALE_MS, hasLiveScan, isCheckStale, isScanHeld, isScanLive } from './queries'

describe('isCheckStale', () => {
  it('flags a check older than the ceiling', () => {
    const now = Date.now()
    expect(isCheckStale(new Date(now - 1000).toISOString(), now)).toBe(false)
    expect(isCheckStale(new Date(now - CHECK_STALE_MS - 1).toISOString(), now)).toBe(true)
  })
})

describe('polling while a file is being scanned', () => {
  const now = Date.parse('2026-09-19T10:00:00Z')
  const fresh = new Date(now - 30_000).toISOString()
  const old = new Date(now - CHECK_STALE_MS - 1_000).toISOString()
  const clar = (scan_state: ScanState, uploaded_at: string): ClarificationView =>
    ({ items: [{ responses: [{ attachments: [{ id: 'a', scan_state, uploaded_at }] }] }] }) as unknown as ClarificationView

  it('keeps polling while scanning inside the window, stops when clean, infected, unscanned or stale', () => {
    expect(isScanLive('scanning', fresh, now)).toBe(true)
    for (const s of ['clean', 'infected', null] as const) expect(isScanLive(s, fresh, now)).toBe(false)
    expect(isScanLive('scanning', old, now)).toBe(false)
  })

  it('does the same for operator clarification attachments', () => {
    const t = new Date().toISOString()
    expect(hasLiveScan(clar('scanning', t))).toBe(true)
    expect(hasLiveScan(clar('clean', t))).toBe(false)
    expect(hasLiveScan(clar('infected', t))).toBe(false)
  })

  it('does the same for officer documents and clarification attachments', () => {
    const doc = (scan_state: ScanState, uploaded_at = fresh) => {
      const v = officerView()
      return { ...v, documents: [{ ...v.documents[0]!, scan_state, uploaded_at, verification: null }] }
    }
    expect(hasLiveCheck(doc('scanning'), now)).toBe(true)
    expect(hasLiveCheck(doc('clean'), now)).toBe(false)
    expect(hasLiveCheck(doc('infected'), now)).toBe(false)
    expect(hasLiveCheck(doc('scanning', old), now)).toBe(false)
    const att = (s: ScanState) =>
      ({
        ...doc(null),
        clarification: { items: [{ requests: [{ response: { attachments: [{ scan_state: s, uploaded_at: fresh }] } }] }] },
      }) as unknown as ReturnType<typeof officerView>
    expect(hasLiveCheck(att('scanning'), now)).toBe(true)
    expect(hasLiveCheck(att('clean'), now)).toBe(false)
  })
})

describe('isScanHeld', () => {
  it('holds a blocked or scanning file, not a clean or unscanned one', () => {
    const slot = (scan_state: ScanState) => {
      const s = slotView('floor_plan')
      return { ...s, document: { ...s.document!, scan_state } }
    }
    expect(isScanHeld(slot('infected'))).toBe(true)
    expect(isScanHeld(slot('scanning'))).toBe(true)
    expect(isScanHeld(slot('clean'))).toBe(false)
    expect(isScanHeld(slot(null))).toBe(false)
  })
})
