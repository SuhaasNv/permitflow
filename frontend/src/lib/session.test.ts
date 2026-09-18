import { describe, expect, it } from 'vitest'

import { sessionWarning } from './session'

const now = Date.parse('2026-09-20T10:00:00Z')
const at = (minutes: number) => new Date(now + minutes * 60_000).toISOString()

describe('sessionWarning (US-048)', () => {
  it('stays silent while more than 30 minutes remain', () => {
    expect(sessionWarning(at(31), now)).toEqual({ level: 'none' })
    expect(sessionWarning(at(480), now)).toEqual({ level: 'none' })
  })
  it('warns inside 30 minutes with a rounded-up countdown', () => {
    expect(sessionWarning(at(30), now)).toEqual({ level: 'warn', text: 'Session ends in 30 min' })
    expect(sessionWarning(at(12.2), now)).toEqual({ level: 'warn', text: 'Session ends in 13 min' })
  })
  it('is urgent inside 5 minutes and honest at the end', () => {
    expect(sessionWarning(at(5), now)).toEqual({ level: 'urgent', text: 'Session ends in 5 min' })
    expect(sessionWarning(at(0.5), now)).toEqual({ level: 'urgent', text: 'Session ends in under a minute' })
    expect(sessionWarning(at(-1), now)).toEqual({ level: 'urgent', text: 'Session ends in under a minute' })
  })
  it('ignores an unparsable timestamp', () => {
    expect(sessionWarning('not a date', now)).toEqual({ level: 'none' })
  })
})
