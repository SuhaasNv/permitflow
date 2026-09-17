import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Tone = 'info' | 'warning' | 'error' | 'success' | 'neutral'

const tones: Record<Tone, string> = {
  info: 'border-info-line/70 bg-info-soft text-[#0f3e8a]',
  warning: 'border-warning-line/70 bg-warning-soft text-[#6e3500]',
  error: 'border-error-line/70 bg-error-soft text-[#7a1a12]',
  success: 'border-success-line/70 bg-success-soft text-[#04532f]',
  neutral: 'border-line bg-surface-2 text-text-2',
}

const PATHS: Record<Tone, string> = {
  info: 'M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
  warning: 'm10.3 3.9-8.5 14.6A2 2 0 0 0 3.5 21.5h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01',
  error: 'M12 8v4.5M12 16h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
  success: 'M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4 12 14l-3-3',
  neutral: 'M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
}

export interface AlertProps {
  tone?: Tone
  title?: string
  children: ReactNode
  className?: string
  action?: ReactNode
}

/** Inline message with a tone icon. Errors are announced immediately, everything else politely. */
export function Alert({ tone = 'info', title, children, className, action }: AlertProps) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn('pf-enter-fast flex gap-3 rounded-md border px-4 py-3 text-sm leading-5', tones[tone], className)}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className="mt-px shrink-0"
      >
        <path d={PATHS[tone]} />
      </svg>
      <div className="min-w-0 flex-1">
        {title ? <div className="font-semibold">{title}</div> : null}
        <div className={cn(title && 'mt-0.5 text-[13px] leading-[19px] opacity-90')}>{children}</div>
      </div>
      {action ? <div className="shrink-0 self-center">{action}</div> : null}
    </div>
  )
}
