import { formatBytes, formatDate, formatDateTime } from './format'

describe('format', () => {
  it('formats dates with three-letter months', () => {
    expect(formatDate('2026-09-17T10:31:00')).toBe('17 Sep 2026')
    expect(formatDateTime('2026-09-17T10:31:00')).toBe('17 Sep, 10:31')
  })
  it('formats bytes', () => {
    expect(formatBytes(412 * 1024)).toBe('412 KB')
    expect(formatBytes(2.1 * 1024 * 1024)).toBe('2.1 MB')
  })
})
