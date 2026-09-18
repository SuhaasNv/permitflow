import { describe, expect, it } from 'vitest'

import { matchesQuery } from './search'

describe('matchesQuery', () => {
  it('matches everything when the query is blank', () => {
    expect(matchesQuery('', ['PF-2026-0001'])).toBe(true)
    expect(matchesQuery('   ', [null])).toBe(true)
  })
  it('is case-insensitive and ignores null fields', () => {
    expect(matchesQuery('jalan', ['PF-2026-0001', null, '10 Jalan Besar'])).toBe(true)
    expect(matchesQuery('JALAN', [undefined, 'Kopi Corner'])).toBe(false)
  })
  it('requires every word, across any field', () => {
    expect(matchesQuery('kopi besar', ['Kopi Corner', '10 Jalan Besar'])).toBe(true)
    expect(matchesQuery('kopi tampines', ['Kopi Corner', '10 Jalan Besar'])).toBe(false)
  })
})
