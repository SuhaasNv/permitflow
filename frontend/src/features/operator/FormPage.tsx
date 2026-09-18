import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useBlocker, useNavigate, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { Button } from '@/features/shared/Button'
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
        <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
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

  const steps: Step[] = [
    ...sections.map((s, i) => {
      const st = view.sections.find((v) => v.key === s.key)
      const short = s.title.split(' ')[0] ?? s.title
      return {
        label: short,
        to: `${base}/form/${s.key}`,
        state: i === activeIndex ? 'current' : st?.complete ? 'done' : st?.started ? 'attention' : 'todo',
      } as Step
    }),
    {
      label: 'Documents',
      to: `${base}/documents`,
      state:
        view.completeness.documents_present === view.completeness.documents_total
          ? 'done'
          : view.completeness.documents_present > 0
            ? 'attention'
            : 'todo',
    },
    { label: 'Review', to: `${base}/review`, state: 'todo' },
  ]

  const save = async (payload: Record<string, unknown>, andContinue: boolean) => {
    await update.mutateAsync({ key: section.key, data: payload })
    dirtyRef.current = false
    setUnsaved(false)
    setSavedAt(Date.now())
    if (andContinue) {
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

      <div className="mb-6">
        <Stepper steps={steps} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[232px_minmax(0,1fr)]">
        <aside className="hidden flex-col gap-4 lg:flex">
          <nav aria-label="Form sections" className="flex flex-col gap-0.5">
            <div className="pf-eyebrow px-3 pb-2">Sections</div>
            {sections.map((s, i) => {
              const st = view.sections.find((v) => v.key === s.key)
              const active = s.key === activeKey
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
                  <span
                    className={cn(
                      'h-2 w-2 shrink-0 rounded-full transition-colors duration-[var(--dur-base)]',
                      st?.complete ? 'bg-success' : st?.started ? 'bg-warning' : 'border border-line-strong bg-surface',
                    )}
                    aria-label={st?.complete ? 'Complete' : st?.started ? 'Needs attention' : 'Not started'}
                    role="img"
                  />
                </Link>
              )
            })}
            <div className="mx-3 my-2 h-px bg-line" />
            <Link
              to={`${base}/documents`}
              className="flex h-10 items-center gap-3 rounded-md px-3 text-sm font-medium text-text-2 no-underline transition-colors hover:bg-neutral-soft hover:text-text"
            >
              <span className="w-5 font-mono text-xs text-text-3">05</span>
              <span className="min-w-0 flex-1">Documents</span>
              <span className="text-xs tabular-nums text-text-3">
                {view.completeness.documents_present}/{view.completeness.documents_total}
              </span>
            </Link>
          </nav>
          <div className="px-3 text-xs leading-[18px] text-text-3">
            Drafts are saved on the server. You can leave and come back to this application at any time.
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
