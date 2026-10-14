import type { PlatformSetting, SettingValue } from '@/api/admin'
import { AppError } from '@/api/client'
import { formatDate, inSingapore } from '@/lib/format'

/** US-101: how a setting's value is shown and typed. The server stores bytes; the page speaks megabytes. */
export const BYTES_PER_MB = 1024 * 1024

const isBytes = (s: PlatformSetting): boolean => s.unit === 'bytes'

const capital = (text: string): string => text.charAt(0).toUpperCase() + text.slice(1)

const trimmed = (n: number): string => String(Number(n.toFixed(2)))

/** A value as the page says it: "1,000", "On", "Closed", "10 MB" (bytes become megabytes). No unit otherwise. */
export function formatValue(s: PlatformSetting, value: SettingValue): string {
  if (typeof value === 'boolean') return value ? 'On' : 'Off'
  if (typeof value === 'string') return capital(value)
  if (isBytes(s)) return `${trimmed(value / BYTES_PER_MB)} MB`
  return value.toLocaleString('en-US')
}

/** The unit written after a number ("requests"); a size already carries its MB, and a switch has none. */
export function unitLabel(s: PlatformSetting): string {
  return s.kind === 'int' && !isBytes(s) ? s.unit : ''
}

/** The value and its unit: "180 requests", "10 MB", "Off". */
export function formatWithUnit(s: PlatformSetting, value: SettingValue): string {
  const unit = unitLabel(s)
  return unit ? `${formatValue(s, value)} ${unit}` : formatValue(s, value)
}

/** What the input starts with, in the unit the person types. */
export function inputText(s: PlatformSetting, value: SettingValue): string {
  return typeof value === 'number' && isBytes(s) ? trimmed(value / BYTES_PER_MB) : String(value)
}

/** The unit written inside the input. */
export function inputSuffix(s: PlatformSetting): string {
  return isBytes(s) ? 'MB' : s.unit
}

/** "10 to 240", "1 MB to 10 MB", "On or Off", "Closed or Open". */
export function rangeText(s: PlatformSetting): string {
  if (s.kind === 'bool') return 'On or Off'
  if (s.kind === 'choice') return s.choices.map(capital).join(' or ')
  if (s.minimum === null || s.maximum === null) return ''
  return `${formatValue(s, s.minimum)} to ${formatValue(s, s.maximum)}`
}

/** Where the top of the range comes from, as the row says it. */
export function rangeSource(s: PlatformSetting): string {
  if (s.max_source === 'env') return 'Ceiling set by the environment'
  if (s.max_source === 'cap') return s.key === 'upload_max_bytes' ? 'Absolute cap of the brief' : 'Absolute cap of the service'
  return ''
}

/** The server's own sentences for a number outside its range, so the page can say them before it asks. */
export function boundError(s: PlatformSetting, value: number): string | null {
  if (s.minimum !== null && value < s.minimum) {
    return `${s.label} cannot go below ${formatValue(s, s.minimum)}; a limit cannot be switched off from the panel.`
  }
  if (s.maximum !== null && value > s.maximum) {
    const where = s.max_source === 'env' ? 'the environment ceiling' : 'the absolute cap'
    return `${s.label} cannot go above ${formatValue(s, s.maximum)} (${where}).`
  }
  return null
}

export type Parsed = { value: number; error?: undefined } | { value?: undefined; error: string }

/** What was typed in the input as the number to send (megabytes become bytes), or the sentence saying why not. */
export function parseNumber(s: PlatformSetting, text: string): Parsed {
  const t = text.trim()
  if (isBytes(s)) {
    // Two decimals, the precision the page shows. A figure within half a display step of the value, the default or
    // a bound is that exact number, so a ceiling of 5,000,000 bytes (shown 4.77 MB) can be set and typed back.
    if (!/^\d+(\.\d{1,2})?$/.test(t)) return { error: `${s.label} must be a number of megabytes, such as 5 or 2.5.` }
    const typed = Math.round(Number(t) * BYTES_PER_MB)
    const exact = [s.value, s.default, s.minimum, s.maximum].find((n): n is number => typeof n === 'number' && Math.abs(n - typed) <= BYTES_PER_MB / 200)
    return { value: exact ?? typed }
  }
  if (!/^\d+$/.test(t)) return { error: `${s.label} must be a whole number.` }
  return { value: Number(t) }
}

/** A server sentence that quotes bytes, said in megabytes. */
export function saidInMegabytes(s: PlatformSetting, message: string): string {
  return isBytes(s) ? message.replace(/\d{6,}/g, (n) => formatValue(s, Number(n))) : message
}

/** "10 Oct 2026, 09:14" in Singapore time. */
export function formatWhen(iso: string): string {
  const p = inSingapore(new Date(iso))
  return `${formatDate(iso)}, ${String(p.hour).padStart(2, '0')}:${String(p.minute).padStart(2, '0')}`
}

/** "2 h 58 min", "12 min", "under a minute". */
export function formatSpan(ms: number): string {
  const minutes = Math.floor(Math.max(0, ms) / 60_000)
  if (minutes < 1) return 'under a minute'
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  return minutes % 60 ? `${hours} h ${minutes % 60} min` : `${hours} h`
}

export type WriteFailure = { field: 'value' | 'password'; message: string } | { field: 'general'; message: string }

/** Where a refused write belongs: a wrong password under the password, a bound or a no-change under the new value. */
export function writeFailure(error: unknown, s: PlatformSetting | null): WriteFailure {
  if (!(error instanceof AppError)) return { field: 'general', message: 'Something went wrong. Try again.' }
  if (error.code === 'step_up_failed' || error.code === 'rate_limited') return { field: 'password', message: error.message }
  const message = s ? saidInMegabytes(s, error.message) : error.message
  if (error.code === 'validation_failed' && typeof error.details?.reason === 'string') return { field: 'value', message }
  return { field: 'general', message }
}
