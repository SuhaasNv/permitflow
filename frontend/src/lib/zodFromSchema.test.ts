import type { SectionDef } from '@/api/formSchema'
import { defaultsFor, sectionSchema, toPayload } from './zodFromSchema'

const premises: SectionDef = {
  key: 'premises',
  title: 'Premises',
  description: '',
  fields: [
    {
      key: 'address_line_1',
      label: 'Address',
      kind: 'text',
      required: true,
      max_length: 200,
      pattern: null,
      pattern_message: null,
      options: [],
      min_value: null,
      max_value: null,
      help: null,
      must_be_true: false,
    },
    {
      key: 'postal_code',
      label: 'Postal code',
      kind: 'text',
      required: true,
      max_length: null,
      pattern: '^[0-9]{6}$',
      pattern_message: 'Enter the 6-digit postal code.',
      options: [],
      min_value: null,
      max_value: null,
      help: null,
      must_be_true: false,
    },
    {
      key: 'premises_type',
      label: 'Type',
      kind: 'select',
      required: true,
      max_length: null,
      pattern: null,
      pattern_message: null,
      options: [{ value: 'shophouse', label: 'Shophouse' }],
      min_value: null,
      max_value: null,
      help: null,
      must_be_true: false,
    },
    {
      key: 'floor_area_sqm',
      label: 'Area',
      kind: 'number',
      required: true,
      max_length: null,
      pattern: null,
      pattern_message: null,
      options: [],
      min_value: 1,
      max_value: 10000,
      help: null,
      must_be_true: false,
    },
    {
      key: 'tenancy_expiry',
      label: 'Expiry',
      kind: 'date',
      required: true,
      max_length: null,
      pattern: null,
      pattern_message: null,
      options: [],
      min_value: null,
      max_value: null,
      help: null,
      must_be_true: false,
    },
  ],
}

describe('zodFromSchema', () => {
  it('draft mode tolerates missing values but not bad formats', () => {
    const s = sectionSchema(premises, 'draft')
    expect(
      s.safeParse({
        address_line_1: '10 Jalan Besar',
        postal_code: '',
        premises_type: '',
        tenancy_expiry: '',
      }).success,
    ).toBe(true)
    const bad = s.safeParse({ postal_code: '12', floor_area_sqm: 0 })
    expect(bad.success).toBe(false)
    if (!bad.success) expect(bad.error.issues.map((i) => i.path[0]).sort()).toEqual(['floor_area_sqm', 'postal_code'])
  })

  it('complete mode requires every required field', () => {
    const s = sectionSchema(premises, 'complete')
    const r = s.safeParse({
      address_line_1: '',
      postal_code: '208787',
      premises_type: 'shophouse',
      floor_area_sqm: 48,
      tenancy_expiry: '2027-10-31',
    })
    expect(r.success).toBe(false)
    if (!r.success) expect(r.error.issues[0]?.message).toBe('This field is required.')
  })

  it('defaults and payload round-trip', () => {
    const d = defaultsFor(premises, {
      address_line_1: 'x',
      floor_area_sqm: 48,
    })
    expect(d).toEqual({
      address_line_1: 'x',
      postal_code: '',
      premises_type: '',
      floor_area_sqm: 48,
      tenancy_expiry: '',
    })
    expect(toPayload(d)).toEqual({ address_line_1: 'x', floor_area_sqm: 48 })
  })
})
