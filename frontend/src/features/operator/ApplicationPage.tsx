import { Link, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { buttonClasses } from '@/features/shared/Button'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { ApplicationHeader } from './ApplicationHeader'
import { CompletionCard } from './CompletionCard'
import { useApplication } from './queries'

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

  if (app.isPending) {
    return (
      <PageSkeleton label="Loading application">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
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

  return (
    <>
      <ApplicationHeader
        view={view}
        actions={
          view.can_edit ? (
            <>
              {view.can_submit ? (
                <Link to={`/app/applications/${id}/review`} className={buttonClasses('secondary')}>
                  Review and submit
                </Link>
              ) : null}
              <Link to={`/app/applications/${id}/form${nextSection ? `/${nextSection.key}` : ''}`} className={buttonClasses('primary')}>
                Continue application
              </Link>
            </>
          ) : undefined
        }
      />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section className="pf-surface overflow-hidden" aria-labelledby="sections-title">
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
              const state = s.complete ? 'Complete' : s.started ? 'Needs attention' : 'Not started'
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
                      s.complete ? 'text-success' : s.started ? 'text-warning' : 'text-text-3',
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
        <CompletionCard view={view} />
      </div>
    </>
  )
}
