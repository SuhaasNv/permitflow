import { describe, expect, it } from 'vitest'

import { nextRespondTarget } from './respond'

const keys = ['business', 'premises', 'operations', 'declarations']

describe('nextRespondTarget (US-041)', () => {
  it('skips locked sections and lands on the next flagged one', () => {
    expect(
      nextRespondTarget({ sectionKeys: keys, activeKey: 'business', flaggedSections: ['business', 'operations'], docsFlagged: false }),
    ).toEqual({
      kind: 'section',
      key: 'operations',
    })
  })
  it('goes to documents after the last flagged section when a document was flagged', () => {
    expect(nextRespondTarget({ sectionKeys: keys, activeKey: 'operations', flaggedSections: ['operations'], docsFlagged: true })).toEqual({
      kind: 'documents',
    })
  })
  it('ends at resubmit when nothing flagged is left', () => {
    expect(nextRespondTarget({ sectionKeys: keys, activeKey: 'operations', flaggedSections: ['operations'], docsFlagged: false })).toEqual({
      kind: 'resubmit',
    })
  })
  it('never walks backwards to an earlier flagged section', () => {
    expect(nextRespondTarget({ sectionKeys: keys, activeKey: 'declarations', flaggedSections: ['business'], docsFlagged: false })).toEqual({
      kind: 'resubmit',
    })
  })
})
