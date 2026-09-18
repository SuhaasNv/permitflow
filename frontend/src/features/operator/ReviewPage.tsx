import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { Dialog } from '@/features/shared/Dialog'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { ApplicationHeader } from './ApplicationHeader'
import { CompletionCard } from './CompletionCard'
import { SectionSummary } from './SectionSummary'
import { applicationKeys, useApplication, useFormSchema, useSubmitApplication } from './queries'
import { useQueryClient } from '@tanstack/react-query'

const ATTENTION = new Set(['issues_found', 'needs_review', 'failed', 'unavailable', 'unreadable'])

function docStatus(slot: { document: { verification: { status: string; issues: unknown[] } | null } | null }): {
  label: string
  tone: Tone
} {
  const v = slot.document?.verification
  if (!slot.document) return { label: 'Missing', tone: 'neutral' }
  if (!v) return { label: 'Uploaded', tone: 'success' }
  switch (v.status) {
    case 'verified':
      return { label: 'Verified', tone: 'success' }
    case 'issues_found':
      return { label: `${v.issues.length} issue${v.issues.length === 1 ? '' : 's'} to check`, tone: 'warning' }
    case 'needs_review':
      return { label: 'Needs officer review', tone: 'warning' }
    case 'unreadable':
      return { label: 'Could not be read', tone: 'neutral' }
    case 'running':
    case 'pending':
      return { label: 'Checking', tone: 'info' }
    case 'failed':
      return { label: 'Check did not complete', tone: 'error' }
    default:
      return { label: 'Check unavailable', tone: 'neutral' }
  }
}

