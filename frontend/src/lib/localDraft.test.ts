import { clearAllLocalDrafts, clearLocalDraft, readLocalDraft, writeLocalDraft } from './localDraft'

describe('device copy of unsaved entries (UAT run 5, F11, F13)', () => {
  it('writes, reads back and clears one copy', () => {
    writeLocalDraft('clarification.a1.i1.1', 'Regraded on 25 Sep.')
    expect(readLocalDraft<string>('clarification.a1.i1.1')).toBe('Regraded on 25 Sep.')
    clearLocalDraft('clarification.a1.i1.1')
    expect(readLocalDraft<string>('clarification.a1.i1.1')).toBeNull()
  })

  it('drops a copy older than a week and ignores anything malformed', () => {
    localStorage.setItem('permitflow.unsaved.old', JSON.stringify({ savedAt: Date.now() - 8 * 86_400_000, value: 'stale' }))
    expect(readLocalDraft<string>('old')).toBeNull()
    expect(localStorage.getItem('permitflow.unsaved.old')).toBeNull()
    localStorage.setItem('permitflow.unsaved.bad', '{not json')
    expect(readLocalDraft<string>('bad')).toBeNull()
  })

  it('the user sign-out clears every copy and nothing else', () => {
    writeLocalDraft('checklist.a1.1', { findings: {}, touched: ['x'] })
    writeLocalDraft('clarification.a1.i1.1', 'text')
    localStorage.setItem('permitflow.nav.collapsed', '1')
    clearAllLocalDrafts()
    expect(readLocalDraft('checklist.a1.1')).toBeNull()
    expect(readLocalDraft('clarification.a1.i1.1')).toBeNull()
    expect(localStorage.getItem('permitflow.nav.collapsed')).toBe('1')
  })
})
