import { Link, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, Skeleton } from '@/features/shared/states'
import { formatDateTime } from '@/lib/format'
import { useApplication } from './queries'

const STEPS = [
  [
    'Officer review',
    'A licensing officer reviews your form and documents. You will be notified if changes are needed.',
    'Typically within 10 working days',
  ],
  ['Site visit', 'If the review is satisfactory, an officer will contact you to arrange a visit to the premises.', 'After review'],
  ['Outcome', 'You will be notified of the final decision here and by email.', 'After the site visit'],
]

export function SubmittedPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  if (app.isPending) return <Skeleton className="mx-auto h-40 max-w-2xl" />
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  const view = app.data
  return (
    <div className="mx-auto mt-6 max-w-2xl">
      <section className="rounded-lg border border-line bg-surface px-6 py-10 text-center shadow-[var(--shadow-1)] sm:px-10" role="status">
        <span className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full border border-success-line bg-success-soft text-success">
          <svg
            width="26"
            height="26"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M20 6 9 17l-5-5" />
          </svg>
        </span>
        <h1 className="text-[26px] font-semibold leading-8 tracking-tight">Application submitted</h1>
        <p className="mt-1.5 text-text-2">Your Food Establishment Licence application has been received by the licensing office.</p>
        <div className="mx-auto mt-6 inline-flex flex-wrap items-center justify-center gap-x-6 gap-y-3 rounded-lg border border-line bg-surface-2 px-5 py-3 text-left">
          <div>
            <div className="text-xs text-text-3">Reference number</div>
            <div className="font-mono text-lg font-semibold">{view.reference_no}</div>
          </div>
          <div>
            <div className="text-xs text-text-3">Status</div>
            <StatusBadge label={view.status_label} tone={view.status_tone} />
          </div>
          <div>
            <div className="text-xs text-text-3">Submitted</div>
            <div className="font-semibold tabular-nums">{formatDateTime(view.updated_at)}</div>
          </div>
        </div>
        <div className="mt-7 flex flex-wrap justify-center gap-2">
          <Link
            to={`/app/applications/${id}`}
            className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-semibold text-white no-underline hover:bg-primary-hover hover:text-white"
          >
            View application
          </Link>
          <Link
            to="/app/dashboard"
            className="inline-flex h-10 items-center rounded-md border border-line-strong bg-surface px-4 text-sm font-semibold text-text no-underline shadow-[var(--shadow-1)] hover:bg-surface-2"
          >
            Back to dashboard
          </Link>
        </div>
      </section>
      <section className="mt-5 rounded-lg border border-line bg-surface px-6 py-5 shadow-[var(--shadow-1)]">
        <h2 className="mb-3 text-base font-semibold">What happens next</h2>
        <ol className="flex flex-col">
          <li className="relative grid grid-cols-[24px_minmax(0,1fr)] gap-3 pb-5 before:absolute before:bottom-0 before:left-[11px] before:top-6 before:w-px before:bg-line">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-success text-white">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <div>
              <div className="text-sm font-semibold">Submitted: Revision 1 recorded</div>
              <div className="text-[13px] text-text-2">
                A copy of everything you entered and uploaded is kept as Revision 1. It cannot be changed.
              </div>
              <div className="mt-1 text-xs text-text-3">{formatDateTime(view.updated_at)}</div>
            </div>
          </li>
          {STEPS.map(([title, desc, when], i) => (
            <li
              key={title}
              className={`relative grid grid-cols-[24px_minmax(0,1fr)] gap-3 ${i < STEPS.length - 1 ? 'pb-5 before:absolute before:bottom-0 before:left-[11px] before:top-6 before:w-px before:bg-line' : ''}`}
            >
              <span
                className="flex h-6 w-6 items-center justify-center rounded-full border-[1.5px] border-line-strong bg-surface"
                aria-hidden="true"
              />
              <div>
                <div className="text-sm font-semibold">{title}</div>
                <div className="text-[13px] text-text-2">{desc}</div>
                <div className="mt-1 text-xs text-text-3">{when}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
