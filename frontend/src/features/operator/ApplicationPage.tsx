import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Button, buttonClasses } from '@/features/shared/Button'
import { TextAreaField } from '@/features/shared/Controls'
import { Dialog } from '@/features/shared/Dialog'
import { useToast } from '@/features/shared/Toast'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { ApplicationHeader } from './ApplicationHeader'
import { CompletionCard } from './CompletionCard'
import { FeedbackNotice, targetHref } from './FeedbackNotice'
import { useApplication, useResubmitApplication, useWithdrawApplication } from './queries'

const ArrowIcon = (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    className="transition-transform duration-[var(--dur-fast)] group-hover:translate-x-0.5"
  >
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
)

export function ApplicationPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  const resubmit = useResubmitApplication(id)
  const navigate = useNavigate()
  const toast = useToast()
  const [confirm, setConfirm] = useState(false)
  const withdraw = useWithdrawApplication(id)
  const [withdrawOpen, setWithdrawOpen] = useState(false)
  const [reason, setReason] = useState('')

  if (app.isPending) {
    return (
      <PageSkeleton label="Loading application">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </PageSkeleton>
    )
  }
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404) {
      return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
    }
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  const view = app.data
  const nextSection = view.sections.find((s) => !s.complete)
  const docsDone = view.completeness.documents_present === view.completeness.documents_total
  const responding = view.resubmit !== null
  const firstOpen = view.feedback.find((f) => f.resolution === 'open')
  const openCount = view.feedback.filter((f) => f.resolution === 'open').length
  const doResubmit = () => {
    if (resubmit.isPending) return
    resubmit.mutate(undefined, {
      onSuccess: () => {
        setConfirm(false)
        toast.push({ title: 'Resubmitted', body: 'Your changes were sent to the licensing office as a new revision.', tone: 'success' })
        navigate(`/app/applications/${id}/submitted`, { replace: true })
      },
      onError: (e) => {
        setConfirm(false)
        toast.push({ title: 'Could not resubmit', body: e.message, tone: 'error' })
      },
    })
  }

  const withdrawn = view.withdrawal_reason !== null || view.status_label === 'Withdrawn'
  const doWithdraw = () => {
    if (withdraw.isPending) return
    withdraw.mutate(reason.trim() || null, {
      onSuccess: () => {
        setWithdrawOpen(false)
        toast.push({ title: 'Application withdrawn', body: 'The licensing office has been told.', tone: 'success' })
      },
      onError: (e) => {
        setWithdrawOpen(false)
        toast.push({ title: 'Could not withdraw', body: e.message, tone: 'error' })
      },
    })
  }

  return (
    <>
      <ApplicationHeader
        view={view}
        actions={
          responding && view.can_edit ? (
            <>
              {firstOpen ? (
                <Link to={targetHref(view, firstOpen)} className={buttonClasses('secondary')}>
                  Respond to feedback
                </Link>
              ) : null}
              <Button disabled={!view.resubmit?.can_resubmit} title={view.resubmit?.reason ?? undefined} onClick={() => setConfirm(true)}>
                Resubmit
              </Button>
            </>
          ) : view.can_edit ? (
            <>
              {view.can_submit ? (
                <Link to={`/app/applications/${id}/review`} className={buttonClasses('secondary')}>
                  Review and submit
                </Link>
              ) : null}
              <Link to={`/app/applications/${id}/form${nextSection ? `/${nextSection.key}` : ''}`} className={buttonClasses('primary')}>
                {view.completeness.percent === 0 ? 'Start application' : 'Continue application'}
              </Link>
            </>
          ) : undefined
        }
      />
      {withdrawn ? (
        <section className="mb-6 rounded-lg border border-line bg-surface-2 px-5 py-4" aria-labelledby="outcome-title">
          <h2 id="outcome-title" className="text-[15px] font-semibold">
            You withdrew this application
          </h2>
          <p className="mt-1 text-sm leading-[21px] text-text-2">
            {view.withdrawal_reason ? (
              <>
                <span className="font-medium text-text">Your reason:</span> {view.withdrawal_reason}
              </>
            ) : (
              'No reason was given.'
            )}
          </p>
          <p className="mt-2 text-[13px] text-text-3">
            The licensing office will not review it further. Start a new application if you need a licence later.
          </p>
        </section>
      ) : null}
      {view.decision_note !== null ? (
        <section
          className={cn(
            'mb-6 rounded-lg border px-5 py-4',
            view.status_tone === 'success' ? 'border-success-line bg-success-soft/50' : 'border-error-line bg-error-soft/50',
          )}
          aria-labelledby="outcome-title"
        >
          <h2 id="outcome-title" className="text-[15px] font-semibold">
            {view.status_tone === 'success' ? 'Your licence application was approved' : 'Your licence application was not approved'}
          </h2>
          <p className="mt-1 text-sm leading-[21px] text-text-2">
            <span className="font-medium text-text">Officer's note:</span> {view.decision_note}
          </p>
          <p className="mt-2 text-[13px] text-text-3">This decision is final. The full record stays available under History.</p>
        </section>
      ) : null}
      {responding && view.resubmit ? (
        <div className="mb-6">
          <Alert
            tone={view.resubmit.can_resubmit ? 'success' : 'warning'}
            title={
              view.resubmit.can_resubmit
                ? `Ready to resubmit: ${[...view.resubmit.changed_sections, ...view.resubmit.changed_document_types].length} of ${openCount} flagged ${openCount === 1 ? 'item' : 'items'} changed.`
                : 'Nothing has changed yet.'
            }
          >
            {view.resubmit.can_resubmit
              ? view.resubmit.untouched_targets.length
                ? `Not changed yet: ${view.resubmit.untouched_targets.join(', ')}. You can resubmit now or keep editing.`
                : 'Every flagged item has been changed. Press Resubmit to send your changes back to the licensing office.'
              : view.resubmit.reason}
          </Alert>
        </div>
      ) : null}
      {view.feedback.length > 0 ? (
        <div className="mb-6">
          <FeedbackNotice view={view} />
        </div>
      ) : null}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section className="pf-surface overflow-hidden lg:self-start" aria-labelledby="sections-title">
          <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
            <h2 id="sections-title" className="text-[15px] font-semibold">
              Application
            </h2>
            <span className="text-xs text-text-3">
              {view.completeness.sections_complete} of {view.completeness.sections_total} sections complete
            </span>
          </div>
          <ol className="pf-stagger divide-y divide-line">
            {view.sections.map((s, i) => {
              const flagged = responding && view.feedback.some((f) => f.resolution === 'open' && f.section_key === s.key)
              const state = flagged ? 'Officer asked for changes' : s.complete ? 'Complete' : s.started ? 'Needs attention' : 'Not started'
              const inner = (
                <>
                  <span className="font-mono text-[13px] text-text-3">0{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold">{s.title}</div>
                    <div className="text-[13px] text-text-3">{s.description}</div>
                  </div>
                  <span
                    className={cn(
                      'inline-flex items-center gap-1.5 text-xs font-medium',
                      flagged ? 'text-warning' : s.complete ? 'text-success' : s.started ? 'text-warning' : 'text-text-3',
                    )}
                  >
                    <span className="h-[7px] w-[7px] rounded-full bg-current" aria-hidden="true" />
                    {state}
                  </span>
                  {s.editable ? (
                    <span className="inline-flex items-center gap-1 text-[13px] font-semibold text-text">
                      {s.started ? 'Edit' : 'Start'}
                      {ArrowIcon}
                    </span>
                  ) : null}
                </>
              )
              return (
                <li key={s.key}>
                  {s.editable ? (
                    <Link
                      to={`/app/applications/${id}/form/${s.key}`}
                      className="group flex items-center gap-4 px-5 py-4 text-text no-underline transition-colors duration-[var(--dur-fast)] hover:bg-surface-2 hover:text-text"
                    >
                      {inner}
                    </Link>
                  ) : (
                    <div className="flex items-center gap-4 px-5 py-4">{inner}</div>
                  )}
                </li>
              )
            })}
            <li>
              {view.can_edit ? (
                <Link
                  to={`/app/applications/${id}/documents`}
                  className="group flex items-center gap-4 px-5 py-4 text-text no-underline transition-colors duration-[var(--dur-fast)] hover:bg-surface-2 hover:text-text"
                >
                  <span className="font-mono text-[13px] text-text-3">05</span>
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold">Documents</div>
                    <div className="text-[13px] text-text-3">
                      {view.completeness.documents_present} of {view.completeness.documents_total} required documents uploaded
                    </div>
                  </div>
                  <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium', docsDone ? 'text-success' : 'text-text-3')}>
                    <span className="h-[7px] w-[7px] rounded-full bg-current" aria-hidden="true" />
                    {docsDone ? 'Complete' : 'In progress'}
                  </span>
                  <span className="inline-flex items-center gap-1 text-[13px] font-semibold text-text">
                    Manage
                    {ArrowIcon}
                  </span>
                </Link>
              ) : (
                <div className="flex items-center gap-4 px-5 py-4">
                  <span className="font-mono text-[13px] text-text-3">05</span>
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold">Documents</div>
                    <div className="text-[13px] text-text-3">
                      {view.completeness.documents_present} of {view.completeness.documents_total} required documents uploaded
                    </div>
                  </div>
                </div>
              )}
            </li>
          </ol>
        </section>
        <div className="flex flex-col gap-6">
          <CompletionCard view={view} />
          {view.can_withdraw ? (
            <section className="pf-surface px-5 py-4" aria-labelledby="withdraw-title">
              <h2 id="withdraw-title" className="text-[15px] font-semibold">
                No longer need this licence?
              </h2>
              <p className="mt-1 text-[13px] leading-[19px] text-text-2">
                You can withdraw the application at any point before a decision. The licensing office is told and stops the review.
              </p>
              <Button variant="danger" size="sm" className="mt-3" onClick={() => setWithdrawOpen(true)}>
                Withdraw application
              </Button>
            </section>
          ) : null}
        </div>
      </div>
      <Dialog
        open={withdrawOpen}
        title="Withdraw this application?"
        confirmLabel="Withdraw application"
        danger
        busy={withdraw.isPending}
        onConfirm={doWithdraw}
        onCancel={() => setWithdrawOpen(false)}
      >
        <p>
          <b>{view.reference_no}</b> is closed for good and the licensing office stops its review. This cannot be undone; you would need to
          start a new application.
        </p>
        <TextAreaField
          label="Reason"
          help="Shared with the licensing office."
          value={reason}
          maxLength={1000}
          onChange={(e) => setReason(e.target.value)}
        />
      </Dialog>
      <Dialog
        open={confirm}
        title="Resubmit this application?"
        confirmLabel="Resubmit"
        busy={resubmit.isPending}
        onConfirm={doResubmit}
        onCancel={() => setConfirm(false)}
      >
        <p>
          Your changes are recorded as <b>Revision {view.revision_count + 1}</b> and sent back to the licensing office. Flagged items you
          changed are marked as addressed; the officer decides whether they are resolved.
        </p>
        {view.resubmit?.untouched_targets.length ? (
          <p>
            Not changed yet: <b>{view.resubmit.untouched_targets.join(', ')}</b>. You can still resubmit; the officer may ask again.
          </p>
        ) : null}
      </Dialog>
    </>
  )
}
