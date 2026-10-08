/**
 * Mirror of `backend/app/domain/field_rules.py` (US-108). Each rule returns an error message or null.
 * The form definition names the rule a field uses; the examples both sides must agree on are in
 * `backend/tests/fixtures/form_rules.json`.
 */

export const PHONE_MESSAGE = 'Enter a Singapore number: 8 digits starting with 3, 6, 8 or 9, for example +65 9123 4567.'
export const UEN_MESSAGE = 'Enter a valid UEN, for example 202312345K.'
export const EMAIL_MESSAGE = 'Enter a valid email address, for example name@example.com.'
export const POSTAL_FORMAT_MESSAGE = 'Enter the 6-digit postal code, for example 208787.'
export const POSTAL_SECTOR_MESSAGE = 'Postal codes start with 01 to 82. Check the first two digits.'
export const NAME_ALNUM_MESSAGE = 'Include at least one letter or number.'
export const PERSON_CHARS_MESSAGE = "Use letters, spaces and these marks only: ' - . , /"
export const PERSON_LETTER_MESSAGE = 'Include at least one letter.'
export const ADDRESS_PARTS_MESSAGE = 'Include the street name and the house or unit number.'
export const ADDRESS_UNIT_MESSAGE = 'Write the unit as #05-12: a floor of 2 or 3 digits, a dash, a unit of 2 to 5 digits.'
export const ADDRESS_POSTAL_MESSAGE = 'Leave the postal code out of the address; it has its own field.'

export const minLengthMessage = (n: number): string => `Enter at least ${n} characters.`
export const maxLengthMessage = (n: number): string => `Must be ${n} characters or fewer.`
export const decimalsMessage = (n: number): string => `Use at most ${n} decimal places.`

const MIN_POSTAL_SECTOR = 1
const MAX_POSTAL_SECTOR = 82
const EARLIEST_UEN_YEAR = 1800

// ---------- dates (calendar days as YYYY-MM-DD strings or UTC midnights) ----------

export interface CalendarDay {
  year: number
  month: number // 1 to 12
  day: number
}

const pad = (n: number, width = 2): string => String(n).padStart(width, '0')
export const toIso = (d: CalendarDay): string => `${pad(d.year, 4)}-${pad(d.month)}-${pad(d.day)}`

/** Today on the Singapore calendar (UTC+8, no daylight saving), whatever the browser's own time zone. */
export function singaporeToday(now: Date = new Date()): CalendarDay {
  const shifted = new Date(now.getTime() + 8 * 60 * 60 * 1000)
  return { year: shifted.getUTCFullYear(), month: shifted.getUTCMonth() + 1, day: shifted.getUTCDate() }
}

const daysInMonth = (year: number, month: number): number => new Date(Date.UTC(year, month, 0)).getUTCDate()

/** Calendar months ahead; the day is clamped to the end of a shorter month (31 Jan + 1 month = 28 Feb). */
export function addMonths(d: CalendarDay, months: number): CalendarDay {
  const index = d.year * 12 + (d.month - 1) + months
  const year = Math.floor(index / 12)
  const month = (index % 12) + 1
  return { year, month, day: Math.min(d.day, daysInMonth(year, month)) }
}

/** A real calendar date written YYYY-MM-DD, nothing looser (2026-02-31 and 20260131 are both refused). */
export function parseIsoDate(value: string): CalendarDay | null {
  const m = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/.exec(value)
  if (!m) return null
  const year = Number(m[1])
  const month = Number(m[2])
  const day = Number(m[3])
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)) return null
  return { year, month, day }
}

export function checkFutureWindow(
  day: CalendarDay,
  today: CalendarDay,
  minMonthsAhead: number | null | undefined,
  maxYearsAhead: number | null | undefined,
): string | null {
  const iso = toIso(day)
  if (iso <= toIso(today)) return 'Enter a date after today.'
  if (minMonthsAhead != null && iso < toIso(addMonths(today, minMonthsAhead)))
    return `Enter a date at least ${minMonthsAhead} months from today.`
  if (maxYearsAhead != null && iso > toIso(addMonths(today, 12 * maxYearsAhead)))
    return `Enter a date no more than ${maxYearsAhead} years from today.`
  return null
}

// ---------- phone ----------

