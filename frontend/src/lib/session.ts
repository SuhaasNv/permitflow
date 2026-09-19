/** Session-end warning (US-048): silent until 30 minutes remain, then a countdown; urgent inside 5 minutes. */

export const WARN_AFTER_MS = 30 * 60 * 1000
export const URGENT_AFTER_MS = 5 * 60 * 1000

export type SessionWarning = { level: 'none' } | { level: 'warn' | 'urgent'; text: string }

export function sessionWarning(expiresAtIso: string, now: number = Date.now()): SessionWarning {
  const remaining = new Date(expiresAtIso).getTime() - now
  if (Number.isNaN(remaining) || remaining > WARN_AFTER_MS) return { level: 'none' }
  const minutes = Math.max(0, Math.ceil(remaining / 60_000))
  const text = minutes <= 1 ? 'Session ends in under a minute' : `Session ends in ${minutes} min`
  return { level: remaining <= URGENT_AFTER_MS ? 'urgent' : 'warn', text }
}
