import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import type { Checklist, ChecklistItem, ChecklistItemInput, ChecklistResult } from '@/api/checklist'
import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Breadcrumb } from '@/features/shared/Breadcrumb'
import { Button, buttonClasses } from '@/features/shared/Button'
import { CheckboxField, TextAreaField } from '@/features/shared/Controls'
import { Dialog } from '@/features/shared/Dialog'
import { SaveIndicator } from '@/features/shared/SaveIndicator'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { useToast } from '@/features/shared/Toast'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'
import { guardUnload, setUnsaved } from '@/lib/unsaved'
import { useChecklist, useChecklistSchema, useOfficerApplication, useSaveChecklist, useSubmitChecklist } from './queries'

const RESULTS: { value: ChecklistResult; label: string; on: string }[] = [
  { value: 'satisfactory', label: 'Satisfactory', on: 'border-success-line bg-success-soft text-success' },
  { value: 'unsatisfactory', label: 'Unsatisfactory', on: 'border-error-line bg-error-soft text-error' },
  { value: 'not_applicable', label: 'Not applicable', on: 'border-line-strong bg-surface-2 text-text' },
]

/** True while the viewport matches `query`; below 1100 px the result buttons stretch across the row. */
function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (notify) => {
      const mq = window.matchMedia(query)
      mq.addEventListener('change', notify)
      return () => mq.removeEventListener('change', notify)
    },
    () => window.matchMedia(query).matches,
    () => false,
  )
}

/** True while the browser reports a connection; the page holds its entries until it returns (US-061). */
function useOnline(): boolean {
  return useSyncExternalStore(
    (notify) => {
      window.addEventListener('online', notify)
      window.addEventListener('offline', notify)
      return () => {
        window.removeEventListener('online', notify)
        window.removeEventListener('offline', notify)
      }
    },
    () => navigator.onLine,
    () => true,
  )
}

/** Autosave waits this long after the last touch; a blur or Save draft goes at once. */
export const AUTOSAVE_DELAY_MS = 1500
/** A failed save is tried again after 3 s, then 6, 12 and 24 s, then every 30 s. */
export function retryDelay(attempt: number): number {
  return Math.min(3000 * 2 ** Math.max(0, attempt - 1), 30_000)
}

/** Their saved copy with my touched items on top: nothing typed here is thrown away (US-061). */
export function mergeFindings(theirs: Findings, mine: Findings, touched: Iterable<string>): Findings {
  const out = { ...theirs }
  for (const key of touched) if (mine[key]) out[key] = mine[key]
  return out
}

/** Local working copy of the item findings, keyed by item key. */
export type Findings = Record<string, { result: ChecklistResult; comment: string; needs_clarification: boolean }>

export function findingsOf(items: ChecklistItem[]): Findings {
  const out: Findings = {}
  for (const i of items) out[i.key] = { result: i.result, comment: i.comment ?? '', needs_clarification: i.needs_clarification }
  return out
}

export function toInput(findings: Findings): ChecklistItemInput[] {
  return Object.entries(findings).map(([key, f]) => ({
    key,
    result: f.result,
    comment: f.comment.trim() || null,
    needs_clarification: f.needs_clarification,
  }))
}

/** Counts and the sentence the sticky card shows, computed on the working copy so they move as you type. */
export function summarise(findings: Findings): {
  assessed: number
  flagged: number
  missing: number
  total: number
  remaining: string | null
} {
  const values = Object.values(findings)
  const total = values.length
  const assessed = values.filter((f) => f.result !== 'not_assessed').length
  const flagged = values.filter((f) => f.needs_clarification).length
  const missing = values.filter((f) => (f.result === 'unsatisfactory' || f.needs_clarification) && !f.comment.trim()).length
  const parts: string[] = []
  const left = total - assessed
  if (left) parts.push(`assess ${left} more ${left === 1 ? 'item' : 'items'}`)
  if (missing) parts.push(`add ${missing} ${missing === 1 ? 'comment' : 'comments'}`)
  const remaining = parts.length ? parts.join(' and ').replace(/^./, (c) => c.toUpperCase()) + ' to submit.' : null
  return { assessed, flagged, missing, total, remaining }
}

