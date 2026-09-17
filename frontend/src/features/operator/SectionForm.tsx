import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useRef, useState } from 'react'
import type { Resolver } from 'react-hook-form'
import { useForm } from 'react-hook-form'

import { AppError } from '@/api/client'
import type { FieldDef, SectionDef } from '@/api/formSchema'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { CheckboxField, SelectField, TextAreaField } from '@/features/shared/Controls'
import { Field } from '@/features/shared/Field'
import type { SectionValues } from '@/lib/zodFromSchema'
import { defaultsFor, sectionSchema, toPayload } from '@/lib/zodFromSchema'

export interface SectionFormProps {
  section: SectionDef
  data: Record<string, unknown>
  editable: boolean
  saving: boolean
  isLast: boolean
  onSave: (payload: Record<string, unknown>, andContinue: boolean) => Promise<void>
  onDirtyChange: (dirty: boolean) => void
}

function fieldError(errors: Record<string, { message?: string } | undefined>, key: string): string | undefined {
  return errors[key]?.message
}

export function SectionForm({ section, data, editable, saving, isLast, onSave, onDirtyChange }: SectionFormProps) {
  const draftSchema = sectionSchema(section, 'draft')
  const completeSchema = sectionSchema(section, 'complete')
  // The schema is built at runtime from the server definition, so its static type is a generic record.
  const resolver = zodResolver(draftSchema) as unknown as Resolver<SectionValues>
  const form = useForm<SectionValues>({
    resolver,
    defaultValues: defaultsFor(section, data),
    mode: 'onBlur',
  })
  const [summary, setSummary] = useState<string[]>([])
  const [serverError, setServerError] = useState<string | null>(null)
  const summaryRef = useRef<HTMLDivElement>(null)

  const dirty = form.formState.isDirty
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange])

  // Re-seed when the section (or its saved data) changes.
  useEffect(() => {
    form.reset(defaultsFor(section, data))
    setSummary([])
    setServerError(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section.key, data])

  const submit = (andContinue: boolean) =>
    form.handleSubmit(async (values) => {
      setServerError(null)
      setSummary([])
      if (andContinue) {
        const parsed = completeSchema.safeParse(values)
        if (!parsed.success) {
          const messages: string[] = []
          for (const issue of parsed.error.issues) {
            const key = String(issue.path[0] ?? '')
            const field = section.fields.find((f) => f.key === key)
            form.setError(key, { type: 'manual', message: issue.message })
            messages.push(field ? field.label : key)
          }
          setSummary(messages)
          summaryRef.current?.focus()
          return
        }
      }
      try {
        await onSave(toPayload(values), andContinue)
        form.reset(values)
      } catch (error) {
        if (error instanceof AppError && error.status === 422 && error.details && typeof error.details.fields === 'object') {
          const fields = error.details.fields as Record<string, string>
          for (const [key, message] of Object.entries(fields)) form.setError(key, { type: 'server', message })
          setSummary(Object.keys(fields).map((k) => section.fields.find((f) => f.key === k)?.label ?? k))
        } else {
          setServerError(error instanceof Error ? error.message : 'Could not save this section. Your entries are still here; try again.')
        }
      }
    })

  const errors = form.formState.errors as Record<string, { message?: string } | undefined>

  const render = (f: FieldDef) => {
    const common = {
      label: f.label,
      help: f.help ?? undefined,
      required: f.required,
      error: fieldError(errors, f.key),
      disabled: !editable,
    }
    const wide = f.kind === 'textarea' || f.key === 'address_line_1' || f.kind === 'checkbox'
    const className = wide ? 'sm:col-span-2' : undefined
    switch (f.kind) {
      case 'select':
        return <SelectField key={f.key} {...common} className={className} options={f.options} {...form.register(f.key)} />
      case 'textarea':
        return (
          <TextAreaField key={f.key} {...common} className={className} maxLength={f.max_length ?? undefined} {...form.register(f.key)} />
        )
      case 'checkbox':
        return (
          <CheckboxField
            key={f.key}
            label={f.label}
            error={common.error}
            disabled={!editable}
            className={className}
            {...form.register(f.key)}
          />
        )
      case 'number':
      case 'integer':
        return (
          <Field
            key={f.key}
            {...common}
            className={className}
            type="number"
            inputMode={f.kind === 'integer' ? 'numeric' : 'decimal'}
            step={f.kind === 'integer' ? 1 : 'any'}
            {...form.register(f.key, {
              setValueAs: (v: string) => (v === '' ? undefined : Number(v)),
            })}
          />
        )
      case 'date':
        return <Field key={f.key} {...common} className={className} type="date" {...form.register(f.key)} />
      default:
        return (
          <Field
            key={f.key}
            {...common}
            className={className}
            type={f.kind === 'email' ? 'email' : f.kind === 'tel' ? 'tel' : 'text'}
            inputMode={f.key === 'postal_code' ? 'numeric' : undefined}
            maxLength={f.max_length ?? undefined}
            {...form.register(f.key)}
          />
        )
    }
  }

  return (
    <form
      noValidate
      onSubmit={submit(true)}
      className="rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]"
      aria-labelledby={`section-${section.key}`}
    >
      <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-4">
        <h2 id={`section-${section.key}`} className="text-base font-semibold">
          {section.title}
        </h2>
        <span className="text-xs text-text-3">{section.description}</span>
        {!editable ? (
          <span className="ml-auto rounded border border-neutral-line bg-neutral-soft px-2 text-xs font-medium text-text-3">Read-only</span>
        ) : null}
      </div>
      <div className="flex flex-col gap-4 p-5">
        {summary.length > 0 ? (
          <div ref={summaryRef} tabIndex={-1}>
            <Alert tone="error">
              <div>
                <b>
                  {summary.length} {summary.length === 1 ? 'field needs' : 'fields need'} attention before this section is complete.
                </b>
                <div className="mt-0.5 text-[13px]">{summary.join(' · ')}</div>
              </div>
            </Alert>
          </div>
        ) : null}
        {serverError ? (
          <Alert tone="error">
            <span>{serverError}</span>
          </Alert>
        ) : null}
        <div className="grid gap-4 sm:grid-cols-2 sm:gap-x-5">{section.fields.map(render)}</div>
      </div>
      {editable ? (
        <div className="flex flex-wrap items-center justify-end gap-2 rounded-b-lg border-t border-line bg-surface-2 px-5 py-3">
          <span className="mr-auto text-xs text-text-3">{dirty ? 'Unsaved changes' : 'All changes saved'}</span>
          <Button type="button" variant="secondary" onClick={submit(false)} disabled={saving}>
            Save section
          </Button>
          <Button type="submit" loading={saving}>
            {isLast ? 'Save and review' : 'Save and continue'}
          </Button>
        </div>
      ) : null}
    </form>
  )
}
