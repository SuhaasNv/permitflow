/**
 * Every date the product shows is a Singapore date (NFR-016, US-090): instants are rendered in
 * Asia/Singapore whatever the browser's own zone; date-only values ("2026-09-19") are calendar dates
 * and never shift. One helper set for the whole frontend.
 */
export const SINGAPORE = 'Asia/Singapore'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

const pad = (n: number): string => String(n).padStart(2, '0')

interface Parts {
  year: number
  month: number
  day: number
  hour: number
  minute: number
}

const partsFormat = new Intl.DateTimeFormat('en-GB', {
  timeZone: SINGAPORE,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

/** The Singapore wall-clock parts of an instant. */
export function inSingapore(d: Date): Parts {
  const p: Record<string, string> = {}
  for (const part of partsFormat.formatToParts(d)) p[part.type] = part.value
  return { year: Number(p.year), month: Number(p.month), day: Number(p.day), hour: Number(p.hour) % 24, minute: Number(p.minute) }
}

/** "2026-09-22": the calendar date in Singapore right now (or at `now`). */
export function todayInSingapore(now: Date = new Date()): string {
  const p = inSingapore(now)
  return `${p.year}-${pad(p.month)}-${pad(p.day)}`
}

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/

/** "17 Sep, 10:31" in Singapore time. */
export function formatDateTime(iso: string): string {
  const p = inSingapore(new Date(iso))
  return `${p.day} ${MONTHS[p.month - 1]}, ${pad(p.hour)}:${pad(p.minute)}`
}

/** "17 Sep 2026": a date-only value as the calendar date it names, an instant as its Singapore date. */
export function formatDate(iso: string): string {
  const dateOnly = DATE_ONLY.exec(iso)
  if (dateOnly) return `${Number(dateOnly[3])} ${MONTHS[Number(dateOnly[2]) - 1]} ${dateOnly[1]}`
  const p = inSingapore(new Date(iso))
  return `${p.day} ${MONTHS[p.month - 1]} ${p.year}`
}

/** "just now", "12 min ago", "3 h ago", otherwise the date. */
export function formatRelative(iso: string, now: number = Date.now()): string {
  const diff = Math.max(0, now - new Date(iso).getTime())
  const minutes = Math.round(diff / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 7) return `${days} d ago`
  return formatDate(iso)
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`
  const mb = n / (1024 * 1024)
  return mb >= 10 ? `${Math.round(mb)} MB` : `${mb.toFixed(1)} MB`
}

/** Time-of-day greeting for the dashboard, by the Singapore hour. */
export function greeting(hour: number = inSingapore(new Date()).hour): string {
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}
