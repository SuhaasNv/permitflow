import { Link, useLocation } from 'react-router-dom'

import { cn } from '@/lib/cn'

/** Brand mark (docs/design/brand) + wordmark. The wordmark is never coloured red. */
export function Logo({ inverted = false, className }: { inverted?: boolean; className?: string }) {
  const { pathname } = useLocation()
  return (
    <Link
      to="/"
      onClick={(e) => {
        // Already on the landing page: scroll back to the top instead of a no-op navigation.
        if (pathname !== '/') return
        e.preventDefault()
        const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
        window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' })
      }}
      className={cn(
        'flex items-center gap-2.5 no-underline',
        inverted ? 'text-white hover:text-white' : 'text-text hover:text-text',
        className,
      )}
      aria-label="PermitFlow home"
    >
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="#A8192A" />
        <path
          d="M9 10h14M9 16h9M9 22h4M16.5 22l2.5 2.5L24 18"
          fill="none"
          stroke="#fff"
          strokeWidth="2.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="text-[17px] font-bold tracking-[-0.02em]">PermitFlow</span>
      <span
        className={cn('hidden border-l pl-2.5 text-xs sm:inline', inverted ? 'border-white/25 text-white/70' : 'border-line text-text-3')}
      >
        Licensing Services
      </span>
    </Link>
  )
}
