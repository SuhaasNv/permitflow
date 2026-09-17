import { Link, useNavigate } from 'react-router-dom'

import type { ApplicationSummary } from '@/api/applications'
import { useAuth } from '@/features/auth/AuthContext'
import { Button } from '@/features/shared/Button'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { EmptyPanel, ErrorPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { formatDateTime, formatRelative, greeting } from '@/lib/format'
import { useApplications, useCreateApplication } from './queries'

function rowAction(app: ApplicationSummary): string {
  if (app.status_label === 'Draft') return 'Continue'
  if (app.status_tone === 'warning') return 'Respond'
  return 'View'
}

/** Presentation-only counts from the served status tone: drafts, waiting for you, with the licensing office. */
function summarise(apps: ApplicationSummary[]) {
  const drafts = apps.filter((a) => a.status_label === 'Draft').length
  const waiting = apps.filter((a) => a.status_tone === 'warning').length
  const decided = apps.filter((a) => a.status_tone === 'success' || a.status_tone === 'error').length
  const withOffice = apps.length - drafts - waiting - decided
  return { drafts, waiting, withOffice, decided }
}

function Row({ app }: { app: ApplicationSummary }) {
  const needsYou = app.status_tone === 'warning'
  return (
    <li>
      <Link
        to={`/app/applications/${app.id}`}
        className={cn(
          'group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 px-4 py-4 text-text no-underline sm:px-5',
          'md:grid-cols-[168px_minmax(0,1fr)_200px_120px_112px]',
          'transition-colors duration-[var(--dur-fast)] ease-[var(--ease-out)] hover:bg-surface-2 hover:text-text focus-visible:bg-surface-2',
        )}
      >
        <div className="min-w-0">
          <div className="font-mono text-[13px] font-medium tracking-[0.01em]">{app.reference_no}</div>
          <div className="text-xs text-text-3">
            {app.revision_count > 0 ? `Revision ${app.revision_count}` : `${app.percent}% complete`}
          </div>
        </div>
        <div className="col-span-2 min-w-0 md:col-span-1">
          <div className="truncate font-medium">
            {app.business_name ?? <span className="text-text-3">Business name not entered yet</span>}
          </div>
          <div className="truncate text-[13px] text-text-3">{app.premises_summary ?? app.licence_title}</div>
        </div>
        <div className="col-start-1 flex flex-wrap items-center gap-2 md:col-start-auto">
          <StatusBadge label={app.status_label} tone={app.status_tone} />
          {needsYou ? <span className="text-xs font-semibold text-warning">Action required</span> : null}
        </div>
        <div className="hidden text-[13px] tabular-nums text-text-2 md:block" title={formatDateTime(app.updated_at)}>
          {formatRelative(app.updated_at)}
        </div>
        <div className="col-start-2 row-start-1 justify-self-end md:col-start-auto md:row-start-auto">
          <span
            className={cn(
              'inline-flex h-8 items-center gap-1 rounded-md border px-3 text-[13px] font-semibold transition-[background-color,border-color,color] duration-[var(--dur-fast)]',
              needsYou ? 'border-transparent bg-primary text-white' : 'border-line-strong bg-surface text-text group-hover:border-text-3',
            )}
          >
            {rowAction(app)}
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
          </span>
        </div>
      </Link>
    </li>
  )
}

function ApplicationsList({ apps }: { apps: ApplicationSummary[] }) {
  return (
    <section className="pf-surface overflow-hidden" aria-labelledby="apps-title">
      <div className="flex items-center justify-between border-b border-line px-4 py-3.5 sm:px-5">
        <h2 id="apps-title" className="text-[15px] font-semibold">
          My applications
        </h2>
        <span className="text-xs text-text-3">Sorted by last update</span>
      </div>
      <div className="hidden grid-cols-[168px_minmax(0,1fr)_200px_120px_112px] gap-x-4 border-b border-line bg-surface-2 px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3 md:grid">
        <span>Reference</span>
        <span>Business</span>
        <span>Status</span>
        <span>Updated</span>
        <span />
      </div>
      <ul className="pf-stagger divide-y divide-line">
        {apps.map((app) => (
          <Row key={app.id} app={app} />
        ))}
      </ul>
    </section>
  )
}

export function OperatorDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const apps = useApplications()
  const create = useCreateApplication()
  const firstName = user?.full_name.split(' ').slice(-2).join(' ') ?? ''
  const summary = apps.data ? summarise(apps.data) : null

  const newApplication = (
    <Button
      loading={create.isPending}
      onClick={() =>
        create.mutate(undefined, {
          onSuccess: (view) => navigate(`/app/applications/${view.id}`),
        })
      }
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="M12 5v14M5 12h14" />
      </svg>
      New application
    </Button>
  )

  return (
    <>
      <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-[36px] leading-[1.05] sm:text-[42px]">
            {greeting()}, {firstName}
          </h1>
          {summary && apps.data && apps.data.length > 0 ? (
            <p className="mt-3 text-[15px] leading-[22px] text-text-2">
              <span className="font-semibold text-text">
                {apps.data.length} {apps.data.length === 1 ? 'application' : 'applications'}
              </span>
              {summary.waiting > 0 ? (
                <>
                  {' · '}
                  <span className="font-semibold text-warning">
                    {summary.waiting} {summary.waiting === 1 ? 'needs' : 'need'} your response
                  </span>
                </>
              ) : null}
              {summary.drafts > 0 ? ` · ${summary.drafts} ${summary.drafts === 1 ? 'draft' : 'drafts'}` : ''}
              {summary.withOffice > 0 ? ` · ${summary.withOffice} with the licensing office` : ''}
              {summary.decided > 0 ? ` · ${summary.decided} decided` : ''}
            </p>
          ) : (
            <p className="mt-3 text-[15px] leading-[22px] text-text-2">Here is what needs your attention today.</p>
          )}
        </div>
        <div className="shrink-0">{newApplication}</div>
      </div>
      {create.isError ? (
        <div className="mb-4">
          <ErrorPanel error={create.error} onRetry={() => create.reset()} />
        </div>
      ) : null}
      {apps.isPending ? (
        <div className="pf-surface overflow-hidden" aria-busy="true" aria-label="Loading applications">
          <div className="border-b border-line px-5 py-4">
            <Skeleton className="h-4 w-32" />
          </div>
          {[0, 1, 2].map((i) => (
            <div key={i} className="grid grid-cols-[168px_minmax(0,1fr)_200px_120px] gap-4 border-b border-line px-5 py-5 last:border-b-0">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-3/5" />
              <Skeleton className="h-5 w-24 rounded-full" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      ) : apps.isError ? (
        <ErrorPanel error={apps.error} onRetry={() => void apps.refetch()} />
      ) : apps.data.length === 0 ? (
        <EmptyPanel
          title="No applications yet"
          description="Start a new application to apply for a Food Establishment Licence. It takes about 20 minutes and you can save a draft at any point."
          action={newApplication}
        />
      ) : (
        <ApplicationsList apps={apps.data} />
      )}
    </>
  )
}
