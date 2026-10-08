/**
 * The form rules (US-108) held to the backend's own table: `backend/tests/fixtures/form_rules.json` is read by
 * `backend/tests/unit/test_form_rules.py` too, so the server and the client cannot drift apart. The form
 * definition used here is the one stored in that file (GET /form-schema as the server serves it).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { FieldDef, FormSchema } from '@/api/formSchema'
import raw from 'virtual:form-rules-fixture'
import { cleanText } from './cleanText'
import { addMonths, checkDecimals, normalisePhone, parseIsoDate, singaporeToday, toIso } from './fieldRules'
import { summariseHours, timeOptions, validateHours } from './hours'
import { normaliseValue, sectionSchema } from './zodFromSchema'

interface RuleCase {
  section: string
  field: string
  value: unknown
  valid: boolean
  stored?: unknown
  message?: string
  today?: string
}

interface Fixture {
  today: string
  schema: FormSchema
  cases: RuleCase[]
  summaries: { value: unknown; text: string }[]
  cleaning: { input: string; multiline: boolean; output: string }[]
}

const fixture = JSON.parse(raw) as Fixture

function fieldDef(section: string, key: string): FieldDef {
  const f = fixture.schema.sections.find((s) => s.key === section)?.fields.find((x) => x.key === key)
  if (!f) throw new Error(`${section}.${key} is not in the fixture schema`)
  return f
}

/** What the draft validator says about one field, given only that field. */
function messageFor(c: RuleCase): string | undefined {
  const def = fixture.schema.sections.find((s) => s.key === c.section)
  if (!def) throw new Error(c.section)
  const result = sectionSchema(def, 'draft').safeParse({ [c.field]: c.value })
  return result.success ? undefined : result.error.issues.find((i) => i.path[0] === c.field)?.message
}

describe('shared rule table', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] })
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it.each(fixture.cases.map((c) => [`${c.field}: ${JSON.stringify(c.value)?.slice(0, 50)} ${c.today ?? ''}`, c] as const))(
    '%s',
    (_name, c) => {
      vi.setSystemTime(new Date(`${c.today ?? fixture.today}T12:00:00+08:00`))
      const message = messageFor(c)
      if (c.valid) {
        expect(message).toBeUndefined()
        expect(normaliseValue(fieldDef(c.section, c.field), c.value)).toEqual(c.stored)
      } else {
        expect(message).toBe(c.message)
      }
    },
  )
})

describe('cleaning and summaries', () => {
  it.each(fixture.cleaning.map((c) => [JSON.stringify(c.input), c] as const))('cleanText %s', (_name, c) => {
    expect(cleanText(c.input, c.multiline)).toBe(c.output)
  })

  it.each(fixture.summaries.map((c) => [c.text || 'unreadable', c] as const))('summary: %s', (_name, c) => {
    expect(summariseHours(c.value)).toBe(c.text)
  })
})

describe('building blocks', () => {
  it('reads Singapore time whatever the browser clock says', () => {
    // 17:00 UTC on the 7th is already 01:00 on the 8th in Singapore
    expect(toIso(singaporeToday(new Date('2026-10-07T17:00:00Z')))).toBe('2026-10-08')
    expect(toIso(singaporeToday(new Date('2026-10-07T15:59:00Z')))).toBe('2026-10-07')
  })

  it('adds calendar months and clamps to the end of a shorter month', () => {
    expect(toIso(addMonths({ year: 2026, month: 1, day: 31 }, 1))).toBe('2026-02-28')
    expect(toIso(addMonths({ year: 2028, month: 2, day: 29 }, 12))).toBe('2029-02-28')
    expect(toIso(addMonths({ year: 2026, month: 11, day: 30 }, 3))).toBe('2027-02-28')
    expect(toIso(addMonths({ year: 2026, month: 10, day: 8 }, 360))).toBe('2056-10-08')
  })

  it('refuses dates that do not exist or are written loosely', () => {
    expect(parseIsoDate('2026-02-31')).toBeNull()
    expect(parseIsoDate('2028-02-29')).toEqual({ year: 2028, month: 2, day: 29 })
    expect(parseIsoDate('20260131')).toBeNull()
    expect(parseIsoDate('2026-1-31')).toBeNull()
  })

  it('normalises phone numbers to +65 XXXX XXXX', () => {
    expect(normalisePhone('9123-4567')).toBe('+65 9123 4567')
    expect(normalisePhone('+65 1234 5678')).toBeNull()
  })

  it('counts decimals without float noise', () => {
    expect(checkDecimals(0.07, 2)).toBeNull()
    expect(checkDecimals(48.25, 2)).toBeNull()
    expect(checkDecimals(1.005, 2)).not.toBeNull()
  })

  it('counts decimals the way the server does, with no float tolerance', () => {
    expect(checkDecimals(1.0000000000000002, 2)).not.toBeNull()
    expect(checkDecimals(48.000000001, 2)).not.toBeNull()
    expect(checkDecimals(1e-7, 2)).not.toBeNull()
    expect(checkDecimals(1.5e-7, 2)).not.toBeNull()
    expect(checkDecimals(1e21, 2)).toBeNull()
    expect(checkDecimals(48, 2)).toBeNull()
    expect(checkDecimals(-0.5, 2)).toBeNull()
  })

  it('lists 48 half-hour times', () => {
    const times = timeOptions()
    expect(times).toHaveLength(48)
    expect([times[0], times[1], times[47]]).toEqual(['00:00', '00:30', '23:30'])
  })

  it('accepts a legacy string only when reading a submitted record', () => {
    expect(validateHours('Mon-Sun 7am-9pm')).toBe('Pick your opening days and hours.')
    expect(validateHours('Mon-Sun 7am-9pm', true)).toBeNull()
  })
})
