import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Button, buttonClasses } from '@/features/shared/Button'
import { Dialog } from '@/features/shared/Dialog'
import { Stepper } from '@/features/shared/Stepper'
import type { Step } from '@/features/shared/Stepper'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { guardUnload, setUnsaved } from '@/lib/unsaved'
import { ApplicationHeader } from './ApplicationHeader'
import { SectionForm } from './SectionForm'
import type { SectionFormHandle } from './SectionForm'
import { useApplication, useFormSchema, useUpdateSection } from './queries'
import { nextRespondTarget } from './respond'

export function FormPage() {
  const { id = '', sectionKey } = useParams()
  const navigate = useNavigate()
  const app = useApplication(id)
  const schema = useFormSchema()
  const update = useUpdateSection(id)
  const [savedAt, setSavedAt] = useState<number | null>(null)
  const [exiting, setExiting] = useState(false)
  const formRef = useRef<SectionFormHandle>(null)
  // A ref, not state: the blocker must see "clean" synchronously right after a successful save.
  const dirtyRef = useRef(false)
  const onDirtyChange = useCallback((d: boolean) => {
    dirtyRef.current = d
    setUnsaved(d)
  }, [])

  // Refresh, tab close or an external link while dirty: the browser asks first. Cleared on unmount.
  useEffect(() => {
    const stop = guardUnload()
    return () => {
      stop()
      setUnsaved(false)
    }
  }, [])

  const blocker = useBlocker(({ currentLocation, nextLocation }) => dirtyRef.current && currentLocation.pathname !== nextLocation.pathname)

  if (app.isPending || schema.isPending) {
    return (
      <PageSkeleton label="Loading form">
        <Skeleton className="h-16" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
          <Skeleton className="h-56" />
          <Skeleton className="h-96" />
        </div>
      </PageSkeleton>
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
  const base = `/app/applications/${id}`
  // Responding to feedback: only flagged targets are editable; "continue" walks them and ends at Resubmit.
  const responding = view.resubmit !== null
  const flaggedSections = view.sections.filter((s) => s.editable).map((s) => s.key)
  const docsFlagged = view.document_slots.some((d) => d.editable)
  const changedSections = view.resubmit?.changed_sections ?? []
  const nextTarget = responding
    ? nextRespondTarget({ sectionKeys: sections.map((s) => s.key), activeKey, flaggedSections, docsFlagged })
    : null
  const flaggedTotal = flaggedSections.length + (docsFlagged ? 1 : 0)
  const changedTotal = changedSections.length + (view.resubmit?.changed_document_types.length ? 1 : 0)

  const steps: Step[] = [
    ...sections.map((s, i) => {
      const st = view.sections.find((v) => v.key === s.key)
      const short = s.title.split(' ')[0] ?? s.title
      const state: Step['state'] =
        i === activeIndex
          ? 'current'
          : responding
            ? st?.editable
              ? changedSections.includes(s.key)
                ? 'done'
                : 'attention'
              : 'locked'
            : st?.complete
              ? 'done'
              : st?.started
                ? 'attention'
                : 'todo'
      return { label: short, to: `${base}/form/${s.key}`, state }
    }),
    {
      label: 'Documents',
      to: `${base}/documents`,
      state: responding
        ? docsFlagged
          ? view.resubmit?.changed_document_types.length
            ? 'done'
            : 'attention'
          : 'locked'
        : view.completeness.documents_present === view.completeness.documents_total
          ? 'done'
          : view.completeness.documents_present > 0
            ? 'attention'
            : 'todo',
    },
    responding ? { label: 'Resubmit', to: base, state: 'attention' } : { label: 'Review', to: `${base}/review`, state: 'todo' },
  ]

  const save = async (payload: Record<string, unknown>, andContinue: boolean) => {
    await update.mutateAsync({ key: section.key, data: payload })
    dirtyRef.current = false
    setUnsaved(false)
    setSavedAt(Date.now())
    if (andContinue) {
      if (nextTarget) {
        navigate(
          nextTarget.kind === 'section' ? `${base}/form/${nextTarget.key}` : nextTarget.kind === 'documents' ? `${base}/documents` : base,
        )
        return
      }
      const next = sections[activeIndex + 1]
      navigate(next ? `${base}/form/${next.key}` : `${base}/documents`)
    }
  }

  return (
    <>
      <ApplicationHeader
        view={view}
        crumb={section.title}
        aside={
          <span>
            · Step {activeIndex + 1} of {steps.length}
          </span>
        }
        actions={
          <Button
            variant="secondary"
            loading={exiting}
            onClick={async () => {
              // Saves the draft first (partial values allowed), then leaves. Validation errors keep you here.
              if (!dirtyRef.current) {
                navigate(base)
                return
              }
              setExiting(true)
              try {
                const ok = await formRef.current?.saveDraft()
                if (ok) navigate(base)
              } finally {
                setExiting(false)
              }
            }}
          >
            Save and exit
          </Button>
        }
      />

      {responding ? (
        <div className="mb-5">
          <Alert
            tone={view.resubmit?.can_resubmit ? 'success' : 'warning'}
            title={
              view.resubmit?.can_resubmit
                ? `Ready to resubmit: ${changedTotal} of ${flaggedTotal} flagged ${flaggedTotal === 1 ? 'item' : 'items'} changed.`
                : `Responding to feedback: ${flaggedTotal} flagged ${flaggedTotal === 1 ? 'item needs' : 'items need'} your changes.`
            }
            action={
              <Link to={base} className={buttonClasses('secondary', 'sm')}>
                {view.resubmit?.can_resubmit ? 'Go to resubmit' : 'Back to application'}
              </Link>
            }
          >
            Only the flagged sections and documents can be changed. Everything else is kept as submitted. Your changes are sent back when
            you press Resubmit on the application page.
          </Alert>
        </div>
      ) : null}
      <div className="mb-6">
        <Stepper steps={steps} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[232px_minmax(0,1fr)]">
        <aside className="hidden flex-col gap-4 lg:flex">
          <nav aria-label="Form sections" className="flex flex-col gap-0.5">
            <div className="pf-eyebrow px-3 pb-2">Sections</div>
            {sections.map((s, i) => {
              const st = view.sections.find((v) => v.key === s.key)
              const active = s.key === activeKey
              const locked = responding && !st?.editable
              const mark: { tone: string; label: string } = responding
                ? locked
                  ? { tone: 'border border-line-strong bg-surface-2', label: 'Locked' }
                  : changedSections.includes(s.key)
                    ? { tone: 'bg-success', label: 'Changed' }
                    : { tone: 'bg-warning', label: 'Flagged' }
                : st?.complete
                  ? { tone: 'bg-success', label: 'Complete' }
                  : st?.started
                    ? { tone: 'bg-warning', label: 'Needs attention' }
                    : { tone: 'border border-line-strong bg-surface', label: 'Not started' }
              if (locked) {
                return (
                  <span
                    key={s.key}
                    className="flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-text-3"
                    title="The licensing officer did not ask for changes here."
                  >
                    <span className="w-5 font-mono text-xs text-text-3">0{i + 1}</span>
                    <span className="min-w-0 flex-1 truncate">{s.title}</span>
                    <span className="text-[11px] font-medium uppercase tracking-[0.06em]">Locked</span>
                  </span>
                )
              }
              return (
                <Link
                  key={s.key}
                  to={`${base}/form/${s.key}`}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-text-2 no-underline',
                    'transition-[background-color,color] duration-[var(--dur-fast)] ease-[var(--ease-out)] hover:bg-neutral-soft hover:text-text',
                    active && 'bg-surface-3 font-semibold text-text',
                  )}
                >
                  <span className="w-5 font-mono text-xs text-text-3">0{i + 1}</span>
                  <span className="min-w-0 flex-1 truncate">{s.title}</span>
                  {responding ? (
                    <span className={cn('text-[11px] font-medium', mark.tone === 'bg-warning' ? 'text-warning' : 'text-success')}>
                      {mark.label}
                    </span>
                  ) : null}
                  <span
                    className={cn('h-2 w-2 shrink-0 rounded-full transition-colors duration-[var(--dur-base)]', mark.tone)}
                    aria-label={mark.label}
                    role="img"
                  />
                </Link>
              )
            })}
            <div className="mx-3 my-2 h-px bg-line" />
            {responding && !docsFlagged ? (
              <span
                className="flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-text-3"
                title="No document was flagged."
              >
                <span className="w-5 font-mono text-xs text-text-3">05</span>
                <span className="min-w-0 flex-1">Documents</span>
                <span className="text-[11px] font-medium uppercase tracking-[0.06em]">Locked</span>
              </span>
            ) : (
              <Link
                to={`${base}/documents`}
                className="flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-text-2 no-underline transition-colors hover:bg-neutral-soft hover:text-text"
              >
                <span className="w-5 font-mono text-xs text-text-3">05</span>
                <span className="min-w-0 flex-1">Documents</span>
                {responding ? (
                  <span
                    className={cn(
                      'text-[11px] font-medium',
                      view.resubmit?.changed_document_types.length ? 'text-success' : 'text-warning',
                    )}
                  >
                    {view.resubmit?.changed_document_types.length ? 'Changed' : 'Flagged'}
                  </span>
                ) : (
                  <span className="text-xs tabular-nums text-text-3">
                    {view.completeness.documents_present}/{view.completeness.documents_total}
                  </span>
                )}
              </Link>
            )}
          </nav>
          <div className="px-3 text-xs leading-[18px] text-text-3">
            {responding
              ? 'Only flagged items can be changed. Press Resubmit on the application page when you are done.'
              : 'Drafts are saved on the server. You can leave and come back to this application at any time.'}
          </div>
        </aside>
        <div key={section.key} className="pf-enter-fast min-w-0">
          <SectionForm
            ref={formRef}
            section={section}
            data={state.data}
            editable={state.editable}
            saving={update.isPending}
            savedAt={savedAt}
            isLast={isLast}
            continueLabel={
              nextTarget
                ? nextTarget.kind === 'section'
                  ? 'Save and continue'
                  : nextTarget.kind === 'documents'
                    ? 'Save and go to documents'
                    : 'Save and go to resubmit'
                : undefined
            }
            stepLabel={`Section ${activeIndex + 1} of ${sections.length}`}
            feedback={view.feedback.filter((f) => f.section_key === section.key)}
            lockedReason={
              !state.editable && view.resubmit ? 'The licensing officer did not ask for changes here. It is kept as submitted.' : undefined
            }
            onSave={save}
            onDirtyChange={onDirtyChange}
          />
        </div>
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
