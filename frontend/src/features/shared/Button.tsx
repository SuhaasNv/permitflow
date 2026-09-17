import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '@/lib/cn'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'md' | 'sm' | 'lg'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  children: ReactNode
}

export const buttonClasses = (variant: Variant = 'primary', size: Size = 'md', extra = ''): string =>
  cn(
    'inline-flex items-center justify-center gap-2 rounded-md border text-sm font-semibold whitespace-nowrap transition-colors',
    'disabled:cursor-not-allowed disabled:border-line disabled:bg-neutral-soft disabled:text-text-3 disabled:shadow-none',
    size === 'md' && 'h-10 px-4',
    size === 'sm' && 'h-8 px-3 text-[13px]',
    size === 'lg' && 'h-12 px-6',
    variant === 'primary' && 'border-transparent bg-primary text-white hover:bg-primary-hover',
    variant === 'secondary' && 'border-line-strong bg-surface text-text shadow-[var(--shadow-1)] hover:bg-surface-2',
    variant === 'ghost' && 'border-transparent bg-transparent text-text-2 hover:bg-neutral-soft hover:text-text',
    variant === 'danger' && 'border-line-strong bg-surface text-text-2 hover:border-error-line hover:bg-error-soft hover:text-error',
    extra,
  )

export function Button({ variant = 'primary', size = 'md', loading = false, className = '', children, disabled, ...rest }: ButtonProps) {
  return (
    <button className={buttonClasses(variant, size, className)} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" aria-hidden="true" />
      ) : null}
      {children}
    </button>
  )
}
