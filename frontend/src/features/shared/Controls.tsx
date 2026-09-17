import type { ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { forwardRef, useId } from 'react'

import { cn } from '@/lib/cn'
import { inputClasses } from './Field'

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
      <label htmlFor={id} className="text-[13px] font-semibold leading-[18px]">
        {label}
        {required ? (
          <span className="ml-0.5 text-error" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {children}
      {error ? (
        <div id={`${id}-error`} role="alert" className="text-[13px] font-medium text-error">
          {error}
        </div>
      ) : help ? (
        <div id={`${id}-help`} className="text-[13px] text-text-3">
          {help}
        </div>
      ) : null}
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
          'appearance-none bg-[url("data:image/svg+xml;utf8,<svg xmlns=%27http://www.w3.org/2000/svg%27 width=%2716%27 height=%2716%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%23465060%27 stroke-width=%272%27><path d=%27m6 9 6 6 6-6%27/></svg>")] bg-[length:16px] bg-[right_10px_center] bg-no-repeat pr-9',
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
        className={cn(inputClasses(Boolean(error)), 'h-auto min-h-24 resize-y py-2.5')}
        {...rest}
      />
    </Labelled>
  )
})

export interface CheckboxFieldProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: string
  error?: string
}

export const CheckboxField = forwardRef<HTMLInputElement, CheckboxFieldProps>(function CheckboxField(
  { label, error, id, className, ...rest },
  ref,
) {
  const autoId = useId()
  const boxId = id ?? autoId
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={boxId} className="flex items-start gap-2.5 text-sm">
        <input
          ref={ref}
          id={boxId}
          type="checkbox"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${boxId}-error` : undefined}
          className="mt-0.5 h-[18px] w-[18px] shrink-0 accent-primary"
          {...rest}
        />
        <span>{label}</span>
      </label>
      {error ? (
        <div id={`${boxId}-error`} role="alert" className="text-[13px] font-medium text-error">
          {error}
        </div>
      ) : null}
    </div>
  )
})
