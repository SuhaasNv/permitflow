import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { downloadDocument } from '@/api/documents'
import type { OfficerAction, OfficerApplication } from '@/api/officer'
import { useFormSchema } from '@/features/operator/queries'
import { displayValue } from '@/features/operator/SectionSummary'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { TextAreaField } from '@/features/shared/Controls'
import { Dialog } from '@/features/shared/Dialog'
import { Breadcrumb } from '@/features/shared/Breadcrumb'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { useToast } from '@/features/shared/Toast'
import { cn } from '@/lib/cn'
import { formatBytes, formatDate, formatDateTime, formatRelative } from '@/lib/format'
import { CheckResult } from './CheckResult'
import { ComparePanel } from './ComparePanel'
import { FeedbackPanel } from './FeedbackPanel'
import type { Target } from './FeedbackPanel'
import { useOfficerApplication, useRerunCheck, useTransition } from './queries'

const ACTION_COPY: Record<string, { title: string; body: string; confirm: string; danger?: boolean }> = {
  under_review: {
    title: 'Start reviewing this application?',
    body: 'The status becomes Under Review and the operator is told a review has started. You can add feedback while it is under review.',
    confirm: 'Start review',
  },
  pending_pre_site_resubmission: {
    title: 'Request a resubmission?',
    body: 'Your open feedback is released to the operator. Only the flagged sections and documents reopen for them.',
    confirm: 'Request resubmission',
  },
  site_visit_scheduled: {
    title: 'Schedule a site visit?',
    body: 'The operator is told an officer will contact them to arrange a visit.',
    confirm: 'Schedule site visit',
  },
  site_visit_done: {
    title: 'Mark the site visit as done?',
    body: 'The application moves on to the post-visit stage.',
    confirm: 'Mark done',
  },
  pending_approval: { title: 'Route to approval?', body: 'The application is marked ready for a decision.', confirm: 'Route to approval' },
  approved: { title: 'Approve this application?', body: 'This is final. The operator sees Approved and your note.', confirm: 'Approve' },
  rejected: {
    title: 'Reject this application?',
    body: 'This is final and cannot be undone. The operator sees Rejected and your note, which is required.',
    confirm: 'Reject',
    danger: true,
  },
}

function KeyFacts({ view }: { view: OfficerApplication }) {
  const current = view.revisions[view.revisions.length - 1]
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-[13px] sm:grid-cols-4">
      <div>
        <dt className="text-text-3">Applicant</dt>
        <dd className="font-medium">{view.applicant.full_name}</dd>
        <dd className="truncate text-text-3">{view.applicant.email}</dd>
      </div>
      <div>
        <dt className="text-text-3">Submitted</dt>
        <dd className="font-medium tabular-nums">{current ? formatDateTime(current.submitted_at) : 'Not yet'}</dd>
        <dd className="text-text-3">Revision {view.current_revision_number}</dd>
      </div>
      <div>
        <dt className="text-text-3">Premises</dt>
        <dd className="font-medium">{view.premises_summary ?? 'Not entered'}</dd>
      </div>
      <div>
        <dt className="text-text-3">Last activity</dt>
        <dd className="font-medium tabular-nums">{formatRelative(view.updated_at)}</dd>
        <dd className="text-text-3">Created {formatDate(view.created_at)}</dd>
      </div>
    </dl>
  )
}

