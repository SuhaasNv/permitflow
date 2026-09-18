import { zodResolver } from '@hookform/resolvers/zod'
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import type { Resolver } from 'react-hook-form'
import { useForm } from 'react-hook-form'

import { AppError } from '@/api/client'
import type { OperatorFeedback } from '@/api/applications'
import type { FieldDef, SectionDef } from '@/api/formSchema'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { CheckboxField, SelectField, TextAreaField } from '@/features/shared/Controls'
import { Field } from '@/features/shared/Field'
import { SaveIndicator } from '@/features/shared/SaveIndicator'
import { useToast } from '@/features/shared/Toast'
import type { SectionValues } from '@/lib/zodFromSchema'
import { defaultsFor, sectionSchema, toPayload } from '@/lib/zodFromSchema'

export interface SectionFormHandle {
  /** Save the current values as a draft (partial allowed). Resolves true when saved, false when validation blocked it. */
  saveDraft: () => Promise<boolean>
}

export interface SectionFormProps {
  section: SectionDef
  data: Record<string, unknown>
  editable: boolean
  saving: boolean
  savedAt?: number | null
  isLast: boolean
  /** Overrides the primary button label (responding to feedback walks flagged targets, not the next section). */
  continueLabel?: string
  stepLabel?: string
  feedback?: OperatorFeedback[]
  lockedReason?: string
  onSave: (payload: Record<string, unknown>, andContinue: boolean) => Promise<void>
  onDirtyChange: (dirty: boolean) => void
}

function fieldError(errors: Record<string, { message?: string } | undefined>, key: string): string | undefined {
  return errors[key]?.message
}

export const SectionForm = forwardRef<SectionFormHandle, SectionFormProps>(function SectionForm(
  {
    section,
    data,
    editable,
    saving,
    savedAt = null,
    isLast,
    continueLabel,
    stepLabel,
    feedback = [],
    lockedReason,
    onSave,
    onDirtyChange,
  }: SectionFormProps,
  ref,
) {
  const draftSchema = sectionSchema(section, 'draft')
  const completeSchema = sectionSchema(section, 'complete')
  // The schema is built at runtime from the server definition, so its static type is a generic record.
  const resolver = zodResolver(draftSchema) as unknown as Resolver<SectionValues>
  const form = useForm<SectionValues>({
    resolver,
    defaultValues: defaultsFor(section, data),
    mode: 'onBlur',
  })
  const toast = useToast()
  const [summary, setSummary] = useState<string[]>([])
  const [serverError, setServerError] = useState<string | null>(null)
  const [updatedElsewhere, setUpdatedElsewhere] = useState(false)
  const summaryRef = useRef<HTMLDivElement>(null)
  // True while our own save is in flight: the server data that comes back is ours, not another tab's.
  const savingRef = useRef(false)

  const dirty = form.formState.isDirty
  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange])

  // Re-seed when the section (or its saved data) changes. Never wipe what the user is typing: if the form is
  // dirty when new server data arrives (another tab saved), keep the edits and say so.
  useEffect(() => {
    if (form.formState.isDirty && !savingRef.current) {
      setUpdatedElsewhere(true)
      return
    }
    form.reset(defaultsFor(section, data))
    setUpdatedElsewhere(false)
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
      savingRef.current = true
      try {
        await onSave(toPayload(values), andContinue)
        form.reset(values)
        if (!andContinue) toast.push({ title: 'Section saved', body: `${section.title} is saved as part of your draft.`, tone: 'success' })
      } catch (error) {
        if (error instanceof AppError && error.status === 422 && error.details && typeof error.details.fields === 'object') {
          const fields = error.details.fields as Record<string, string>
          for (const [key, message] of Object.entries(fields)) form.setError(key, { type: 'server', message })
          setSummary(Object.keys(fields).map((k) => section.fields.find((f) => f.key === k)?.label ?? k))
        } else {
          setServerError(error instanceof Error ? error.message : 'Could not save this section. Your entries are still here; try again.')
        }
      } finally {
        savingRef.current = false
      }
    })

  useImperativeHandle(
    ref,
    () => ({
      saveDraft: () =>
        new Promise<boolean>((resolve) => {
          void form.handleSubmit(
            async (values) => {
              savingRef.current = true
              try {
                await onSave(toPayload(values), false)
                form.reset(values)
                resolve(true)
              } catch (error) {
                setServerError(error instanceof Error ? error.message : 'Could not save this section.')
                resolve(false)
              } finally {
                savingRef.current = false
              }
            },
            () => resolve(false),
          )()
        }),
    }),
    [form, onSave],
  )

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
    <form noValidate onSubmit={submit(true)} className="pf-surface" aria-labelledby={`section-${section.key}`}>
      <div className="flex flex-wrap items-start gap-x-4 gap-y-1 border-b border-line px-5 py-5 sm:px-7">
        <div className="min-w-0 flex-1">
          {stepLabel ? <div className="pf-eyebrow mb-1.5">{stepLabel}</div> : null}
          <h2 id={`section-${section.key}`} className="text-[22px] font-semibold leading-7 tracking-[-0.01em]">
            {section.title}
          </h2>
          {section.description ? <p className="mt-1 text-[14px] leading-5 text-text-2">{section.description}</p> : null}
        </div>
        {!editable ? (
          <span className="mt-1 inline-flex h-6 items-center gap-1.5 rounded-full border border-neutral-line bg-neutral-soft px-2 text-xs font-medium text-text-2">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            Read-only
          </span>
        ) : null}
      </div>
      <div className="flex flex-col gap-5 px-5 py-6 sm:px-7">
        {feedback
          .filter((f) => f.resolution === 'open')
          .map((f) => (
            <Alert key={f.id} tone="warning" title="The licensing office asked for a change here">
              {f.message}
            </Alert>
          ))}
        {feedback.some((f) => f.resolution === 'addressed') ? (
          <Alert tone="info">
            <span>You changed this section in your latest revision. The officer will review it.</span>
          </Alert>
        ) : null}
        {!editable && lockedReason ? (
          <Alert tone="neutral">
            <span>{lockedReason}</span>
          </Alert>
        ) : null}
        {summary.length > 0 ? (
          <div ref={summaryRef} tabIndex={-1} className="outline-none">
            <Alert
              tone="error"
              title={`${summary.length} ${summary.length === 1 ? 'field needs' : 'fields need'} attention before this section is complete.`}
            >
              {summary.join(' · ')}
            </Alert>
          </div>
        ) : null}
        {serverError ? (
          <Alert tone="error">
            <span>{serverError}</span>
          </Alert>
        ) : null}
        {updatedElsewhere ? (
          <Alert
            tone="warning"
            title="This section was updated elsewhere"
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  form.reset(defaultsFor(section, data))
                  setUpdatedElsewhere(false)
                }}
              >
                Discard my edits
              </Button>
            }
          >
            Another tab or device saved this section. Your unsaved edits are still here; saving will overwrite the other version.
          </Alert>
        ) : null}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-x-6">{section.fields.map(render)}</div>
      </div>
      {editable ? (
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line bg-surface-2 px-5 py-3.5 sm:px-7">
          <SaveIndicator dirty={dirty} saving={saving} savedAt={savedAt} className="mr-auto" />
          <Button type="button" variant="secondary" onClick={submit(false)} disabled={saving}>
            Save section
          </Button>
          <Button type="submit" loading={saving}>
            {continueLabel ?? (isLast ? 'Save and review' : 'Save and continue')}
          </Button>
        </div>
      ) : null}
    </form>
  )
})
