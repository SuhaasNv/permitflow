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

/**
 * Shared button classes, also used by router Links that must look like buttons.
 * Hover lifts the tone, press settles it (150 ms), focus shows the 2 px ring.
 */
export const buttonClasses = (variant: Variant = 'primary', size: Size = 'md', extra = ''): string =>
  cn(
    'inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-md border text-sm font-semibold no-underline',
    'transition-[background-color,border-color,color,box-shadow,transform] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
    'active:translate-y-px active:duration-75',
    'disabled:pointer-events-none disabled:border-line disabled:bg-neutral-soft disabled:text-text-3 disabled:shadow-none',
    size === 'md' && 'h-10 px-4',
    size === 'sm' && 'h-8 px-3 text-[13px]',
    size === 'lg' && 'h-12 px-6 text-[15px]',
    variant === 'primary' &&
      'border-transparent bg-primary text-white shadow-[inset_0_-1px_0_rgba(0,0,0,0.12)] hover:bg-primary-hover hover:text-white',
    variant === 'secondary' &&
      'border-line-strong bg-surface text-text shadow-[var(--shadow-1)] hover:border-text-3 hover:bg-surface-2 hover:text-text',
    variant === 'ghost' && 'border-transparent bg-transparent text-text-2 hover:bg-neutral-soft hover:text-text',
    variant === 'danger' && 'border-line-strong bg-surface text-text-2 hover:border-error-line hover:bg-error-soft hover:text-error',
    extra,
  )

export function Button({ variant = 'primary', size = 'md', loading = false, className = '', children, disabled, ...rest }: ButtonProps) {
  return (
    <button className={buttonClasses(variant, size, className)} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? (
        <span
          className={cn(
            'h-4 w-4 animate-spin rounded-full border-2',
            variant === 'primary' ? 'border-white/40 border-t-white' : 'border-line-strong border-t-text-2',
          )}
          aria-hidden="true"
        />
      ) : null}
      {children}
    </button>
  )
}
