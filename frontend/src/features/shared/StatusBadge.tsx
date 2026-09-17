import { cn } from '@/lib/cn'

export type Tone = 'neutral' | 'info' | 'warning' | 'success' | 'error' | 'primary'

const tones: Record<Tone, string> = {
  neutral: 'border-neutral-line bg-neutral-soft text-neutral',
  info: 'border-info-line bg-info-soft text-info',
  warning: 'border-warning-line bg-warning-soft text-warning',
  success: 'border-success-line bg-success-soft text-success',
  error: 'border-error-line bg-error-soft text-error',
  primary: 'border-primary-line bg-primary-soft text-primary',
}

export interface StatusBadgeProps {
  /** Role-specific label exactly as served by the API. The client never maps status codes. */
  label: string
  tone: Tone
  size?: 'md' | 'lg'
  /** Pulses the dot: something is in progress (checking, saving). */
  live?: boolean
  className?: string
}

/** Dot + label pill. Colour is never the only signal (UX-008). */
export function StatusBadge({ label, tone, size = 'md', live, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border font-semibold transition-colors duration-[var(--dur-base)]',
        size === 'md' ? 'h-6 px-2 text-xs' : 'h-7 px-2.5 text-[13px]',
        tones[tone],
        className,
      )}
      data-tone={tone}
    >
      <span className="relative flex h-[7px] w-[7px] shrink-0" aria-hidden="true">
        {live ? <span className="absolute inset-0 animate-ping rounded-full bg-current opacity-60" /> : null}
        <span className="relative h-[7px] w-[7px] rounded-full bg-current" />
      </span>
      {label}
    </span>
  )
}
