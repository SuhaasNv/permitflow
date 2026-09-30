/** Session-end warning (US-048): silent until 30 minutes remain, then a countdown; urgent inside 5 minutes. */

export const WARN_AFTER_MS = 30 * 60 * 1000
export const URGENT_AFTER_MS = 5 * 60 * 1000

export type SessionWarning = { level: 'none' } | { level: 'warn' | 'urgent'; text: string }

/** The server ends a session after SESSION_IDLE_MINUTES without a request (US-093), 60 in every environment.
 * ponytail: mirrors the backend default; send the number with the token if an environment ever changes it. */
export const IDLE_LIMIT_MS = 60 * 60 * 1000
export const IDLE_WARN_MS = 5 * 60 * 1000

/** Idle warning (US-095, WCAG 2.2.1): the time left before the idle sign-out, once inside the last 5 minutes. */
export function idleWarning(lastActivityAt: number, now: number = Date.now()): string | null {
  const remaining = lastActivityAt + IDLE_LIMIT_MS - now
  if (remaining > IDLE_WARN_MS) return null
  const minutes = Math.max(0, Math.ceil(remaining / 60_000))
  return minutes <= 1 ? 'under a minute' : `${minutes} min`
}

export function sessionWarning(expiresAtIso: string, now: number = Date.now()): SessionWarning {
  const remaining = new Date(expiresAtIso).getTime() - now
  if (Number.isNaN(remaining) || remaining > WARN_AFTER_MS) return { level: 'none' }
  const minutes = Math.max(0, Math.ceil(remaining / 60_000))
  const text = minutes <= 1 ? 'Session ends in under a minute' : `Session ends in ${minutes} min`
  return { level: remaining <= URGENT_AFTER_MS ? 'urgent' : 'warn', text }
}
