import { Link } from 'react-router-dom'

import type { ApplicationSummary } from '@/api/applications'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { cn } from '@/lib/cn'
import { formatDateTime, formatRelative } from '@/lib/format'

function rowAction(app: ApplicationSummary): string {
  if (app.status_label === 'Draft') return 'Continue'
  if (app.needs_operator_action) return 'Respond'
  return 'View'
}

/** Presentation-only grouping from the served status tone and label. The server owns the vocabulary. */
export type Bucket = 'waiting' | 'draft' | 'office' | 'decided'

export function bucketOf(app: ApplicationSummary): Bucket {
  if (app.needs_operator_action) return 'waiting'
  if (app.status_label === 'Draft') return 'draft'
  if (app.status_tone === 'success' || app.status_tone === 'error') return 'decided'
  return 'office'
}

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

/** One application as a table-like row (My applications). Whole row is the link. */
export function ApplicationRow({ app }: { app: ApplicationSummary }) {
  const needsYou = app.needs_operator_action
  return (
    <li>
      <Link
        to={`/app/applications/${app.id}`}
        className={cn(
          'group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 px-4 py-4 text-text no-underline sm:px-5',
          'md:grid-cols-[168px_minmax(0,1fr)_220px_120px_112px]',
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
            {ArrowIcon}
          </span>
        </div>
      </Link>
    </li>
  )
}

/** One application as a compact work card (Dashboard): what it is, where it stands, what to do next. */
export function ApplicationCard({ app }: { app: ApplicationSummary }) {
  const needsYou = app.needs_operator_action
  const draft = app.status_label === 'Draft'
  return (
    <li>
      <Link
        to={`/app/applications/${app.id}`}
        className={cn(
          'group flex h-full flex-col gap-3 rounded-lg border bg-surface p-4 text-text no-underline',
          'transition-[border-color,background-color,transform] duration-[var(--dur-fast)] ease-[var(--ease-out)] hover:-translate-y-px hover:text-text',
          needsYou ? 'border-warning-line hover:border-warning' : 'border-line hover:border-line-strong',
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-mono text-xs text-text-3">{app.reference_no}</div>
            <div className="mt-0.5 truncate text-[15px] font-semibold leading-[22px]">
              {app.business_name ?? <span className="font-medium text-text-3">Business name not entered yet</span>}
            </div>
          </div>
          <StatusBadge label={app.status_label} tone={app.status_tone} />
        </div>
        {draft ? (
          <div>
            <div className="h-1 overflow-hidden rounded-full bg-surface-3">
              <div
                className="h-full rounded-full bg-text transition-[width] duration-[600ms] ease-[var(--ease-out)]"
                style={{ width: `${app.percent}%` }}
              />
            </div>
            <div className="mt-1.5 text-xs text-text-3">{app.percent}% complete</div>
          </div>
        ) : (
          <div className="text-[13px] text-text-2">{app.premises_summary ?? app.licence_title}</div>
        )}
        <div className="mt-auto flex items-center justify-between text-xs text-text-3">
          <span title={formatDateTime(app.updated_at)}>Updated {formatRelative(app.updated_at)}</span>
          <span className={cn('inline-flex items-center gap-1 text-[13px] font-semibold', needsYou ? 'text-primary' : 'text-text')}>
            {rowAction(app)}
            {ArrowIcon}
          </span>
        </div>
      </Link>
    </li>
  )
}
