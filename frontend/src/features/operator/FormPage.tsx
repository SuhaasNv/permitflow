import { useCallback, useRef } from 'react'
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { Dialog } from '@/features/shared/Dialog'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { SectionForm } from './SectionForm'
import { useApplication, useFormSchema, useUpdateSection } from './queries'

const STEPS = ['Business', 'Premises', 'Operations', 'Declarations', 'Documents', 'Review']

function Stepper({ current }: { current: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-y-2 text-[13px]" aria-label="Application steps">
      {STEPS.map((label, i) => {
        const state = i < current ? 'done' : i === current ? 'current' : 'todo'
        return (
          <li key={label} className="flex items-center">
            <span
              className={cn(
                'flex items-center gap-2 whitespace-nowrap font-medium',
                state === 'current' ? 'text-primary' : state === 'done' ? 'text-text-2' : 'text-text-3',
              )}
              aria-current={state === 'current' ? 'step' : undefined}
            >
              <span
                className={cn(
                  'flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold',
                  state === 'done' && 'border-success bg-success text-white',
                  state === 'current' && 'border-primary bg-primary text-white',
                  state === 'todo' && 'border-line-strong bg-surface',
                )}
              >
                {state === 'done' ? '✓' : i + 1}
              </span>
              {label}
            </span>
            {i < STEPS.length - 1 ? (
              <span className={cn('mx-2 h-px w-7', state === 'done' ? 'bg-success' : 'bg-line-strong')} aria-hidden="true" />
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}

export function FormPage() {
  const { id = '', sectionKey } = useParams()
  const navigate = useNavigate()
  const app = useApplication(id)
  const schema = useFormSchema()
  const update = useUpdateSection(id)
  // A ref, not state: the blocker must see "clean" synchronously right after a successful save.
  const dirtyRef = useRef(false)
  const onDirtyChange = useCallback((d: boolean) => {
    dirtyRef.current = d
  }, [])

  const blocker = useBlocker(({ currentLocation, nextLocation }) => dirtyRef.current && currentLocation.pathname !== nextLocation.pathname)

  if (app.isPending || schema.isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading form">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  if (schema.isError) return <ErrorPanel error={schema.error} onRetry={() => void schema.refetch()} />

  const view = app.data
  const sections = schema.data.sections
  const activeKey =
    sectionKey && sections.some((s) => s.key === sectionKey)
      ? sectionKey
      : (view.sections.find((s) => !s.complete)?.key ?? sections[0]?.key ?? '')
  const activeIndex = sections.findIndex((s) => s.key === activeKey)
  const section = sections[activeIndex]
  const state = view.sections.find((s) => s.key === activeKey)
  if (!section || !state) return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
  const isLast = activeIndex === sections.length - 1

  const save = async (payload: Record<string, unknown>, andContinue: boolean) => {
    await update.mutateAsync({ key: section.key, data: payload })
    dirtyRef.current = false
    if (andContinue) {
      const next = sections[activeIndex + 1]
      navigate(next ? `/app/applications/${id}/form/${next.key}` : `/app/applications/${id}/documents`)
    }
  }

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-2 text-[13px] text-text-3">
        <Link to="/app/dashboard" className="text-text-2">
          My applications
        </Link>
        <span aria-hidden="true">›</span>
        <span className="text-text">{view.reference_no}</span>
      </nav>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="truncate text-[26px] font-semibold leading-8 tracking-tight">
            {view.reference_no} · {view.licence_title}
          </h1>
          <p className="mt-1 text-text-2">
            {view.sections[0]?.data.business_name ? String(view.sections[0].data.business_name) : 'New application'}
          </p>
        </div>
        <Link
          to={`/app/applications/${id}`}
          className="inline-flex h-10 items-center rounded-md border border-line-strong bg-surface px-4 text-sm font-semibold text-text no-underline shadow-[var(--shadow-1)] hover:bg-surface-2"
        >
          Save and exit
        </Link>
      </div>

      <div className="rounded-t-lg border border-line bg-surface px-5 py-3.5 shadow-[var(--shadow-1)]">
        <div className="flex flex-wrap items-center gap-4">
          <StatusBadge label={view.status_label} tone={view.status_tone} size="lg" />
          <span className="text-sm text-text-2">{view.status_explanation}</span>
          <span className="ml-auto whitespace-nowrap text-xs tabular-nums text-text-3">
            Step {activeIndex + 1} of {STEPS.length}
          </span>
        </div>
      </div>
      <div className="mb-5 rounded-b-lg border border-t-0 border-line bg-surface-2 px-5 py-2.5">
        <Stepper current={activeIndex} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="flex flex-col gap-4">
          <nav aria-label="Form sections" className="rounded-lg border border-line bg-surface p-2">
            {sections.map((s) => {
              const st = view.sections.find((v) => v.key === s.key)
              const active = s.key === activeKey
              return (
                <Link
                  key={s.key}
                  to={`/app/applications/${id}/form/${s.key}`}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'flex items-center gap-2.5 rounded-md px-2.5 py-[9px] text-sm font-medium text-text-2 no-underline hover:bg-neutral-soft hover:text-text',
                    active && 'bg-neutral-soft font-semibold text-text shadow-[inset_3px_0_0_var(--color-primary)]',
                  )}
                >
                  <span>{s.title}</span>
                  <span
                    className={cn(
                      'ml-auto flex h-[18px] w-[18px] items-center justify-center rounded-full text-[11px]',
                      st?.complete
                        ? 'bg-success text-white'
                        : st?.started
                          ? 'bg-error text-white'
                          : 'border-[1.5px] border-line-strong bg-surface',
                    )}
                    aria-label={st?.complete ? 'Complete' : st?.started ? 'Needs attention' : 'Not started'}
                  >
                    {st?.complete ? '✓' : st?.started ? '!' : ''}
                  </span>
                </Link>
              )
            })}
            <div className="mx-1 my-1.5 h-px bg-line" />
            <Link
              to={`/app/applications/${id}/documents`}
              className="flex items-center gap-2.5 rounded-md px-2.5 py-[9px] text-sm font-medium text-text-2 no-underline hover:bg-neutral-soft hover:text-text"
            >
              Documents
              <span className="ml-auto text-xs text-text-3">
                {view.completeness.documents_present}/{view.completeness.documents_total}
              </span>
            </Link>
          </nav>
          <p className="px-1 text-xs leading-[18px] text-text-3">
            {view.completeness.sections_complete} of {view.completeness.sections_total} sections complete ·{' '}
            {view.completeness.documents_present} of {view.completeness.documents_total} documents uploaded
          </p>
        </aside>
        <SectionForm
          section={section}
          data={state.data}
          editable={state.editable}
          saving={update.isPending}
          isLast={isLast}
          onSave={save}
          onDirtyChange={onDirtyChange}
        />
      </div>

      <Dialog
        open={blocker.state === 'blocked'}
        title="Leave without saving?"
        confirmLabel="Leave"
        cancelLabel="Stay"
        danger
        onConfirm={() => blocker.proceed?.()}
        onCancel={() => blocker.reset?.()}
      >
        <p>Changes you made in this section have not been saved. If you leave now they will be lost.</p>
      </Dialog>
    </>
  )
}