/** `+65 XXXX XXXX` for a valid Singapore number (optional +65 or 65, spaces, dashes), else null. */
export function normalisePhone(value: string): string | null {
  if (!/^\+?[0-9 -]+$/.test(value)) return null
  const digits = value.replace(/[ -]/g, '')
  let local: string
  if (digits.startsWith('+')) {
    if (!digits.startsWith('+65')) return null
    local = digits.slice(3)
  } else if (digits.length === 10 && digits.startsWith('65')) {
    local = digits.slice(2)
  } else {
    local = digits
  }
  if (!/^[0-9]{8}$/.test(local) || !'3689'.includes(local[0] ?? '')) return null
  return `+65 ${local.slice(0, 4)} ${local.slice(4)}`
}

export const checkPhone = (value: string): string | null => (normalisePhone(value) ? null : PHONE_MESSAGE)

// ---------- UEN ----------

/** The three ACRA formats. `value` is already uppercased and trimmed. */
export function checkUen(value: string, currentYear: number): string | null {
  if (/^[0-9]{8}[A-Z]$/.test(value) || /^[TSR][0-9]{2}[A-Z]{2}[0-9]{4}[A-Z]$/.test(value)) return null
  const m = /^([0-9]{4})[0-9]{5}[A-Z]$/.exec(value)
  if (m && Number(m[1]) >= EARLIEST_UEN_YEAR && Number(m[1]) <= currentYear) return null
  return UEN_MESSAGE
}

// ---------- email ----------

export function checkEmail(value: string): string | null {
  if (value.split('@').length !== 2 || /\s/.test(value) || value.includes('..')) return EMAIL_MESSAGE
  const [local = '', domain = ''] = value.split('@')
  if (!local || local.startsWith('.') || local.endsWith('.')) return EMAIL_MESSAGE
  const labels = domain.split('.')
  const tld = labels[labels.length - 1] ?? ''
  if (labels.length < 2 || labels.some((l) => l === '') || !/^(?:[A-Za-z]{2,}|xn--[A-Za-z0-9-]{2,})$/.test(tld))
    return EMAIL_MESSAGE
  return null
}

// ---------- names ----------

const hasLetter = (value: string): boolean => /\p{L}/u.test(value)

export const checkBusinessName = (value: string): string | null =>
  /[\p{L}\p{N}]/u.test(value) ? null : NAME_ALNUM_MESSAGE

export function checkPersonName(value: string): string | null {
  if (!/^[\p{L}\p{M} '’.,/-]*$/u.test(value)) return PERSON_CHARS_MESSAGE
  return hasLetter(value) ? null : PERSON_LETTER_MESSAGE
}

// ---------- postal code and address ----------

export function checkPostalCode(value: string): string | null {
  if (!/^[0-9]{6}$/.test(value)) return POSTAL_FORMAT_MESSAGE
  const sector = Number(value.slice(0, 2))
  return sector >= MIN_POSTAL_SECTOR && sector <= MAX_POSTAL_SECTOR ? null : POSTAL_SECTOR_MESSAGE
}

export function checkAddress(value: string): string | null {
  if (!/[0-9]/.test(value) || !hasLetter(value)) return ADDRESS_PARTS_MESSAGE
  for (let i = 0; i < value.length; i++) {
    if (value[i] === '#' && !/^#[0-9]{2,3}-[0-9]{2,5}(?![0-9])/.test(value.slice(i))) return ADDRESS_UNIT_MESSAGE
  }
  if (/(?<![0-9])[0-9]{6}(?![0-9])/.test(value)) return ADDRESS_POSTAL_MESSAGE
  return null
}

// ---------- numbers ----------

/**
 * At most `maxDecimals` digits after the point, counted on the number's shortest decimal text exactly as
 * the server does (so 1.0000000000000002 and 1e-7 are too long). No float tolerance.
 */
export function checkDecimals(value: number, maxDecimals: number): string | null {
  const m = /^-?\d+(?:\.(\d+))?(?:e([+-]\d+))?$/i.exec(String(value))
  if (!m) return decimalsMessage(maxDecimals)
  const decimals = (m[1]?.length ?? 0) - Number(m[2] ?? 0)
  return decimals > maxDecimals ? decimalsMessage(maxDecimals) : null
}

/** Rule name from the form definition to its text check. Rules that need more than the text are handled by the caller. */
export const TEXT_RULES: Record<string, (value: string) => string | null> = {
  business_name: checkBusinessName,
  person_name: checkPersonName,
  sg_phone: checkPhone,
  sg_postal: checkPostalCode,
  sg_address: checkAddress,
}
