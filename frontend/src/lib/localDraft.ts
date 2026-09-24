/**
 * A copy of entries the server has not confirmed yet, kept on this device (UAT run 5, F11 and F13).
 *
 * On site the connection drops; an iPad may reload or discard a background tab before it returns, and
 * iOS Safari shows no "leave page" prompt. Pages write what is unsaved here as it is typed, clear it once
 * a save lands, and offer it back on the next load. Storage can be unavailable (private mode, quota): every
 * call is guarded and the page keeps working without it.
 */

const PREFIX = 'permitflow.unsaved.'
/** A copy older than this is dropped on read: a week-old entry is more likely stale than lost work. */
const MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000

interface Stored<T> {
  savedAt: number
  value: T
}

export function readLocalDraft<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null || !('savedAt' in parsed) || !('value' in parsed)) return null
    const stored = parsed as Stored<T>
    if (typeof stored.savedAt !== 'number' || Date.now() - stored.savedAt > MAX_AGE_MS) {
      localStorage.removeItem(PREFIX + key)
      return null
    }
    return stored.value
  } catch {
    return null
  }
}

export function writeLocalDraft<T>(key: string, value: T): void {
  try {
    const stored: Stored<T> = { savedAt: Date.now(), value }
    localStorage.setItem(PREFIX + key, JSON.stringify(stored))
  } catch {
    // Storage full or unavailable: the in-memory copy and the server retries still hold the entries.
  }
}

export function clearLocalDraft(key: string): void {
  try {
    localStorage.removeItem(PREFIX + key)
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}

/** Every copy on this device: the user's own Sign out leaves nothing of theirs behind on a shared tablet. A session
 * ended by another device or by expiry keeps them, so the same officer can sign in again and carry on. */
export function clearAllLocalDrafts(): void {
  try {
    for (const key of Object.keys(localStorage)) if (key.startsWith(PREFIX)) localStorage.removeItem(key)
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}
