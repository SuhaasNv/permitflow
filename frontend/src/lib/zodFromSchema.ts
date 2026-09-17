/**
 * Build Zod validators from the server's form schema so client and server agree (SEC-007).
 * `mode: 'draft'` tolerates missing required values (save and return later); `'complete'` does not.
 */

import { z } from 'zod'

import type { FieldDef, SectionDef } from '@/api/formSchema'

export type FormMode = 'draft' | 'complete'
export type SectionValues = Record<string, string | number | boolean | undefined>

const REQUIRED = 'This field is required.'

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
      let num = z.number({ message: 'Must be a number.' })
      if (f.kind === 'integer') num = num.int('Must be a whole number.')
      if (f.min_value !== null) num = num.min(f.min_value, `Must be at least ${f.min_value}.`)
      if (f.max_value !== null) num = num.max(f.max_value, `Must be at most ${f.max_value}.`)
      return optional ? num.optional() : num
    }
    case 'date': {
      const base = z.string().refine((v) => v === '' || /^\d{4}-\d{2}-\d{2}$/.test(v), 'Enter a date as YYYY-MM-DD.')
      return optional ? base.optional() : base.refine((v) => v !== '', REQUIRED)
    }
    default: {
      let str = z.string().trim()
      if (f.max_length !== null) str = str.max(f.max_length, `Must be ${f.max_length} characters or fewer.`)
      const withRules = str.refine(
        (v) => {
          if (v === '') return true
          if (f.kind === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) return false
          if (f.pattern && !new RegExp(f.pattern).test(v)) return false
          return true
        },
        f.kind === 'email' ? 'Enter a valid email address.' : (f.pattern_message ?? 'Invalid format.'),
      )
      return optional ? withRules.optional() : withRules.refine((v) => v !== '', REQUIRED)
    }
  }
}

export function sectionSchema(section: SectionDef, mode: FormMode): z.ZodObject<Record<string, z.ZodTypeAny>> {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const f of section.fields) shape[f.key] = fieldSchema(f, mode)
  return z.object(shape)
}

/** Form defaults from saved data: strings for text-like fields, numbers or undefined, booleans. */
export function defaultsFor(section: SectionDef, data: Record<string, unknown>): SectionValues {
  const out: SectionValues = {}
  for (const f of section.fields) {
    const v = data[f.key]
    if (f.kind === 'checkbox') out[f.key] = v === true
    else if (f.kind === 'number' || f.kind === 'integer') out[f.key] = typeof v === 'number' ? v : undefined
    else out[f.key] = typeof v === 'string' ? v : ''
  }
  return out
}

/** Strip empty strings and undefined so the server sees "missing", not "". */
export function toPayload(values: SectionValues): Record<string, string | number | boolean> {
  const out: Record<string, string | number | boolean> = {}
  for (const [k, v] of Object.entries(values)) {
    if (v === undefined || v === '') continue
    if (typeof v === 'number' && Number.isNaN(v)) continue
    out[k] = v
  }
  return out
}