export function ReviewPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const app = useApplication(id)
  const schema = useFormSchema()
  const submit = useSubmitApplication(id)
  const qc = useQueryClient()
  const [confirm, setConfirm] = useState(false)
  const submitError = submit.error instanceof AppError ? submit.error : null
  // Submitted elsewhere (another tab): drop the stale view so the page reflects the real state.
  useEffect(() => {
    if (submitError?.status === 409) void qc.invalidateQueries({ queryKey: applicationKeys.detail(id) })
  }, [submitError, qc, id])

  if (app.isPending || schema.isPending) {
    return (
      <PageSkeleton label="Loading review">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          <Skeleton className="h-96" />
          <Skeleton className="h-64" />
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
  const base = `/app/applications/${id}`
  // Review is only for an editable application; a submitted or decided one shows its own page.
  if (!view.can_edit) return <Navigate to={base} replace />
  const withAttention = view.document_slots.filter((s) => s.document?.verification && ATTENTION.has(s.document.verification.status))
  const stillChecking = view.document_slots.filter(
    (s) => s.document?.verification && (s.document.verification.status === 'pending' || s.document.verification.status === 'running'),
  )
  const missing =
    submitError?.status === 422 && Array.isArray(submitError.details?.missing) ? (submitError.details.missing as string[]) : []

  const doSubmit = () => {
    if (submit.isPending) return
    submit.mutate(undefined, {
      onSuccess: () => navigate(`${base}/submitted`, { replace: true }),
      onSettled: () => setConfirm(false),
    })
  }

  return (
    <>
      <ApplicationHeader view={view} crumb="Review and submit" />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-5">
          {submit.isError && !missing.length ? (
            <Alert tone="error" title={submitError?.status === 409 ? 'Already submitted' : 'Could not submit'}>
              {submitError?.status === 409
                ? 'This application was submitted from another tab or device. Nothing was sent twice.'
                : (submitError?.message ?? 'Try again in a moment. Nothing you entered has been lost.')}
            </Alert>
          ) : null}
          {stillChecking.length ? (
            <Alert
              tone="info"
              title={`${stillChecking.length} document ${stillChecking.length === 1 ? 'check is' : 'checks are'} still running`}
            >
              You can wait for the result or submit now. The licensing officer will see the result when it finishes.
            </Alert>
          ) : null}
          {missing.length ? (
            <Alert tone="error" title="Not ready to submit">
              {missing.join(' · ')}
            </Alert>
          ) : null}
          {withAttention.length ? (
            <Alert
              tone="warning"
              title={`${withAttention.length} ${withAttention.length === 1 ? 'document has' : 'documents have'} unresolved check results`}
              action={
                <Link to={`${base}/documents`} className="text-[13px] font-semibold text-inherit">
                  Review documents
                </Link>
              }
            >
              You can still submit. The licensing officer sees the same findings and may ask you to clarify.
            </Alert>
          ) : null}
          <div className="pf-surface px-5 py-6 sm:px-7">
            <div className="mb-2 flex items-baseline justify-between">
              <h2 className="text-[15px] font-semibold uppercase tracking-[0.06em] text-text-3">Your answers</h2>
              <span className="text-xs text-text-3">
                {view.completeness.sections_complete} of {view.completeness.sections_total} sections complete
              </span>
            </div>
            <div className="divide-y divide-line">
              {schema.data.sections.map((def, i) => {
                const state = view.sections.find((s) => s.key === def.key)
                if (!state) return null
                return (
                  <SectionSummary
                    key={def.key}
                    def={def}
                    state={state}
                    index={i}
                    editHref={state.editable ? `${base}/form/${def.key}` : undefined}
                  />
                )
              })}
              <section className="pt-6" aria-labelledby="summary-docs">
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <span className="font-mono text-[13px] text-text-3">0{schema.data.sections.length + 1}</span>
                  <h2 id="summary-docs" className="text-[17px] font-semibold leading-6">
                    Documents
                  </h2>
                  <StatusBadge
                    label={`${view.completeness.documents_present} of ${view.completeness.documents_total} uploaded`}
                    tone={view.completeness.documents_present === view.completeness.documents_total ? 'success' : 'neutral'}
                  />
                  {view.can_edit ? (
                    <Link to={`${base}/documents`} className="ml-auto text-[13px] font-semibold">
                      Manage
                    </Link>
                  ) : null}
                </div>
                <ul className="divide-y divide-line">
                  {view.document_slots.map((slot) => {
                    const s = docStatus(slot)
                    return (
                      <li key={slot.type} className="flex items-center gap-3 py-2.5 text-sm">
                        <span className="min-w-0 flex-1">
                          <span className="font-medium">{slot.label}</span>
                          {slot.document ? (
                            <span className="ml-2 break-all text-[13px] text-text-3">{slot.document.original_filename}</span>
                          ) : null}
                        </span>
                        <StatusBadge label={s.label} tone={s.tone} live={s.label === 'Checking'} />
                      </li>
                    )
                  })}
                </ul>
              </section>
            </div>
          </div>
        </div>
        <aside className="flex flex-col gap-5 lg:sticky lg:top-[88px] lg:self-start">
          <section className="pf-surface overflow-hidden">
            <div className="px-5 pt-5">
              <h2 className="text-[17px] font-semibold leading-6">{view.can_submit ? 'Ready to submit' : 'Not ready yet'}</h2>
              <p className="mt-2 text-[13px] leading-[19px] text-text-2">
                After you submit, your application becomes <span className="font-semibold text-text">Revision 1</span> and is locked for
                editing. If the licensing office needs changes, you will be notified and only the flagged parts will reopen.
              </p>
            </div>
            <div className="flex flex-col gap-2 px-5 pb-5 pt-5">
              <Button size="lg" disabled={!view.can_submit} loading={submit.isPending} onClick={() => setConfirm(true)}>
                Submit application
              </Button>
              <Link
                to="/app/dashboard"
                className="inline-flex h-10 items-center justify-center rounded-md text-sm font-semibold text-text-2 no-underline transition-colors hover:bg-neutral-soft hover:text-text"
              >
                Save draft and exit
              </Link>
            </div>
          </section>
          <CompletionCard view={view} />
        </aside>
      </div>

      <Dialog
        open={confirm}
        title="Submit this application?"
        confirmLabel="Submit application"
        busy={submit.isPending}
        onConfirm={doSubmit}
        onCancel={() => setConfirm(false)}
      >
        <p>
          Your form and {view.completeness.documents_present} documents are recorded as <b>Revision 1</b> and sent to the licensing office.
          You will not be able to edit the application unless an officer requests changes.
        </p>
      </Dialog>
    </>
  )
}