function ReviewRail({
  view,
  targets,
  onAction,
  busy,
}: {
  view: OfficerApplication
  targets: Target[]
  onAction: (action: OfficerAction) => void
  busy: boolean
}) {
  const s = view.verification_summary
  const primary = view.actions.find((a) => a.enabled && !a.requires_note)
  const rest = view.actions.filter((a) => a !== primary)
  return (
    <aside className="flex flex-col gap-5 lg:sticky lg:top-[88px] lg:self-start">
      <section className="pf-surface" aria-labelledby="review-title">
        <div className="px-5 pt-5">
          <h2 id="review-title" className="text-[17px] font-semibold leading-6">
            Review
          </h2>
          <p className="mt-1 text-[13px] leading-[19px] text-text-2">
            {view.actions.length === 0
              ? 'No further action is available for this application.'
              : 'Every status change is recorded with your name in the audit trail.'}
          </p>
        </div>
        {view.actions.length > 0 ? (
          <div className="flex flex-col gap-2 px-5 pb-5 pt-4">
            {primary ? (
              <Button size="lg" loading={busy} onClick={() => onAction(primary)}>
                {primary.label}
              </Button>
            ) : null}
            {rest.map((a) => (
              <Button
                key={a.target}
                variant={a.requires_note ? 'danger' : 'secondary'}
                disabled={!a.enabled || busy}
                title={a.reason ?? undefined}
                onClick={() => onAction(a)}
              >
                {a.label}
              </Button>
            ))}
            {rest.some((a) => !a.enabled && a.reason) ? (
              <ul className="mt-1 flex flex-col gap-1 text-xs leading-[17px] text-text-3">
                {rest
                  .filter((a) => !a.enabled && a.reason)
                  .map((a) => (
                    <li key={a.target}>
                      {a.label}: {a.reason}
                    </li>
                  ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="pf-surface" aria-labelledby="ai-title">
        <div className="flex items-baseline justify-between px-5 pt-4">
          <h2 id="ai-title" className="text-[15px] font-semibold">
            Document checks
          </h2>
          <span className="text-xs text-text-3">AI-assisted</span>
        </div>
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 px-5 pb-4 text-[13px]">
          <Stat label="Analysed" value={s.total} />
          <Stat label="Verified" value={s.verified} tone="success" />
          <Stat label="Issues found" value={s.issues_found} tone="warning" />
          <Stat label="Need your review" value={s.needs_review} tone="warning" />
          {s.checking > 0 ? <Stat label="Still checking" value={s.checking} tone="info" /> : null}
          {s.other > 0 ? <Stat label="Unreadable or failed" value={s.other} /> : null}
        </dl>
        <p className="border-t border-line px-5 py-3 text-xs leading-[18px] text-text-3">
          Checks compare each document with the submitted form. They are advisory: the decision is yours.
        </p>
      </section>

      <FeedbackPanel view={view} targets={targets} />
    </aside>
  )
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: 'success' | 'warning' | 'info' }) {
  return (
    <div className="flex items-baseline justify-between border-b border-line py-1.5 last:border-b-0">
      <dt className="text-text-2">{label}</dt>
      <dd
        className={cn(
          'font-mono font-medium tabular-nums',
          value > 0 && tone === 'success' && 'text-success',
          value > 0 && tone === 'warning' && 'text-warning',
          value > 0 && tone === 'info' && 'text-info',
        )}
      >
        {value}
      </dd>
    </div>
  )
}

/** Officer case review workspace (S-21): submission on the left, review rail on the right. */
export function OfficerCasePage() {
  const { id = '' } = useParams()
  const app = useOfficerApplication(id)
  const schema = useFormSchema()
  const transition = useTransition(id)
  const rerun = useRerunCheck(id)
  const toast = useToast()
  const [pending, setPending] = useState<OfficerAction | null>(null)
  const [note, setNote] = useState('')
  const [noteError, setNoteError] = useState<string | null>(null)

  if (app.isPending || schema.isPending) {
    return (
      <PageSkeleton label="Loading case">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Skeleton className="h-[480px]" />
          <Skeleton className="h-72" />
        </div>
      </PageSkeleton>
    )
  }
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/officer/queue" backLabel="Back to the queue" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  if (schema.isError) return <ErrorPanel error={schema.error} onRetry={() => void schema.refetch()} />

  const view = app.data
  const targets: Target[] = [
    ...view.sections.map((sec) => ({ value: `section:${sec.key}`, label: sec.title, target_type: 'section' as const, key: sec.key })),
    ...view.documents.map((d) => ({
      value: `document:${d.document_type}`,
      label: d.label,
      target_type: 'document' as const,
      key: d.document_type,
    })),
  ]
  const openFor = (type: 'section' | 'document', key: string) =>
    view.feedback.filter((f) => f.resolution === 'open' && (type === 'section' ? f.section_key === key : f.document_type === key))
  const error = transition.error instanceof AppError ? transition.error : null
  const stale = error?.status === 409 && error.code === 'version_conflict'

  const confirm = () => {
    if (!pending) return
    if (pending.requires_note && note.trim().length < 3) {
      setNoteError('Write a note for the operator: it is shown with the outcome.')
      return
    }
    transition.mutate(
      { target: pending.target, note: pending.requires_note || note.trim() ? note.trim() : undefined, expected_version: view.version },
      {
        onSuccess: (next) => {
          setPending(null)
          setNote('')
          toast.push({ title: `Now ${next.status_label}`, body: 'The operator has been notified.', tone: 'success' })
        },
        onError: () => setPending(null),
      },
    )
  }

  const copy = pending ? ACTION_COPY[pending.target] : null

  return (
    <>
      <Breadcrumb items={[{ label: 'Review queue', to: '/officer/queue' }, { label: view.reference_no }]} />
      <div className="mb-6">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="font-mono text-[13px] font-medium tracking-[0.02em] text-text-2">{view.reference_no}</span>
          <span className="text-line-strong" aria-hidden="true">
            ·
          </span>
          <span className="text-[13px] text-text-2">{view.licence_title}</span>
        </div>
        <h1 className="mt-1.5 text-[28px] font-semibold leading-9 tracking-[-0.015em]">
          {view.business_name ?? <span className="text-text-2">Business name not entered</span>}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
          <StatusBadge label={view.status_label} tone={view.status_tone} size="lg" live={view.verification_summary.checking > 0} />
          {view.decision_note ? <span className="text-sm text-text-2">Note: {view.decision_note}</span> : null}
        </div>
        <div className="mt-5 border-t border-line pt-4">
          <KeyFacts view={view} />
        </div>
      </div>

      {view.status === 'pre_site_resubmitted' ? (
        <div className="mb-5">
          <Alert tone="info" title={`Revision ${view.current_revision_number} resubmitted`}>
            {view.changed_sections.length} {view.changed_sections.length === 1 ? 'section' : 'sections'} and{' '}
            {view.changed_document_types.length} {view.changed_document_types.length === 1 ? 'document' : 'documents'} changed. Start the
            review, check the changes below and mark each feedback item resolved or leave it open for another round.
          </Alert>
        </div>
      ) : null}
      {view.addressed_unresolved_count > 0 && view.status !== 'pre_site_resubmitted' ? (
        <div className="mb-5">
          <Alert
            tone="warning"
            title={`${view.addressed_unresolved_count} addressed ${view.addressed_unresolved_count === 1 ? 'item is' : 'items are'} not resolved yet`}
          >
            The operator changed these targets. Mark each one resolved, or leave it open and request another resubmission, before scheduling
            a site visit.
          </Alert>
        </div>
      ) : null}
      {stale ? (
        <div className="mb-5">
          <Alert
            tone="warning"
            title="This application changed since you opened it"
            action={
              <Button variant="secondary" size="sm" onClick={() => void app.refetch()}>
                Reload
              </Button>
            }
          >
            Another officer or the operator updated it. Reload to see the latest before acting.
          </Alert>
        </div>
      ) : error ? (
        <div className="mb-5">
          <Alert tone="error" title="Could not change the status">
            {error.message}
          </Alert>
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex flex-col gap-6">
          <section className="pf-surface px-5 py-6 sm:px-7" aria-labelledby="submission-title">
            <div className="mb-2 flex items-baseline justify-between">
              <h2 id="submission-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
                Submission · Revision {view.current_revision_number}
              </h2>
              <span className="text-xs text-text-3">
                {view.sections.filter((s) => s.complete).length} of {view.sections.length} sections complete
              </span>
            </div>
            <div className="divide-y divide-line">
              {schema.data.sections.map((def, i) => {
                const section = view.sections.find((s) => s.key === def.key)
                if (!section) return null
                return (
                  <section
                    key={def.key}
                    id={`target-section-${def.key}`}
                    className="scroll-mt-24 py-6 first:pt-0 last:pb-0"
                    aria-labelledby={`case-${def.key}`}
                  >
                    <div className="mb-4 flex flex-wrap items-center gap-3">
                      <span className="font-mono text-[13px] text-text-3">0{i + 1}</span>
                      <h3 id={`case-${def.key}`} className="text-[17px] font-semibold leading-6">
                        {def.title}
                      </h3>
                      {!section.complete ? <StatusBadge label="Incomplete" tone="warning" /> : null}
                      {openFor('section', def.key).length ? (
                        <StatusBadge label={`${openFor('section', def.key).length} open feedback`} tone="warning" />
                      ) : null}
                      {view.changed_sections.includes(def.key) ? (
                        <StatusBadge label={`Changed in Revision ${view.current_revision_number}`} tone="info" />
                      ) : null}
                    </div>
                    <dl className="grid gap-x-6 gap-y-2.5 text-sm sm:grid-cols-[220px_minmax(0,1fr)]">
                      {def.fields.map((f) => {
                        const value = section.data[f.key]
                        const empty = value === undefined || value === null || value === ''
                        return (
                          <div key={f.key} className="contents">
                            <dt className="text-text-3 sm:py-0.5">{f.label}</dt>
                            <dd className={empty ? 'text-text-3 sm:py-0.5' : 'font-medium sm:py-0.5'}>{displayValue(f, value)}</dd>
                          </div>
                        )
                      })}
                    </dl>
                  </section>
                )
              })}
            </div>
          </section>

          <section className="pf-surface overflow-hidden" aria-labelledby="docs-title">
            <div className="flex items-baseline justify-between border-b border-line px-5 py-4 sm:px-7">
              <h2 id="docs-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
                Documents
              </h2>
              <span className="text-xs text-text-3">
                {view.documents.length} attached
                {view.missing_document_types.length ? ` · ${view.missing_document_types.length} missing` : ''}
              </span>
            </div>
            <ol className="divide-y divide-line">
              {view.documents.map((d, i) => (
                <li key={d.id} id={`target-document-${d.document_type}`} className="scroll-mt-24 px-5 py-5 sm:px-7">
                  <div className="flex items-start gap-3.5">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-ink text-white">
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z" />
                        <path d="M14 2v6h6" />
                      </svg>
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline gap-x-2">
                        <span className="font-mono text-xs text-text-3">0{i + 1}</span>
                        <h3 className="text-[15px] font-semibold leading-[22px]">{d.label}</h3>
                        {!d.in_current_revision ? <StatusBadge label="Uploaded after submission" tone="info" /> : null}
                        {openFor('document', d.document_type).length ? (
                          <StatusBadge label={`${openFor('document', d.document_type).length} open feedback`} tone="warning" />
                        ) : null}
                        {view.changed_document_types.includes(d.document_type) ? (
                          <StatusBadge label={`Replaced in Revision ${view.current_revision_number}`} tone="info" />
                        ) : null}
                      </div>
                      <div className="truncate text-[13px] text-text-3">
                        <span className="text-text-2">{d.original_filename}</span> · {formatBytes(d.size_bytes)} · uploaded{' '}
                        {formatDateTime(d.uploaded_at)}
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() =>
                        void downloadDocument(id, d.id, d.original_filename).catch((e: unknown) =>
                          toast.push({ title: 'Download failed', body: e instanceof Error ? e.message : 'Try again.', tone: 'error' }),
                        )
                      }
                    >
                      Open
                    </Button>
                  </div>
                  {d.verification ? (
                    <div className="mt-4 rounded-md border border-line bg-surface-2 px-4 py-3.5">
                      <CheckResult verification={d.verification} />
                      {d.verification.status !== 'pending' && d.verification.status !== 'running' ? (
                        <div className="mt-3 flex justify-end border-t border-line pt-2.5">
                          <Button
                            variant="ghost"
                            size="sm"
                            loading={rerun.isPending && rerun.variables === d.id}
                            disabled={rerun.isPending}
                            onClick={() =>
                              rerun.mutate(d.id, {
                                onError: (e) => toast.push({ title: 'Could not re-run the check', body: e.message, tone: 'error' }),
                              })
                            }
                          >
                            Re-run check
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </li>
              ))}
              {view.missing_document_types.map((t) => (
                <li key={t} className="px-5 py-4 text-sm text-text-3 sm:px-7">
                  <span className="font-medium text-text-2">{t.replaceAll('_', ' ')}</span> was not attached to this revision.
                </li>
              ))}
            </ol>
          </section>

          <ComparePanel view={view} />

          <section className="pf-surface" aria-labelledby="history-title">
            <div className="border-b border-line px-5 py-4 sm:px-7">
              <h2 id="history-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
                Revision history
              </h2>
            </div>
            <ol className="divide-y divide-line">
              {view.revisions.map((r) => (
                <li key={r.id} className="flex items-baseline gap-4 px-5 py-3 text-sm sm:px-7">
                  <span className="font-mono text-xs text-text-3">R{r.number}</span>
                  <span className="font-medium">Revision {r.number}</span>
                  <span className="text-text-3">
                    submitted {formatDateTime(r.submitted_at)} by {r.submitted_by}
                  </span>
                  {r.number === view.current_revision_number ? (
                    <span className="ml-auto text-xs font-semibold text-text-2">Current</span>
                  ) : null}
                </li>
              ))}
            </ol>
            <p className="border-t border-line px-5 py-3 text-xs text-text-3 sm:px-7">
              The audit trail arrives with US-029.{' '}
              <Link to="/officer/queue" className="text-text-2">
                Back to the queue
              </Link>
            </p>
          </section>
        </div>
        <ReviewRail view={view} targets={targets} busy={transition.isPending} onAction={(a) => setPending(a)} />
      </div>

      <Dialog
        open={pending !== null}
        title={copy?.title ?? ''}
        confirmLabel={copy?.confirm ?? 'Confirm'}
        danger={copy?.danger}
        busy={transition.isPending}
        onConfirm={confirm}
        onCancel={() => {
          setPending(null)
          setNoteError(null)
        }}
      >
        <p>{copy?.body}</p>
        {pending?.requires_note || pending?.target === 'approved' ? (
          <TextAreaField
            label={pending.requires_note ? 'Note to the operator' : 'Note to the operator'}
            required={pending.requires_note}
            value={note}
            error={noteError ?? undefined}
            onChange={(e) => {
              setNote(e.target.value)
              setNoteError(null)
            }}
            maxLength={2000}
            placeholder="Shown to the operator with the outcome."
          />
        ) : null}
      </Dialog>
    </>
  )
}
