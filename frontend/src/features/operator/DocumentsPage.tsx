import { useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import type { ApplicationView } from '@/api/applications'
import { AppError } from '@/api/client'
import { buttonClasses } from '@/features/shared/Button'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { ApplicationHeader } from './ApplicationHeader'
import { DocumentSlot } from './documents/DocumentSlot'
import { FeedbackNotice } from './FeedbackNotice'
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
      <PageSkeleton label="Loading documents">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="flex flex-col gap-4">
            <Skeleton className="h-40" />
            <Skeleton className="h-40" />
          </div>
          <Skeleton className="h-56" />
        </div>
      </PageSkeleton>
    )
  }
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/applications" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  const view = app.data
  const c = view.completeness
  const canDelete = view.revision_count === 0 && view.can_edit
  const base = `/app/applications/${id}`

  return (
    <>
      <ApplicationHeader
        view={view}
        crumb="Documents"
        aside={
          <span>
            · {c.documents_present} of {c.documents_total} documents uploaded
          </span>
        }
        actions={
          view.can_edit ? (
            <>
              <Link to={`${base}/form`} className={buttonClasses('secondary')}>
                Back to form
              </Link>
              <Link to={view.resubmit ? base : `${base}/review`} className={buttonClasses('primary')}>
                {view.resubmit ? (view.resubmit.can_resubmit ? 'Go to resubmit' : 'Back to application') : 'Review and submit'}
              </Link>
            </>
          ) : undefined
        }
      />

      {view.feedback.length > 0 ? (
        <div className="mb-6">
          <FeedbackNotice view={view} compact />
        </div>
      ) : null}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="pf-stagger flex flex-col gap-4">
          {view.document_slots.map((slot, i) => (
            <DocumentSlot
              key={slot.type}
              applicationId={id}
              slot={slot}
              index={i}
              canDelete={canDelete}
              feedback={view.feedback.filter((f) => f.document_type === slot.type)}
              lockedReason={view.resubmit ? 'The licensing officer did not ask for a new copy of this document.' : undefined}
              onUploaded={(r) => setView(r.application)}
              onDeleted={setView}
            />
          ))}
        </div>
        <aside className="flex flex-col gap-6 lg:sticky lg:top-[88px] lg:self-start">
          <section className="pf-surface">
            <div className="flex items-baseline justify-between px-5 pt-4">
              <h2 className="text-[15px] font-semibold">Required documents</h2>
              <span className="font-mono text-sm tabular-nums text-text-2">
                {c.documents_present}/{c.documents_total}
              </span>
            </div>
            <ul className="mt-2 divide-y divide-line px-5 pb-2">
              {view.document_slots.map((slot) => (
                <li key={slot.type} className="flex items-center gap-2.5 py-2.5 text-sm">
                  <span
                    className={cn(
                      'flex h-[18px] w-[18px] items-center justify-center rounded-full transition-colors duration-[var(--dur-base)]',
                      slot.present ? 'bg-success text-white' : 'border-[1.5px] border-line-strong',
                    )}
                    aria-hidden="true"
                  >
                    {slot.present ? (
                      <svg
                        width="10"
                        height="10"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M20 6 9 17l-5-5" />
                      </svg>
                    ) : null}
                  </span>
                  <span className="min-w-0 flex-1 truncate">{slot.label}</span>
                  <span className="text-xs text-text-3">{slot.present ? 'Uploaded' : 'Missing'}</span>
                </li>
              ))}
            </ul>
          </section>
          <div className="px-1 text-[13px] leading-[19px] text-text-2">
            <div className="mb-1.5 font-semibold text-text">About the automatic check</div>
            <p>
              Each upload is read and compared with your form so you can fix likely problems early. It never approves or rejects anything: a
              licensing officer reviews every application and sees the same findings.
            </p>
            <p className="mt-3 text-text-3">
              PDF, PNG, JPG or TXT, up to 10 MB each. PDF is recommended: the automatic check reads PDF and TXT, not images. Re-uploading an
              identical file is detected and does not count as a change.
            </p>
            <p className="mt-3 text-text-3">
              This is a demonstration: upload only the fictional sample documents, never real identity or business records. Text from PDF
              and TXT uploads is sent to the check provider (<Link to="/privacy">privacy policy</Link>).
            </p>
          </div>
        </aside>
      </div>
    </>
  )
}