function ResultControl({
  value,
  onChange,
  disabled,
  compact,
}: {
  value: ChecklistResult
  onChange: (r: ChecklistResult) => void
  disabled?: boolean
  compact: boolean
}) {
  return (
    <div className="flex flex-wrap gap-2" role="group" aria-label="Result">
      {RESULTS.map((r) => {
        const on = r.value === value
        return (
          <button
            key={r.value}
            type="button"
            aria-pressed={on}
            disabled={disabled}
            // Pressing the selected result again clears it back to Not assessed.
            onClick={() => onChange(on ? 'not_assessed' : r.value)}
            className={cn(
              'inline-flex h-11 items-center justify-center gap-2 rounded-md border px-3.5 text-sm',
              'transition-[border-color,background-color,color] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
              'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgba(23,92,211,0.2)] disabled:cursor-not-allowed',
              compact && 'flex-1',
              on ? cn('font-semibold', r.on) : 'border-line-strong bg-surface font-medium text-text-2 hover:border-text-3',
            )}
          >
            <span className={cn('h-2 w-2 shrink-0 rounded-full', on ? 'bg-current' : 'bg-line-strong')} aria-hidden="true" />
            {r.label}
          </button>
        )
      })}
    </div>
  )
}

/** S-30: the checklist as the officer fills it on site. Tablet first (820 portrait and 1024), one item after another,
 * a result per item, a comment when one is needed, a flag for the operator. The draft autosaves 1.5 s after the last
 * touch and on blur, retries with backoff when a save fails, holds its entries while offline, and merges another tab's
 * save under the officer's own (US-061). The submit arrives with US-063. */
