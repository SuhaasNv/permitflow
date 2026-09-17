import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { Dialog } from '@/features/shared/Dialog'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, Skeleton } from '@/features/shared/states'
import { CompletionCard } from './CompletionCard'
import { SectionSummary } from './SectionSummary'
import { useApplication, useFormSchema, useSubmitApplication } from './queries'

const ATTENTION = new Set(['issues_found', 'needs_review', 'failed', 'unavailable', 'unreadable'])

export function ReviewPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const app = useApplication(id)
  const schema = useFormSchema()
  const submit = useSubmitApplication(id)
  const [confirm, setConfirm] = useState(false)

  if (app.isPending || schema.isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading review">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-40 w-full" />
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
  const withAttention = view.document_slots.filter((s) => s.document?.verification && ATTENTION.has(s.document.verification.status))
  const submitError = submit.error instanceof AppError ? submit.error : null
  const missing =
    submitError?.status === 422 && Array.isArray(submitError.details?.missing) ? (submitError.details.missing as string[]) : []

  const doSubmit = () =>
    submit.mutate(undefined, {
      onSuccess: () => navigate(`/app/applications/${id}/submitted`),
      onSettled: () => setConfirm(false),
    })

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-2 text-[13px] text-text-3">
        <Link to="/app/dashboard" className="text-text-2">
          My applications
        </Link>
        <span aria-hidden="true">›</span>
        <Link to={`/app/applications/${id}`} className="text-text-2">
          {view.reference_no}
        </Link>
        <span aria-hidden="true">›</span>
        <span className="text-text">Review and submit</span>
      </nav>
      <div className="mb-5">
        <h1 className="text-[26px] font-semibold leading-8 tracking-tight">Review and submit</h1>
        <p className="mt-1 text-text-2">
          {view.reference_no} · {view.licence_title}
        </p>
      </div>
      <div className="mb-5 flex flex-wrap items-center gap-4 rounded-lg border border-line bg-surface px-5 py-3.5 shadow-[var(--shadow-1)]">
        <StatusBadge label={view.status_label} tone={view.status_tone} size="lg" />
        <span className="text-sm text-text-2">
          {view.can_submit
            ? 'Everything required is in place. Check the details below, then submit.'
            : 'Some items are still missing. Complete them before you submit.'}
        </span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-5">
          {submit.isError && !missing.length ? (
            <Alert tone="error">
              <span>{submitError?.message ?? 'Could not submit. Try again.'}</span>
            </Alert>
          ) : null}
          {missing.length ? (
            <Alert tone="error">
              <div>
                <b>Not ready to submit.</b> <span className="text-[13px]">{missing.join(' · ')}</span>
              </div>
            </Alert>
          ) : null}
          {withAttention.length ? (
            <Alert tone="warning">
              <div>
                <b>
                  {withAttention.length} {withAttention.length === 1 ? 'document has' : 'documents have'} unresolved check results.
                </b>{' '}
                You can still submit; the licensing officer will see the same findings and may ask you to clarify.{' '}
                <Link to={`/app/applications/${id}/documents`} className="font-semibold text-inherit">
                  Review documents
                </Link>
              </div>
            </Alert>
          ) : null}
          {schema.data.sections.map((def) => {
            const state = view.sections.find((s) => s.key === def.key)
            if (!state) return null
            return (
              <SectionSummary
                key={def.key}
                def={def}
                state={state}
                editHref={state.editable ? `/app/applications/${id}/form/${def.key}` : undefined}
              />
            )
          })}
          <section className="rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]" aria-labelledby="summary-docs">
            <div className="flex items-center gap-3 border-b border-line px-5 py-3.5">
              <h2 id="summary-docs" className="text-base font-semibold">
                Documents
              </h2>
              <StatusBadge
                label={`${view.completeness.documents_present} of ${view.completeness.documents_total} uploaded`}
                tone={view.completeness.documents_present === view.completeness.documents_total ? 'success' : 'neutral'}
              />
              {view.can_edit ? (
                <Link to={`/app/applications/${id}/documents`} className="ml-auto text-[13px] font-semibold">
                  Manage
                </Link>
              ) : null}
            </div>
            <ul className="px-5">
              {view.document_slots.map((slot) => {
                const v = slot.document?.verification
                const tone = !v
                  ? 'neutral'
                  : v.status === 'verified'
                    ? 'success'
                    : v.status === 'issues_found' || v.status === 'failed'
                      ? 'error'
                      : v.status === 'needs_review'
                        ? 'warning'
                        : v.status === 'running' || v.status === 'pending'
                          ? 'info'
                          : 'neutral'
                const label = !slot.document
                  ? 'Missing'
                  : !v
                    ? 'Uploaded'
                    : v.status === 'issues_found'
                      ? `${v.issues.length} issue${v.issues.length === 1 ? '' : 's'} found`
                      : v.status === 'needs_review'
                        ? 'Needs officer review'
                        : v.status === 'unreadable'
                          ? 'Could not be read'
                          : v.status === 'running' || v.status === 'pending'
                            ? 'Checking…'
                            : v.status === 'failed'
                              ? 'Check failed'
                              : v.status === 'unavailable'
                                ? 'Check unavailable'
                                : 'Verified'
                return (
                  <li key={slot.type} className="flex items-center gap-3 border-b border-line py-2.5 text-sm last:border-b-0">
                    <span className="min-w-0 flex-1">
                      <span className="font-medium">{slot.label}</span>
                      {slot.document ? <span className="ml-1 break-all text-text-3">· {slot.document.original_filename}</span> : null}
                    </span>
                    <StatusBadge label={label} tone={tone} />
                  </li>
                )
              })}
            </ul>
          </section>
        </div>
        <aside className="flex flex-col gap-4">
          <section className="rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]">
            <div className="border-b border-line px-5 py-3.5">
              <h2 className="text-base font-semibold">{view.can_submit ? 'Ready to submit' : 'Not ready yet'}</h2>
            </div>
            <div className="px-5 py-4 text-[13px] text-text-2">
              After you submit, your application becomes <b>Revision 1</b> and is locked for editing. If the licensing office needs changes,
              you will be notified and only the flagged parts will reopen.
            </div>
            <div className="flex flex-col gap-2 border-t border-line bg-surface-2 px-5 py-3">
              <Button size="lg" disabled={!view.can_submit} loading={submit.isPending} onClick={() => setConfirm(true)}>
                Submit application
              </Button>
              <Link
                to="/app/dashboard"
                className="inline-flex h-10 items-center justify-center rounded-md text-sm font-semibold text-text-2 no-underline hover:bg-neutral-soft hover:text-text"
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
