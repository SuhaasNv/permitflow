import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Tone = 'info' | 'warning' | 'error' | 'success' | 'neutral'

const tones: Record<Tone, string> = {
  info: 'border-info-line bg-info-soft text-[#0f3e8a]',
  warning: 'border-warning-line bg-warning-soft text-[#6e3500]',
  error: 'border-error-line bg-error-soft text-[#7a1a12]',
  success: 'border-success-line bg-success-soft text-[#04532f]',
  neutral: 'border-line bg-surface-2 text-text-2',
}

export function Alert({ tone = 'info', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <div
      role={tone === 'error' ? 'alert' : 'status'}
      className={cn('flex gap-3 rounded-md border px-4 py-3 text-sm leading-5', tones[tone], className)}
    >
      {children}
    </div>
  )
}
