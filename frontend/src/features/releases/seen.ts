/**
 * The "New" mark beside the version (US-094): shown until the What's new page has been opened once for this
 * build, per browser. A convenience only, so storage that is missing or refused (private windows, cleared
 * site data) just means the mark shows; nothing else depends on it. Chips already on screen learn of a
 * read through one window event, so the mark clears the moment the page opens.
 */

const KEY = 'permitflow.releases.seen'
const EVENT = 'permitflow:release-seen'

export function hasSeenRelease(version: string): boolean {
  try {
    return localStorage.getItem(KEY) === version
  } catch {
    return false
  }
}

export function markReleaseSeen(version: string): void {
  try {
    localStorage.setItem(KEY, version)
  } catch {
    // Nothing to do: the mark shows again next time.
  }
  window.dispatchEvent(new Event(EVENT))
}

/** For `useSyncExternalStore`: fires on a read in this tab and on a change from another tab. */
export function subscribeSeen(onChange: () => void): () => void {
  window.addEventListener(EVENT, onChange)
  window.addEventListener('storage', onChange)
  return () => {
    window.removeEventListener(EVENT, onChange)
    window.removeEventListener('storage', onChange)
  }
}
