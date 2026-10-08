import type { FieldDef } from '@/api/formSchema'
import { displayValue } from './SectionSummary'

const hours: FieldDef = {
  key: 'operating_hours',
  label: 'Operating hours',
  kind: 'hours',
  required: true,
  max_length: null,
  pattern: null,
  pattern_message: null,
  options: [],
  min_value: null,
  max_value: null,
  help: null,
  must_be_true: false,
}

describe('displayValue for operating hours (US-108)', () => {
  it('reads the picked hours as words, never as an object', () => {
    const value = { days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'], opens: '07:00', closes: '21:00', open_24h: false }
    expect(displayValue(hours, value)).toBe('Mon to Sat, 07:00 to 21:00')
    expect(displayValue(hours, { days: ['mon', 'wed', 'fri'], opens: null, closes: null, open_24h: true })).toBe(
      'Mon, Wed, Fri, open 24 hours',
    )
    expect(displayValue(hours, { days: ['fri', 'sat'], opens: '18:00', closes: '02:00', open_24h: false })).toBe(
      'Fri, Sat, 18:00 to 02:00 (next day)',
    )
  })

  it('shows an older free-text entry exactly as it was written', () => {
    expect(displayValue(hours, 'Mon-Sun 7am-9pm')).toBe('Mon-Sun 7am-9pm')
  })

  it('says "Not entered" for nothing, and for a value it cannot read', () => {
    expect(displayValue(hours, undefined)).toBe('Not entered')
    expect(displayValue(hours, { days: [], opens: null, closes: null, open_24h: false })).toBe('Not entered')
  })
})
