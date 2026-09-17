import { Link, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { PageHeader } from '@/features/shared/PageHeader'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, Skeleton } from '@/features/shared/states'
import { formatDate } from '@/lib/format'
import { useApplication } from './queries'

export function ApplicationPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)

  if (app.isPending) {
    return (
      <div className="flex flex-col gap-3" aria-busy="true" aria-label="Loading application">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="mt-4 h-24 w-full" />
      </div>
    )
  }
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404) {
      return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
    }
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  const view = app.data
  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-2 text-[13px] text-text-3">
        <Link to="/app/dashboard" className="text-text-2">
          My applications
        </Link>
        <span aria-hidden="true">›</span>
        <span className="text-text">{view.reference_no}</span>
      </nav>
      <PageHeader title={`${view.reference_no} · ${view.licence_title}`} subtitle={view.status_explanation} />
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-line bg-surface px-5 py-3.5 shadow-[var(--shadow-1)]">
        <StatusBadge label={view.status_label} tone={view.status_tone} size="lg" />
        <span className="text-sm text-text-2">{view.status_explanation}</span>
        <span className="ml-auto text-xs tabular-nums text-text-3">Created {formatDate(view.created_at)}</span>
      </div>
      <ul className="mt-5 grid gap-3 sm:grid-cols-2">
        {view.sections.map((s) => (
          <li key={s.key} className="rounded-lg border border-line bg-surface p-4">
            <div className="font-semibold">{s.title}</div>
            <div className="text-[13px] text-text-3">{s.description}</div>
            <div className="mt-2 text-xs text-text-2">{s.complete ? 'Complete' : s.started ? 'Needs attention' : 'Not started'}</div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-[13px] text-text-3">The form editor arrives with the next story (US-011).</p>
    </>
  )
}
