/**
 * Build Zod validators from the server's form schema so client and server agree (SEC-007).
 * `mode: 'draft'` tolerates missing required values (save and return later); `'complete'` does not.
 *
 * The rules themselves (US-108) live in `fieldRules.ts` and `hours.ts`, mirrors of the backend's
 * `field_rules.py` and `hours.py`; the form definition only names which rule a field uses.
 */

import { z } from 'zod'

import type { FieldDef, SectionDef } from '@/api/formSchema'
import { cleanText, lengthOf } from '@/lib/cleanText'
import {
  checkDecimals,
  checkEmail,
  checkFutureWindow,
  checkUen,
  maxLengthMessage,
  minLengthMessage,
  normalisePhone,
  parseIsoDate,
  singaporeToday,
  TEXT_RULES,
} from '@/lib/fieldRules'
import type { HoursValue } from '@/lib/hours'
import { HOURS_REQUIRED_MESSAGE, hoursFromData, hoursStarted, normaliseHours, validateHours } from '@/lib/hours'

export type FormMode = 'draft' | 'complete'
export type SectionValues = Record<string, string | number | boolean | HoursValue | undefined>

const REQUIRED = 'This field is required.'
const TEXT_KINDS: readonly string[] = ['text', 'textarea', 'email', 'tel']

/** What the server will store for a text value: cleaned, lower-cased email, upper-cased UEN, +65 phone. */
export function normaliseText(f: FieldDef, value: string): string {
  const text = cleanText(value, f.kind === 'textarea')
  if (f.kind === 'email') return text.toLowerCase()
  if (f.rule === 'uen') return text.toUpperCase()
  if (f.rule === 'sg_phone') return normalisePhone(text) ?? text
  return text
}

/** Mirror of the backend's `normalise_value`: used to check what a value becomes. */
export function normaliseValue(f: FieldDef, value: unknown): unknown {
  if (TEXT_KINDS.includes(f.kind) && typeof value === 'string') return normaliseText(f, value)
  if (f.kind === 'hours' && typeof value === 'object' && value !== null && !Array.isArray(value)) {
    return normaliseHours(value as Record<string, unknown>)
  }
  return value
}

/** The error for a cleaned, non-empty text value, in the same order the server checks. */
export function textError(f: FieldDef, text: string, currentYear: number): string | null {
  if (f.min_length != null && lengthOf(text) < f.min_length) return minLengthMessage(f.min_length)
  if (f.max_length !== null && lengthOf(text) > f.max_length) return maxLengthMessage(f.max_length)
  if (f.kind === 'email') return checkEmail(text)
  if (f.rule === 'uen') return checkUen(text, currentYear)
  const check = f.rule ? TEXT_RULES[f.rule] : undefined
  if (check) return check(text)
  if (f.pattern && !new RegExp(f.pattern).test(text)) return f.pattern_message ?? 'Invalid format.'
  return null
}

function fieldSchema(f: FieldDef, mode: FormMode): z.ZodTypeAny {
  const optional = mode === 'draft' || !f.required
  switch (f.kind) {
    case 'checkbox': {
      const base = z.boolean()
      if (f.must_be_true && mode === 'complete') return base.refine((v) => v === true, 'You must confirm this declaration.')
      return base.optional()
    }
    case 'select': {
      const values = f.options.map((o) => o.value)
      const base = z.string().refine((v) => v === '' || values.includes(v), 'Choose one of the options.')
      return optional ? base.optional() : base.refine((v) => v !== '', REQUIRED)
    }
    case 'number':
    case 'integer': {
      let num = z.number({ error: (issue) => (issue.input === undefined ? REQUIRED : 'Must be a number.') })
      if (f.kind === 'integer') num = num.int('Must be a whole number.')
      if (f.min_value !== null) num = num.min(f.min_value, `Must be at least ${f.min_value}.`)
      if (f.max_value !== null) num = num.max(f.max_value, `Must be at most ${f.max_value}.`)
      const decimals = f.max_decimals
      const checked = decimals != null ? num.superRefine((v, ctx) => {
        const message = checkDecimals(v, decimals)
        if (message) ctx.addIssue({ code: 'custom', message })
      }) : num
      return optional ? checked.optional() : checked
    }
    case 'date': {
      const date = z.string({ error: REQUIRED }).superRefine((v, ctx) => {
        if (v === '') {
          if (!optional) ctx.addIssue({ code: 'custom', message: REQUIRED })
          return
        }
        const day = parseIsoDate(v)
        if (!day) {
          ctx.addIssue({ code: 'custom', message: 'Enter a real date as YYYY-MM-DD.' })
          return
        }
        if (f.min_months_ahead == null && f.max_years_ahead == null) return
        const message = checkFutureWindow(day, singaporeToday(), f.min_months_ahead, f.max_years_ahead)
        if (message) ctx.addIssue({ code: 'custom', message })
      })
      return optional ? date.optional() : date
    }
    case 'hours': {
      return z.unknown().superRefine((v, ctx) => {
        const started = typeof v === 'object' && v !== null && !Array.isArray(v) ? hoursStarted(v as HoursValue) : v !== undefined && v !== ''
        if (!started) {
          if (!optional) ctx.addIssue({ code: 'custom', message: HOURS_REQUIRED_MESSAGE })
          return
        }
        const message = validateHours(v)
        if (message) ctx.addIssue({ code: 'custom', message })
      })
    }
    default: {
      const text = z.string({ error: REQUIRED }).superRefine((v, ctx) => {
        const cleaned = normaliseText(f, v)
        if (cleaned === '') {
          if (!optional) ctx.addIssue({ code: 'custom', message: REQUIRED })
          return
        }
        const message = textError(f, cleaned, singaporeToday().year)
        if (message) ctx.addIssue({ code: 'custom', message })
      })
      return optional ? text.optional() : text
    }
  }
}

export function sectionSchema(section: SectionDef, mode: FormMode): z.ZodObject<Record<string, z.ZodTypeAny>> {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const f of section.fields) shape[f.key] = fieldSchema(f, mode)
  return z.object(shape)
}

/** Form defaults from saved data: strings for text-like fields, numbers or undefined, booleans, the hours picker's value. */
export function defaultsFor(section: SectionDef, data: Record<string, unknown>): SectionValues {
  const out: SectionValues = {}
  for (const f of section.fields) {
    const v = data[f.key]
    if (f.kind === 'checkbox') out[f.key] = v === true
    else if (f.kind === 'number' || f.kind === 'integer') out[f.key] = typeof v === 'number' ? v : undefined
    else if (f.kind === 'hours') out[f.key] = hoursFromData(v)
    else out[f.key] = typeof v === 'string' ? v : ''
  }
  return out
}

/** Strip empty strings and undefined so the server sees "missing", not "". */
export function toPayload(values: SectionValues): Record<string, string | number | boolean | HoursValue> {
  const out: Record<string, string | number | boolean | HoursValue> = {}
  for (const [k, v] of Object.entries(values)) {
    if (v === undefined || v === '') continue
    if (typeof v === 'number' && Number.isNaN(v)) continue
    if (typeof v === 'object' && !hoursStarted(v)) continue
    out[k] = v
  }
  return out
}
