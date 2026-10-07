import { useSyncExternalStore } from 'react'

/** True while the browser reports a connection; pages hold their entries until it returns (US-061, US-087). */
export function useOnline(): boolean {
  return useSyncExternalStore(
    (notify) => {
      window.addEventListener('online', notify)
      window.addEventListener('offline', notify)
      return () => {
        window.removeEventListener('online', notify)
        window.removeEventListener('offline', notify)
      }
    },
    () => navigator.onLine,
    () => true,
  )
}

/** A failed save or upload is tried again after 1 s, then 2, 4, 8 and 16 s, then every 30 s (US-087). */
export function retryDelay(attempt: number): number {
  return Math.min(1000 * 2 ** Math.max(0, attempt - 1), 30_000)
}

/** Whether a failed request is worth retrying by itself: the network, or the server, not the request. */
export function isTransient(error: unknown): boolean {
  const status = (error as { status?: number } | null)?.status
  return status === 0 || status === undefined || status >= 500 || status === 408 || status === 429
}

/** No retry while the tab is hidden: the browser throttles timers there and a save with keepalive already went. */
export function tabHidden(): boolean {
  return typeof document !== 'undefined' && document.visibilityState === 'hidden'
}
