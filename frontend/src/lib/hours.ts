/**
 * Operating hours (US-108): one set of times shared by every open day. Mirror of
 * `backend/app/domain/hours.py`; both are held to `backend/tests/fixtures/form_rules.json`.
 *
 * The stored value is a `HoursValue`. A submitted revision made before v0.4.1 holds a free-text string
 * instead: `summariseHours` returns it as written.
 */

export const DAYS = [
  { value: 'mon', label: 'Mon' },
  { value: 'tue', label: 'Tue' },
  { value: 'wed', label: 'Wed' },
  { value: 'thu', label: 'Thu' },
  { value: 'fri', label: 'Fri' },
  { value: 'sat', label: 'Sat' },
  { value: 'sun', label: 'Sun' },
] as const

export type DayKey = (typeof DAYS)[number]['value']
const DAY_KEYS: readonly string[] = DAYS.map((d) => d.value)

export interface HoursValue {
  days: DayKey[]
  opens: string | null
  closes: string | null
  open_24h: boolean
}

export const LEGACY_MESSAGE = 'Pick your opening days and hours.'
export const HOURS_REQUIRED_MESSAGE = 'Choose the days you open and the opening and closing time.'
export const NO_DAYS_MESSAGE = 'Choose at least one day you open.'
export const NO_TIMES_MESSAGE = 'Choose an opening and a closing time.'
export const BAD_TIME_MESSAGE = 'Choose a time on the half hour, from 00:00 to 23:30.'
export const SAME_TIME_MESSAGE = 'Opening and closing time cannot be the same.'

export const STEP_MINUTES = 30

export function timeOptions(stepMinutes: number = STEP_MINUTES): string[] {
  const out: string[] = []
  for (let m = 0; m < 24 * 60; m += stepMinutes) out.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`)
  return out
}

const isSlot = (value: unknown): boolean => {
  if (typeof value !== 'string') return false
  const m = /^([01][0-9]|2[0-3]):([0-5][0-9])$/.exec(value)
  return m !== null && Number(m[2]) % STEP_MINUTES === 0
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

/** Days de-duplicated in week order, blank times as null, times dropped when open 24 hours. */
export function normaliseHours(value: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...value }
  const days = value.days
  if (Array.isArray(days) && days.every((d) => typeof d === 'string' && DAY_KEYS.includes(d))) {
    out.days = DAY_KEYS.filter((d) => days.includes(d))
  }
  for (const key of ['opens', 'closes']) {
    const v = out[key]
    out[key] = v === undefined || v === null || (typeof v === 'string' && v.trim() === '') ? null : v
  }
  if (out.open_24h === undefined) out.open_24h = false
  if (out.open_24h === true) {
    out.opens = null
    out.closes = null
  }
  return out
}

/**
 * The error message for an operating-hours value, or null. A free-text string is the pre-v0.4.1 shape:
 * fine when reading a submitted snapshot, an error when an operator edits (they re-pick once).
 */
export function validateHours(raw: unknown, snapshot = false): string | null {
  if (typeof raw === 'string') return snapshot ? null : LEGACY_MESSAGE
  if (!isRecord(raw)) return LEGACY_MESSAGE
  const value = normaliseHours(raw)
  if (!Object.keys(value).every((k) => ['days', 'opens', 'closes', 'open_24h'].includes(k))) return LEGACY_MESSAGE
  const days = value.days
  if (!Array.isArray(days) || !days.every((d) => typeof d === 'string' && DAY_KEYS.includes(d))) return LEGACY_MESSAGE
  if (typeof value.open_24h !== 'boolean') return LEGACY_MESSAGE
  if (days.length === 0) return NO_DAYS_MESSAGE
  if (value.open_24h) return null
  const { opens, closes } = value
  if (opens === null || closes === null) return NO_TIMES_MESSAGE
  if (!isSlot(opens) || !isSlot(closes)) return BAD_TIME_MESSAGE
  if (opens === closes) return SAME_TIME_MESSAGE
  return null
}

function dayPhrase(days: readonly string[]): string {
  if (days.length === DAYS.length) return 'Every day'
  const label = (key: string): string => DAYS.find((d) => d.value === key)?.label ?? key
  const indexes = days.map((d) => DAY_KEYS.indexOf(d))
  const parts: string[] = []
  let i = 0
  while (i < indexes.length) {
    let j = i
    while (j + 1 < indexes.length && indexes[j + 1] === (indexes[j] ?? 0) + 1) j++
    if (j - i >= 2) parts.push(`${label(days[i] ?? '')} to ${label(days[j] ?? '')}`) // three or more in a row read as a range
    else for (let k = i; k <= j; k++) parts.push(label(days[k] ?? ''))
    i = j + 1
  }
  return parts.join(', ')
}

export function closesAfterMidnight(opens: string, closes: string): boolean {
  return closes < opens
}

/**
 * The one place hours become words: "Mon to Sat, 07:00 to 21:00", "Every day, open 24 hours". A legacy
 * free-text string is returned as written; anything unreadable is an empty string.
 */
export function summariseHours(raw: unknown): string {
  if (typeof raw === 'string') return raw
  if (!isRecord(raw) || validateHours(raw) !== null) return ''
  const value = normaliseHours(raw)
  const days = dayPhrase(value.days as string[])
  if (value.open_24h) return `${days}, open 24 hours`
  const opens = String(value.opens)
  const closes = String(value.closes)
  return `${days}, ${opens} to ${closes}${closesAfterMidnight(opens, closes) ? ' (next day)' : ''}`
}

/** A saved value as the picker holds it; a legacy string (or nothing) starts the picker empty. */
export function hoursFromData(raw: unknown): HoursValue | undefined {
  if (!isRecord(raw) || validateHours(raw) === LEGACY_MESSAGE) return undefined
  const v = normaliseHours(raw)
  return {
    days: v.days as DayKey[],
    opens: typeof v.opens === 'string' ? v.opens : null,
    closes: typeof v.closes === 'string' ? v.closes : null,
    open_24h: v.open_24h === true,
  }
}

/** True once the operator has touched the picker at all, so an untouched one is sent as "missing". */
export function hoursStarted(value: HoursValue | undefined): value is HoursValue {
  return value !== undefined && (value.days.length > 0 || value.open_24h || Boolean(value.opens) || Boolean(value.closes))
}
