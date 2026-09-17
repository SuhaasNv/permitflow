import { formatBytes, formatDate, formatDateTime, formatRelative, greeting } from './format'

describe('format', () => {
  it('formats dates with three-letter months', () => {
    expect(formatDate('2026-09-17T10:31:00')).toBe('17 Sep 2026')
    expect(formatDateTime('2026-09-17T10:31:00')).toBe('17 Sep, 10:31')
  })
  it('formats bytes', () => {
    expect(formatBytes(412 * 1024)).toBe('412 KB')
    expect(formatBytes(2.1 * 1024 * 1024)).toBe('2.1 MB')
  })
  it('formats relative time and falls back to the date after a week', () => {
    const now = new Date('2026-09-18T10:00:00').getTime()
    expect(formatRelative('2026-09-18T09:59:40', now)).toBe('just now')
    expect(formatRelative('2026-09-18T09:35:00', now)).toBe('25 min ago')
    expect(formatRelative('2026-09-18T07:00:00', now)).toBe('3 h ago')
    expect(formatRelative('2026-09-16T10:00:00', now)).toBe('2 d ago')
    expect(formatRelative('2026-09-01T10:00:00', now)).toBe('1 Sep 2026')
  })
  it('greets by time of day', () => {
    expect(greeting(8)).toBe('Good morning')
    expect(greeting(14)).toBe('Good afternoon')
    expect(greeting(20)).toBe('Good evening')
  })
})
