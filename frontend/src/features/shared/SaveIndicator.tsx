import { useEffect, useState } from 'react'

import { cn } from '@/lib/cn'
import { inSingapore } from '@/lib/format'

export interface SaveIndicatorProps {
  dirty: boolean
  saving: boolean
  /** Epoch ms of the last successful save in this session, or null if none yet. */
  savedAt: number | null
  /** A save failed on the way and will be tried again (US-061). */
  retrying?: boolean
  className?: string
}

function relative(savedAt: number, now: number): string {
  const seconds = Math.max(0, Math.round((now - savedAt) / 1000))
  if (seconds < 8) return 'Saved just now'
  if (seconds < 60) return `Saved ${seconds} s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `Saved ${minutes} min ago`
  const p = inSingapore(new Date(savedAt))
  return `Saved at ${String(p.hour).padStart(2, '0')}:${String(p.minute).padStart(2, '0')}`
}

/** "Unsaved changes" / "Saving…" / "Saved just now" with a live relative time. Polite live region. */
export function SaveIndicator({ dirty, saving, savedAt, retrying = false, className }: SaveIndicatorProps) {
  const [now, setNow] = useState(() => Date.now())
  // savedAt changes only on a successful save; "now" then starts from that instant.
  const clock = savedAt !== null && savedAt > now ? savedAt : now
  useEffect(() => {
    if (savedAt === null) return
    const timer = setInterval(() => setNow(Date.now()), 5000)
    return () => clearInterval(timer)
  }, [savedAt])

  let text: string
  let tone: 'muted' | 'saving' | 'saved' | 'dirty' | 'retrying'
  if (saving) {
    text = 'Saving…'
    tone = 'saving'
  } else if (retrying) {
    text = 'Could not save, retrying'
    tone = 'retrying'
  } else if (dirty) {
    text = 'Unsaved changes'
    tone = 'dirty'
  } else if (savedAt !== null) {
    text = relative(savedAt, clock)
    tone = 'saved'
  } else {
    text = 'No changes yet'
    tone = 'muted'
  }

  return (
    <span
      className={cn('inline-flex h-6 items-center gap-1.5 text-xs font-medium transition-colors duration-[var(--dur-base)]', className)}
      aria-live="polite"
      data-state={tone}
    >
      <span key={tone} className="pf-enter-fast inline-flex items-center gap-1.5">
        {tone === 'saving' ? (
          <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-line-strong border-t-text-2" aria-hidden="true" />
        ) : tone === 'saved' ? (
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="text-success"
          >
            <path className="pf-check" d="M20 6 9 17l-5-5" />
          </svg>
        ) : tone === 'dirty' ? (
          <span className="h-[7px] w-[7px] rounded-full bg-warning" aria-hidden="true" />
        ) : tone === 'retrying' ? (
          <span className="h-[7px] w-[7px] rounded-full bg-error" aria-hidden="true" />
        ) : null}
        <span
          className={cn(
            tone === 'saved' ? 'text-text-2' : tone === 'dirty' ? 'text-warning' : tone === 'retrying' ? 'text-error' : 'text-text-3',
          )}
        >
          {text}
        </span>
      </span>
    </span>
  )
}
