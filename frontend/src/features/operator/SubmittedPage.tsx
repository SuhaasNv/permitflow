import { Link, Navigate, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { buttonClasses } from '@/features/shared/Button'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, Skeleton } from '@/features/shared/states'
import { formatDateTime } from '@/lib/format'
import { useApplication } from './queries'

const STEPS: [string, string, string][] = [
  [
    'Officer review',
    'A licensing officer reviews your form and documents. You will be notified if changes are needed.',
    'You will see the status change here',
  ],
  ['Site visit', 'If the review is satisfactory, an officer will contact you to arrange a visit to the premises.', 'After review'],
  ['Outcome', 'The final decision appears on this page and on your dashboard.', 'After the site visit'],
]

export function SubmittedPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  if (app.isPending) return <Skeleton className="mx-auto h-72 max-w-3xl" />
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  const view = app.data
  if (view.revision_count === 0) return <Navigate to={`/app/applications/${id}`} replace />
  return (
    <div className="mx-auto max-w-3xl pt-4 sm:pt-8">
      <div className="pf-stagger text-center" role="status">
        <span className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-success text-white">
          <svg
            width="30"
            height="30"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path className="pf-check" d="M20 6 9 17l-5-5" />
          </svg>
        </span>
        <h1 className="font-display text-[44px] leading-[1.05] sm:text-[52px]">Application submitted</h1>
        <p className="mx-auto mt-4 max-w-[52ch] text-[16px] leading-6 text-text-2">
          Your Food Establishment Licence application has been received by the licensing office. A copy of everything you entered and
          uploaded is kept as Revision 1.
        </p>
        <dl className="mx-auto mt-8 grid max-w-[560px] grid-cols-1 divide-y divide-line border-y border-line text-left sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <div className="px-5 py-4">
            <dt className="pf-eyebrow mb-1">Reference</dt>
            <dd className="font-mono text-[17px] font-medium">{view.reference_no}</dd>
          </div>
          <div className="px-5 py-4">
            <dt className="pf-eyebrow mb-1.5">Status</dt>
            <dd>
              <StatusBadge label={view.status_label} tone={view.status_tone} />
            </dd>
          </div>
          <div className="px-5 py-4">
            <dt className="pf-eyebrow mb-1">Last updated</dt>
            <dd className="text-[15px] font-medium tabular-nums">{formatDateTime(view.updated_at)}</dd>
          </div>
        </dl>
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          <Link to={`/app/applications/${id}`} className={buttonClasses('primary')}>
            View application
          </Link>
          <Link to="/app/dashboard" className={buttonClasses('secondary')}>
            Back to dashboard
          </Link>
        </div>
      </div>
      <section className="pf-surface mt-12 px-6 py-6 sm:px-8" aria-labelledby="next-title">
        <h2 id="next-title" className="mb-5 text-[17px] font-semibold">
          What happens next
        </h2>
        <ol className="flex flex-col">
          <li className="relative grid grid-cols-[28px_minmax(0,1fr)] gap-4 pb-6 before:absolute before:bottom-0 before:left-[13px] before:top-7 before:w-px before:bg-line">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-success text-white">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <div>
              <div className="text-[15px] font-semibold">Submitted · Revision {view.revision_count} recorded</div>
              <div className="mt-0.5 text-[13px] leading-[19px] text-text-2">
                The snapshot cannot be changed. Later revisions are compared against it.
              </div>
              <div className="mt-1 text-xs text-text-3">{formatDateTime(view.updated_at)}</div>
            </div>
          </li>
          {STEPS.map(([title, desc, when], i) => (
            <li
              key={title}
              className={`relative grid grid-cols-[28px_minmax(0,1fr)] gap-4 ${i < STEPS.length - 1 ? 'pb-6 before:absolute before:bottom-0 before:left-[13px] before:top-7 before:w-px before:bg-line' : ''}`}
            >
              <span
                className="flex h-7 w-7 items-center justify-center rounded-full border-[1.5px] border-line-strong bg-surface font-mono text-xs text-text-3"
                aria-hidden="true"
              >
                {i + 2}
              </span>
              <div>
                <div className="text-[15px] font-semibold">{title}</div>
                <div className="mt-0.5 text-[13px] leading-[19px] text-text-2">{desc}</div>
                <div className="mt-1 text-xs text-text-3">{when}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
