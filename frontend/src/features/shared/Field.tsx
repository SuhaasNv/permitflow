import type { InputHTMLAttributes, ReactNode } from 'react'
import { forwardRef, useId } from 'react'

import { cn } from '@/lib/cn'

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  help?: string
  error?: string
  required?: boolean
  trailing?: ReactNode
}

export const inputClasses = (invalid = false, readOnly = false): string =>
  cn(
    'h-10 min-h-[44px] w-full rounded-md border bg-surface px-3 text-[15px] text-text placeholder:text-text-3/70 xl:min-h-0',
    'transition-[border-color,box-shadow,background-color] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
    'focus:border-focus focus:shadow-[0_0_0_3px_rgba(23,92,211,0.16)] focus:outline-none',
    'disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-text-2',
    invalid ? 'border-error shadow-[0_0_0_3px_rgba(180,35,24,0.12)]' : 'border-line-strong hover:border-text-3',
    readOnly && 'border-line bg-surface-2 text-text-2',
  )

export function FieldLabel({ htmlFor, required, children }: { htmlFor: string; required?: boolean; children: ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="flex items-baseline gap-1.5 text-[13px] font-semibold leading-[18px] text-text">
      {children}
      {required ? (
        <span className="text-error" aria-hidden="true">
          *
        </span>
      ) : (
        <span className="text-xs font-normal text-text-3">Optional</span>
      )}
    </label>
  )
}

export function FieldMessage({ id, error, help }: { id: string; error?: string; help?: string }) {
  if (error) {
    return (
      <div
        id={`${id}-error`}
        role="alert"
        className="pf-enter-fast flex items-start gap-1.5 text-[13px] leading-[18px] font-medium text-error"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
          className="mt-0.5 shrink-0"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4.5M12 16h.01" />
        </svg>
        <span>{error}</span>
      </div>
    )
  }
  if (help) {
    return (
      <div id={`${id}-help`} className="text-[13px] leading-[18px] text-text-3">
        {help}
      </div>
    )
  }
  return null
}

/** Label + control + help/error. The error is announced (role="alert") and linked via aria-describedby (UX-003). */
export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, help, error, required, trailing, id, className, ...rest },
  ref,
) {
  const autoId = useId()
  const inputId = id ?? autoId
  const describedBy = error ? `${inputId}-error` : help ? `${inputId}-help` : undefined
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <FieldLabel htmlFor={inputId} required={required}>
        {label}
      </FieldLabel>
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          aria-required={required || undefined}
          className={inputClasses(Boolean(error), rest.readOnly)}
          {...rest}
        />
        {trailing ? <span className="absolute right-1.5 top-1/2 flex -translate-y-1/2 items-center text-text-3">{trailing}</span> : null}
      </div>
      <FieldMessage id={inputId} error={error} help={help} />
    </div>
  )
})