export function ChecklistPage() {
  const { id = '' } = useParams()
  const app = useOfficerApplication(id)
  const schema = useChecklistSchema()
  const checklist = useChecklist(id)
  const save = useSaveChecklist(id)
  const submit = useSubmitChecklist(id)
  const navigate = useNavigate()
  const toast = useToast()
  const [confirming, setConfirming] = useState(false)
  // The working copy is the server draft until the officer touches it, then the officer's edits only.
  // State renders; the refs beside it are written synchronously in the handlers so a timer or a blur
  // that fires between two fast taps reads what was tapped, never what was last committed.
  const [edits, setEdits] = useState<Findings | null>(null)
  const [savedAt, setSavedAt] = useState<number | null>(null)
  const [dirty, setDirty] = useState(false)
  const [retrying, setRetrying] = useState(false)
  const [merged, setMerged] = useState<number | null>(null)
  const compact = useMediaQuery('(max-width: 1099px)')
  const online = useOnline()
  const timer = useRef<number | null>(null)
  const attempt = useRef(0)
  const touched = useRef<Set<string>>(new Set())
  const work = useRef<Findings | null>(null) // the edits, synchronous
  const server = useRef<Checklist | null>(null) // the last draft the server sent
  const versionRef = useRef<number | null>(null) // the version the next save is based on
  const dirtyRef = useRef(false)
  const inFlight = useRef(false)
  // One id per attempt at the same batch of entries: a retry reuses it, so a save whose reply was lost
  // answers with the state instead of a conflict; a new touch starts a new batch.
  const saveId = useRef<string | null>(null)

  useEffect(() => guardUnload(), [])
  useEffect(
    () => () => {
      setUnsaved(false)
      if (timer.current !== null) window.clearTimeout(timer.current)
    },
    [],
  )
  useEffect(() => {
    if (checklist.data) {
      server.current = checklist.data
      if (versionRef.current === null) versionRef.current = checklist.data.version
    }
  }, [checklist.data])

  const findings = useMemo(() => edits ?? (checklist.data ? findingsOf(checklist.data.items) : null), [edits, checklist.data])
  const summary = useMemo(() => (findings ? summarise(findings) : null), [findings])

  const setVersion = (v: number) => {
    versionRef.current = v
  }
  const markDirty = (value: boolean) => {
    dirtyRef.current = value
    setDirty(value)
    setUnsaved(value)
  }
  const current = (): Findings | null => work.current ?? (server.current ? findingsOf(server.current.items) : null)

  // Plain functions on purpose: everything they read lives in refs written by the handlers.
  const schedule = (delay: number) => {
    if (timer.current !== null) window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      timer.current = null
      flush()
    }, delay)
  }
  const flush = () => {
    const items = current()
    const version = versionRef.current
    if (!items || version === null || !dirtyRef.current || inFlight.current) return
    if (!navigator.onLine) return // the online event schedules the save
    const sent = new Set(touched.current)
    inFlight.current = true
    saveId.current ??= crypto.randomUUID()
    save.mutate(
      { items: toInput(items), version, save_id: saveId.current },
      {
        onSettled: () => {
          inFlight.current = false
        },
        onSuccess: (next) => {
          setVersion(next.version)
          setSavedAt(Date.now())
          setRetrying(false)
          attempt.current = 0
          saveId.current = null
          for (const key of sent) touched.current.delete(key)
          if (touched.current.size > 0) {
            // Touched again while the save was in flight: still dirty, save once more.
            schedule(AUTOSAVE_DELAY_MS)
          } else {
            markDirty(false)
          }
        },
        onError: (e) => {
          if (e instanceof AppError && e.status === 409 && e.code === 'version_conflict') {
            const theirs = e.details?.current
            if (theirs && typeof theirs === 'object') {
              const other = theirs as Checklist
              const mergedCopy = mergeFindings(findingsOf(other.items), current() ?? {}, touched.current)
              work.current = mergedCopy
              setEdits(mergedCopy)
              setVersion(other.version)
              setMerged(touched.current.size)
              schedule(0)
            }
            return
          }
          if (e instanceof AppError && (e.status === 409 || e.status === 422)) {
            // Submitted elsewhere, or a state the draft cannot be saved in: stop the autosave loop and
            // reload so the page shows what stands (read-only once submitted).
            toast.push({ title: 'Could not save the checklist', body: e.message, tone: 'error' })
            saveId.current = null
            markDirty(false)
            void checklist.refetch()
            return
          }
          // Network or server trouble: keep the entries and try again with backoff.
          attempt.current += 1
          setRetrying(true)
          schedule(retryDelay(attempt.current))
        },
      },
    )
  }

  // Back online with unsaved entries: save at once.
  const wasOnline = useRef(true)
  useEffect(() => {
    if (online && !wasOnline.current && dirtyRef.current) schedule(0)
    wasOnline.current = online
    // eslint-disable-next-line react-hooks/exhaustive-deps -- schedule is a plain function reading refs
  }, [online])

  if (checklist.isError) {
    const e = checklist.error
    if (e instanceof AppError && e.status === 404) return <NotFoundPanel backTo="/officer/queue" backLabel="Back to the queue" />
    if (e instanceof AppError && e.status === 409)
      return (
        <div className="mx-auto max-w-[640px]">
          <Alert
            tone="warning"
            title="The checklist opens once a site visit is scheduled"
            action={
              <Link to={`/officer/applications/${id}`} className={buttonClasses('secondary', 'sm')}>
                Back to the case
              </Link>
            }
          >
            {e.message}
          </Alert>
        </div>
      )
    return <ErrorPanel error={e} onRetry={() => void checklist.refetch()} />
  }
  if (app.isError && app.data === undefined) return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  if (schema.isError) return <ErrorPanel error={schema.error} onRetry={() => void schema.refetch()} />
  if (!app.data || !schema.data || !checklist.data || findings === null || summary === null) {
    return (
      <PageSkeleton label="Loading checklist">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="mt-6 h-[480px]" />
      </PageSkeleton>
    )
  }
  const view = app.data
  const draft = checklist.data
  const sections = schema.data.sections
  const readOnly = draft.status === 'submitted'

  const doSubmit = () => {
    submit.mutate(undefined, {
      onSuccess: () => {
        setConfirming(false)
        markDirty(false)
        toast.push({
          title: 'Checklist submitted',
          body:
            summary.flagged > 0
              ? `The operator has been asked about ${summary.flagged} ${summary.flagged === 1 ? 'item' : 'items'}.`
              : 'Nothing was flagged. The case can be routed to approval.',
          tone: 'success',
        })
        navigate(`/officer/applications/${id}`)
      },
      onError: (e) => {
        setConfirming(false)
        if (e instanceof AppError && e.status === 422) {
          const keys = e.details?.items
          const first = Array.isArray(keys) && typeof keys[0] === 'string' ? keys[0] : null
          if (first) document.getElementById(`item-${first}`)?.scrollIntoView({ block: 'center' })
        }
        toast.push({ title: 'Could not submit the checklist', body: e.message, tone: 'error' })
      },
    })
  }
  const flaggedTitles = sections
    .flatMap((s) => s.items)
    .filter((i) => findings[i.key]?.needs_clarification)
    .map((i) => i.title)
  const update = (key: string, patch: Partial<Findings[string]>) => {
    // Two taps in one frame must both land (a tablet taps faster than React commits): the ref is the truth.
    const base = current() ?? findings
    const next = { ...base, [key]: { ...base[key], ...patch } }
    work.current = next
    if (!inFlight.current) saveId.current = null // a new batch of entries gets its own id
    setEdits(next)
    touched.current.add(key)
    markDirty(true)
    schedule(AUTOSAVE_DELAY_MS)
  }
  const numbering = new Map(sections.flatMap((s) => s.items).map((i, idx) => [i.key, idx + 1]))
  return (
    <>
      <Breadcrumb
        items={[
          { label: 'Review queue', to: '/officer/queue' },
          { label: view.reference_no, to: `/officer/applications/${id}` },
          { label: 'Site visit checklist' },
        ]}
      />
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <span className="font-mono text-[13px] font-medium tracking-[0.02em] text-text-2">{view.reference_no}</span>
            <span className="text-line-strong" aria-hidden="true">
              ·
            </span>
            <span className="text-[13px] text-text-2">{view.licence_title}</span>
          </div>
          <h1 className="mt-1.5 text-[28px] font-semibold leading-9 tracking-[-0.015em]">Site visit checklist</h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
            <StatusBadge label={view.status_label} tone={view.status_tone} size="lg" />
            <span className="text-sm text-text-2">
              {view.business_name ?? 'Business name not entered'}
              {view.premises_summary ? `, ${view.premises_summary}` : ''}. Visit {draft.visit_no}
              {view.site_visit ? `, ${view.site_visit.when}` : ''}.
              {readOnly ? ' The findings are final.' : ' Fill the checklist on site; press Save draft as you go.'}
            </span>
          </div>
          <div className="mt-2 text-[13px] text-text-3">
            {readOnly
              ? `Submitted by ${draft.submitted_by ?? ''} on ${draft.submitted_at ? formatDateTime(draft.submitted_at) : ''}`
              : `Draft, not submitted${draft.version > 1 && draft.updated_at ? ` · last saved ${formatDateTime(draft.updated_at)}` : ''}`}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-3">
          {!readOnly ? <SaveIndicator dirty={dirty} saving={save.isPending} savedAt={savedAt} retrying={retrying} /> : null}
          <Link to={`/officer/applications/${id}`} className={buttonClasses('secondary', 'sm')}>
            Back to the case
          </Link>
        </div>
      </div>

      {!online && !readOnly ? (
        <div className="mb-5">
          <Alert tone="warning" title="You are offline: changes will not save until you reconnect">
            Keep this page open. Your entries stay here and are saved when the connection returns.
          </Alert>
        </div>
      ) : null}
      {merged !== null ? (
        <div className="mb-5">
          <Alert
            tone="info"
            title="Another tab or device saved this checklist"
            action={
              <Button variant="ghost" size="sm" onClick={() => setMerged(null)}>
                Dismiss
              </Button>
            }
          >
            Their version was taken and your entries on {merged} {merged === 1 ? 'item were' : 'items were'} kept on top of it, then saved.
            Check the items you did not touch.
          </Alert>
        </div>
      ) : null}

      <nav aria-label="Sections" className="mb-4 flex flex-wrap gap-1.5">
        {sections.map((s) => {
          const done = s.items.filter((i) => findings[i.key]?.result !== 'not_assessed').length
          const complete = done === s.items.length
          return (
            <a
              key={s.key}
              href={`#section-${s.key}`}
              className={cn(
                'inline-flex h-9 items-center gap-2 rounded-full border px-3 text-[13px] font-medium no-underline transition-colors duration-[var(--dur-fast)]',
                complete ? 'border-success-line bg-success-soft text-success' : 'border-line-strong bg-surface text-text-2 hover:text-text',
              )}
            >
              {s.title}
              <span className="font-mono text-xs">
                {done} of {s.items.length}
              </span>
            </a>
          )
        })}
      </nav>
      <div className="mb-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <span className="text-sm font-semibold">
            {summary.assessed} of {summary.total} assessed, {summary.flagged} flagged
          </span>
          {summary.missing ? (
            <span className="text-[13px] text-error">
              {summary.missing} {summary.missing === 1 ? 'comment' : 'comments'} missing
            </span>
          ) : null}
        </div>
        <div
          className="h-1.5 overflow-hidden rounded-full bg-surface-3"
          role="progressbar"
          aria-valuenow={summary.assessed}
          aria-valuemin={0}
          aria-valuemax={summary.total}
          aria-label="Items assessed"
        >
          <div
            className="h-full rounded-full bg-info transition-[width] duration-[600ms]"
            style={{ width: `${(summary.assessed / summary.total) * 100}%` }}
          />
        </div>
      </div>

      <div
        className="pf-surface px-5"
        onBlur={(e) => {
          // Leaving the list saves at once; moving between fields inside it waits for the debounce.
          if (!readOnly && dirtyRef.current && !e.currentTarget.contains(e.relatedTarget)) schedule(0)
        }}
      >
        {sections.map((s) => (
          <section key={s.key} id={`section-${s.key}`} className="scroll-mt-24" aria-labelledby={`section-${s.key}-title`}>
            <div className="pb-1 pt-5">
              <h2 id={`section-${s.key}-title`} className="text-[17px] font-semibold leading-6">
                {s.title}
              </h2>
              <span className="text-xs text-text-3">
                {s.items.length} {s.items.length === 1 ? 'item' : 'items'}
              </span>
            </div>
            <ol>
              {s.items.map((def) => {
                const n = numbering.get(def.key) ?? 0
                const f = findings[def.key]
                if (!f) return null
                const needsComment = f.result === 'unsatisfactory' || f.needs_clarification
                const showComment = needsComment || f.comment.trim().length > 0
                const commentMissing = needsComment && !f.comment.trim()
                return (
                  <li
                    key={def.key}
                    id={`item-${def.key}`}
                    className="flex scroll-mt-24 flex-col gap-3.5 border-b border-line py-5 last:border-b-0"
                  >
                    <div className="flex items-start gap-3">
                      <span className="font-mono text-[13px] leading-6 text-text-3">{String(n).padStart(2, '0')}</span>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-base font-semibold leading-6">{def.title}</h3>
                        {def.guidance ? <p className="text-[13px] leading-5 text-text-3">{def.guidance}</p> : null}
                      </div>
                      {f.result === 'not_assessed' ? <StatusBadge label="Not assessed" tone="neutral" /> : null}
                    </div>
                    <div className={cn('flex flex-col gap-3', !compact && 'pl-[34px]')}>
                      <ResultControl
                        value={f.result}
                        disabled={readOnly}
                        compact={compact}
                        onChange={(r) => update(def.key, { result: r })}
                      />
                      <CheckboxField
                        label="Need further clarification"
                        checked={f.needs_clarification}
                        disabled={readOnly}
                        onChange={(e) => update(def.key, { needs_clarification: e.target.checked })}
                      />
                      {showComment ? (
                        <TextAreaField
                          label="Comment"
                          required={needsComment}
                          value={f.comment}
                          readOnly={readOnly}
                          maxLength={2000}
                          error={commentMissing ? 'A comment is required for an unsatisfactory or flagged item.' : undefined}
                          help={f.needs_clarification ? 'The operator reads this when the item is flagged.' : undefined}
                          onChange={(e) => update(def.key, { comment: e.target.value })}
                        />
                      ) : null}
                    </div>
                  </li>
                )
              })}
            </ol>
          </section>
        ))}
      </div>

      {!readOnly ? (
        <div className="sticky bottom-0 mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface px-5 py-3.5 shadow-[0_-8px_24px_rgba(27,36,48,0.06)] max-lg:bottom-[64px]">
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold">
              {summary.assessed} of {summary.total} assessed, {summary.flagged} flagged
            </span>
            <span className="text-[13px] text-text-2">{summary.remaining ?? 'Everything is assessed. Submit when you are ready.'}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" loading={save.isPending} disabled={!dirty} onClick={() => schedule(0)}>
              Save draft
            </Button>
            <Button
              disabled={summary.remaining !== null || dirty || save.isPending}
              title={summary.remaining ?? (dirty || save.isPending ? 'Wait for the draft to save.' : undefined)}
              onClick={() => setConfirming(true)}
            >
              {view.status === 'site_visit_done' ? 'Submit checklist' : 'Mark visit done and submit'}
            </Button>
          </div>
        </div>
      ) : null}
      <Dialog
        open={confirming}
        title={view.status === 'site_visit_done' ? 'Submit the checklist?' : 'Mark the visit done and submit the checklist?'}
        confirmLabel="Submit"
        busy={submit.isPending}
        onConfirm={doSubmit}
        onCancel={() => setConfirming(false)}
      >
        <p>
          The findings become final and the case moves on.{' '}
          {flaggedTitles.length > 0
            ? `The operator is asked about ${flaggedTitles.length} flagged ${flaggedTitles.length === 1 ? 'item' : 'items'} and reads your comment on each:`
            : 'Nothing is flagged: the operator is told the visit is recorded and you can route the case to approval.'}
        </p>
        {flaggedTitles.length > 0 ? (
          <ul className="list-disc pl-5">
            {flaggedTitles.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        ) : null}
        <p className="text-text-3">
          {summary.assessed} items assessed: {summary.total - Object.values(findings).filter((f) => f.result !== 'satisfactory').length}{' '}
          satisfactory, {Object.values(findings).filter((f) => f.result === 'unsatisfactory').length} unsatisfactory,{' '}
          {Object.values(findings).filter((f) => f.result === 'not_applicable').length} not applicable.
        </p>
      </Dialog>
    </>
  )
}
