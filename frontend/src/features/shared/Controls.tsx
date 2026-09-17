import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { forwardRef, useId } from 'react'

import { cn } from '@/lib/cn'
import { FieldLabel, FieldMessage, inputClasses } from './Field'

interface Wrap {
  label: string
  help?: string
  error?: string
  required?: boolean
  className?: string
}

function Labelled({ id, label, help, error, required, className, children }: Wrap & { id: string; children: ReactNode }) {
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <FieldLabel htmlFor={id} required={required}>
        {label}
      </FieldLabel>
      {children}
      <FieldMessage id={id} error={error} help={help} />
    </div>
  )
}

export interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement>, Wrap {
  options: { value: string; label: string }[]
  placeholder?: string
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(function SelectField(
  { label, help, error, required, className, options, placeholder = 'Choose an option', id, ...rest },
  ref,
) {
  const autoId = useId()
  const selectId = id ?? autoId
  return (
    <Labelled id={selectId} label={label} help={help} error={error} required={required} className={className}>
      <select
        ref={ref}
        id={selectId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${selectId}-error` : help ? `${selectId}-help` : undefined}
        className={cn(
          inputClasses(Boolean(error)),
          'appearance-none bg-[url("data:image/svg+xml;utf8,<svg xmlns=%27http://www.w3.org/2000/svg%27 width=%2716%27 height=%2716%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%23465060%27 stroke-width=%272%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27><path d=%27m6 9 6 6 6-6%27/></svg>")] bg-[length:16px] bg-[right_10px_center] bg-no-repeat pr-9',
        )}
        {...rest}
      >
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Labelled>
  )
})

export interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement>, Wrap {}

export const TextAreaField = forwardRef<HTMLTextAreaElement, TextAreaFieldProps>(function TextAreaField(
  { label, help, error, required, className, id, ...rest },
  ref,
) {
  const autoId = useId()
  const areaId = id ?? autoId
  return (
    <Labelled id={areaId} label={label} help={help} error={error} required={required} className={className}>
      <textarea
        ref={ref}
        id={areaId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${areaId}-error` : help ? `${areaId}-help` : undefined}
        className={cn(inputClasses(Boolean(error)), 'h-auto min-h-24 resize-y py-2.5 leading-[22px]')}
        {...rest}
      />
    </Labelled>
  )
})

export interface CheckboxFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
  error?: string
}

/** Custom-drawn checkbox: 18 px box, animated check, same focus ring as inputs. */
export const CheckboxField = forwardRef<HTMLInputElement, CheckboxFieldProps>(function CheckboxField(
  { label, error, id, className, ...rest },
  ref,
) {
  const autoId = useId()
  const boxId = id ?? autoId
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label
        htmlFor={boxId}
        className={cn(
          'group flex cursor-pointer items-start gap-3 rounded-md border px-3.5 py-3 text-sm leading-[21px]',
          'transition-[border-color,background-color] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
          'has-[:checked]:border-line-strong has-[:checked]:bg-surface-2 has-[:disabled]:cursor-not-allowed',
          error ? 'border-error-line bg-error-soft/40' : 'border-line hover:border-line-strong',
        )}
      >
        <span className="relative mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center">
          <input
            ref={ref}
            id={boxId}
            type="checkbox"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${boxId}-error` : undefined}
            className={cn(
              'peer h-[18px] w-[18px] cursor-pointer appearance-none rounded-[4px] border bg-surface',
              'transition-[background-color,border-color,box-shadow] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
              'checked:border-text checked:bg-text focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgba(23,92,211,0.2)]',
              'disabled:cursor-not-allowed disabled:bg-surface-2',
              error ? 'border-error' : 'border-line-strong group-hover:border-text-3',
            )}
            {...rest}
          />
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#fff"
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="pointer-events-none absolute opacity-0 transition-opacity duration-[var(--dur-fast)] peer-checked:opacity-100"
          >
            <path d="M20 6 9 17l-5-5" />
          </svg>
        </span>
        <span className="text-text">{label}</span>
      </label>
      {error ? (
        <div id={`${boxId}-error`} role="alert" className="pf-enter-fast text-[13px] font-medium text-error">
          {error}
        </div>
      ) : null}
    </div>
  )
})
