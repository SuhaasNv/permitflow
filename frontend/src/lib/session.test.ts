import { describe, expect, it } from 'vitest'

import { IDLE_LIMIT_MS, idleWarning, sessionWarning } from './session'

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

describe('idleWarning (US-095)', () => {
  const idleFor = (minutes: number) => now - minutes * 60_000

  it('stays silent until 55 minutes without a request', () => {
    expect(idleWarning(idleFor(54), now)).toBeNull()
  })

  it('counts down the last 5 minutes, rounded up', () => {
    expect(idleWarning(idleFor(55), now)).toBe('5 min')
    expect(idleWarning(idleFor(57.5), now)).toBe('3 min')
  })

  it('says under a minute at the end and never goes negative', () => {
    expect(idleWarning(idleFor(59.5), now)).toBe('under a minute')
    expect(idleWarning(now - IDLE_LIMIT_MS - 60_000, now)).toBe('under a minute')
  })
})
