import { useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import type { ApplicationView } from '@/api/applications'
import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { DocumentSlot } from './documents/DocumentSlot'
import { applicationKeys, useApplication } from './queries'

export function DocumentsPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  const qc = useQueryClient()

  const setView = (view: ApplicationView) => {
    qc.setQueryData(applicationKeys.detail(id), view)
    void qc.invalidateQueries({ queryKey: applicationKeys.all })
  }

  if (app.isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading documents">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  const view = app.data
  const c = view.completeness
  const canDelete = view.status_label === 'Draft'

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
        <span className="text-text">Documents</span>
      </nav>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-[26px] font-semibold leading-8 tracking-tight">Documents</h1>
          <p className="mt-1 text-text-2">
            {view.reference_no} · {view.licence_title}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          <Link
            to={`/app/applications/${id}/form`}
            className="inline-flex h-10 items-center rounded-md border border-line-strong bg-surface px-4 text-sm font-semibold text-text no-underline shadow-[var(--shadow-1)] hover:bg-surface-2"
          >
            Back to form
          </Link>
          <Link
            to={`/app/applications/${id}/review`}
            className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-semibold text-white no-underline hover:bg-primary-hover hover:text-white"
          >
            Review and submit
          </Link>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-4 rounded-lg border border-line bg-surface px-5 py-3.5 shadow-[var(--shadow-1)]">
        <StatusBadge label={view.status_label} tone={view.status_tone} size="lg" />
        <span className="text-sm text-text-2">
          {c.documents_total} documents required · {c.documents_present} uploaded
        </span>
      </div>

      <Alert tone="info" className="mb-5">
        <div>
          <b>Uploads are checked automatically.</b> The checker reads each document and compares it with your form to warn you about likely
          problems. It does not approve or reject anything: a licensing officer reviews every application.
        </div>
      </Alert>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-4">
          {view.document_slots.map((slot) => (
            <DocumentSlot
              key={slot.type}
              applicationId={id}
              slot={slot}
              canDelete={canDelete}
              onUploaded={(r) => setView(r.application)}
              onDeleted={setView}
            />
          ))}
        </div>
        <aside className="flex flex-col gap-4">
          <div className="rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]">
            <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
              <h2 className="text-base font-semibold">Required documents</h2>
              <span className="text-xs tabular-nums text-text-3">
                {c.documents_present} / {c.documents_total}
              </span>
            </div>
            <ul className="px-5">
              {view.document_slots.map((slot) => (
                <li key={slot.type} className="flex items-center gap-2.5 border-b border-line py-2.5 text-sm last:border-b-0">
                  <span
                    className={cn(
                      'flex h-5 w-5 items-center justify-center rounded-full text-[11px]',
                      slot.present ? 'bg-success text-white' : 'border-[1.5px] border-line-strong',
                    )}
                    aria-hidden="true"
                  >
                    {slot.present ? '✓' : ''}
                  </span>
                  <span>{slot.label}</span>
                  <span className="ml-auto text-xs text-text-3">{slot.present ? 'Uploaded' : 'Missing'}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-lg border border-line bg-surface px-5 py-4 shadow-[var(--shadow-1)]">
            <h2 className="mb-1.5 text-base font-semibold">Accepted files</h2>
            <p className="text-[13px] text-text-2">
              PDF, PNG, JPG or TXT, up to 10 MB each. PDF is recommended: it is the only format the automatic check can read. Re-uploading
              an identical file is detected and does not count as a change.
            </p>
          </div>
        </aside>
      </div>
    </>
  )
}
