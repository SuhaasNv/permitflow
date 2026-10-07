import { formatBytes, formatDate, formatDateTime, formatRelative, greeting, inSingapore, todayInSingapore } from './format'

describe('format (Singapore time, NFR-016)', () => {
  it('renders instants in Singapore whatever the browser zone', () => {
    // 02:31 UTC is 10:31 in Singapore
    expect(formatDateTime('2026-09-17T02:31:00Z')).toBe('17 Sep, 10:31')
    expect(formatDate('2026-09-17T02:31:00Z')).toBe('17 Sep 2026')
    // 16:00 UTC is already the next day in Singapore
    expect(formatDateTime('2026-09-17T16:00:00Z')).toBe('18 Sep, 00:00')
    expect(formatDate('2026-09-17T16:00:00Z')).toBe('18 Sep 2026')
    expect(formatDateTime('2026-09-17T15:59:00Z')).toBe('17 Sep, 23:59')
    expect(inSingapore(new Date('2026-09-17T15:59:00Z'))).toEqual({ year: 2026, month: 9, day: 17, hour: 23, minute: 59 })
  })
  it('keeps a date-only value as the calendar date it names', () => {
    expect(formatDate('2026-09-19')).toBe('19 Sep 2026')
    expect(formatDate('2027-09-18')).toBe('18 Sep 2027')
    expect(todayInSingapore(new Date('2026-09-21T15:59:00Z'))).toBe('2026-09-21')
    expect(todayInSingapore(new Date('2026-09-21T16:00:00Z'))).toBe('2026-09-22')
  })
  it('formats bytes', () => {
    expect(formatBytes(412 * 1024)).toBe('412 KB')
    expect(formatBytes(2.1 * 1024 * 1024)).toBe('2.1 MB')
  })
  it('formats relative time and falls back to the Singapore date after a week', () => {
    const now = new Date('2026-09-18T02:00:00Z').getTime()
    expect(formatRelative('2026-09-18T01:59:40Z', now)).toBe('just now')
    expect(formatRelative('2026-09-18T01:35:00Z', now)).toBe('25 min ago')
    expect(formatRelative('2026-09-17T23:00:00Z', now)).toBe('3 h ago')
    expect(formatRelative('2026-09-16T02:00:00Z', now)).toBe('2 d ago')
    expect(formatRelative('2026-09-01T02:00:00Z', now)).toBe('1 Sep 2026')
  })
  it('greets by the Singapore hour', () => {
    expect(greeting(8)).toBe('Good morning')
    expect(greeting(14)).toBe('Good afternoon')
    expect(greeting(20)).toBe('Good evening')
  })
})
