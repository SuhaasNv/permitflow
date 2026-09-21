import { useSyncExternalStore } from 'react'
import { Link } from 'react-router-dom'

import { cn } from '@/lib/cn'
import { hasSeenRelease, subscribeSeen } from './seen'

interface VersionChipProps {
  /** `rail`: the side rail footer and the landing footer (light); `strip`: the dark portal strip on phones. */
  variant: 'rail' | 'strip'
  className?: string
}

/** The version as a link to What's new (US-094): the mono chip plus the link's own words, "New" until the page
 * has been read once for this build, then "What's new" (on the dark strip the chip alone). */
export function VersionChip({ variant, className }: VersionChipProps) {
  const seen = useSyncExternalStore(subscribeSeen, () => hasSeenRelease(__APP_VERSION__), () => true)
  const dark = variant === 'strip'
  return (
    <Link
      to="/releases"
      aria-label={`Version ${__APP_VERSION__}, what's new`}
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded no-underline',
        // On the strip the whole 28 px height is the target, with air on both sides.
        dark ? 'h-7 px-2 text-[#d9dee5] hover:text-white' : 'min-h-6 text-text-3 hover:text-text',
        className,
      )}
    >
      <span
        className={cn(
          'rounded border px-1.5 font-mono text-[10px] leading-4',
          dark ? 'border-[#6b7684]' : 'border-line group-hover:border-line-strong',
        )}
      >
        v{__APP_VERSION__}
      </span>
      {!seen ? (
        <span className={cn('text-[11px] font-semibold', dark ? 'text-white' : 'text-primary')}>New</span>
      ) : dark ? null : (
        <span className="text-xs font-medium text-text-2 underline underline-offset-2">What's new</span>
      )}
    </Link>
  )
}
