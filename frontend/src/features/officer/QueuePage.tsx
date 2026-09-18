import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import type { QueueItem } from '@/api/officer'
import { PageHeader } from '@/features/shared/PageHeader'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { EmptyPanel, ErrorPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { formatDate, formatDateTime, formatRelative } from '@/lib/format'
import { useQueue } from './queries'

type Filter = 'all' | 'mine' | 'operator' | 'decided'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'mine', label: 'Needs review' },
  { key: 'operator', label: 'Waiting on operator' },
  { key: 'decided', label: 'Decided' },
  { key: 'all', label: 'All' },
]

function bucket(item: QueueItem): Exclude<Filter, 'all'> {
  if (item.decided) return 'decided'
  return item.officer_turn ? 'mine' : 'operator'
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

function ChecksCell({ item }: { item: QueueItem }) {
  if (item.documents_checking > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[13px] text-info">
        <span className="relative flex h-[7px] w-[7px]" aria-hidden="true">
          <span className="absolute inset-0 animate-ping rounded-full bg-current opacity-60" />
          <span className="relative h-[7px] w-[7px] rounded-full bg-current" />
        </span>
        Checking {item.documents_checking}
      </span>
    )
  }
  if (item.documents_attention > 0) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[13px] font-medium text-warning">
        <span className="h-[7px] w-[7px] rounded-full bg-current" aria-hidden="true" />
        {item.documents_attention} to check
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-[13px] text-text-3">
      <span className="h-[7px] w-[7px] rounded-full bg-success" aria-hidden="true" />
      Clear
    </span>
  )
}

function Row({ item }: { item: QueueItem }) {
  const mine = item.officer_turn
  return (
    <li>
      <Link
        to={`/officer/applications/${item.id}`}
        className={cn(
          'group grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 px-4 py-4 text-text no-underline sm:px-5',
          'lg:grid-cols-[130px_minmax(0,1fr)_200px_130px] xl:grid-cols-[150px_minmax(0,1fr)_230px_130px_120px_150px]',
          'transition-colors duration-[var(--dur-fast)] ease-[var(--ease-out)] hover:bg-surface-2 hover:text-text focus-visible:bg-surface-2',
        )}
      >
        <div className="min-w-0">
          <div className="font-mono text-[13px] font-medium tracking-[0.01em]">{item.reference_no}</div>
          <div className="text-xs text-text-3">
            Revision {item.revision_count}
            {item.open_feedback_count > 0 ? ` · ${item.open_feedback_count} open` : ''}
          </div>
        </div>
        <div className="col-span-2 min-w-0 lg:col-span-1">
          <div className="truncate font-medium">{item.business_name ?? <span className="text-text-3">Business name not entered</span>}</div>
          <div className="truncate text-[13px] text-text-3">
            {item.applicant_name}
            {item.premises_summary ? ` · ${item.premises_summary}` : ''}
            <span className="xl:hidden"> · {formatRelative(item.last_activity_at)}</span>
          </div>
        </div>
        <div className="col-start-1 lg:col-start-auto">
          <StatusBadge label={item.status_label} tone={item.status_tone} />
          <div className="mt-1.5 hidden lg:block xl:hidden">
            <ChecksCell item={item} />
          </div>
        </div>
        <div className="hidden xl:block">
          <ChecksCell item={item} />
        </div>
        <div className="hidden text-[13px] tabular-nums text-text-2 xl:block" title={formatDateTime(item.last_activity_at)}>
          <div>{formatRelative(item.last_activity_at)}</div>
          {item.submitted_at ? <div className="text-xs text-text-3">Submitted {formatDate(item.submitted_at)}</div> : null}
        </div>
        <div className="col-start-2 row-start-1 justify-self-end lg:col-start-auto lg:row-start-auto">
          <span
            className={cn(
              'inline-flex h-8 items-center gap-1 whitespace-nowrap rounded-md border px-3 text-[13px] font-semibold transition-[background-color,border-color,color] duration-[var(--dur-fast)]',
              mine ? 'border-transparent bg-ink text-white' : 'border-line-strong bg-surface text-text-2 group-hover:border-text-3',
            )}
          >
            {item.next_action}
            {mine ? ArrowIcon : null}
          </span>
        </div>
      </Link>
    </li>
  )
}

/** Officer work queue (S-20): every submitted application, grouped by whose turn it is. */
export function OfficerQueuePage() {
  const queue = useQueue()
  const [filter, setFilter] = useState<Filter>('mine')

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: 0, mine: 0, operator: 0, decided: 0 }
    for (const item of queue.data?.items ?? []) {
      c.all += 1
      c[bucket(item)] += 1
    }
    return c
  }, [queue.data])

  const shown = (queue.data?.items ?? []).filter((i) => filter === 'all' || bucket(i) === filter)
  const summary = queue.data
    ? `${queue.data.officer_turn_count} ${queue.data.officer_turn_count === 1 ? 'needs' : 'need'} review · ${queue.data.waiting_on_operator_count} waiting on operators · ${queue.data.decided_count} decided`
    : 'Submitted applications, newest activity first.'

  return (
    <>
      <PageHeader
        eyebrow="Licensing officer"
        title="Review queue"
        subtitle={summary}
        meta={
          queue.dataUpdatedAt ? (
            <span>Refreshed {formatRelative(new Date(queue.dataUpdatedAt).toISOString())} · updates every 30 s</span>
          ) : null
        }
      />
      {queue.isPending ? (
        <div className="pf-surface overflow-hidden" aria-busy="true" aria-label="Loading queue">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="grid grid-cols-[150px_minmax(0,1fr)_230px_140px] gap-4 border-b border-line px-5 py-5 last:border-b-0">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-4 w-3/5" />
              <Skeleton className="h-5 w-32 rounded-full" />
              <Skeleton className="h-4 w-16" />
            </div>
          ))}
        </div>
      ) : queue.isError ? (
        <ErrorPanel error={queue.error} onRetry={() => void queue.refetch()} />
      ) : queue.data.items.length === 0 ? (
        <EmptyPanel
          done
          title="Nothing has been submitted yet"
          description="Applications appear here the moment an operator submits. Nothing is required from you right now."
          footnote="Updates every 30 seconds"
        />
      ) : (
        <section className="pf-surface overflow-hidden" aria-label="Review queue">
          <div
            className="flex flex-wrap items-center gap-1 border-b border-line px-3 py-2.5 sm:px-4"
            role="tablist"
            aria-label="Filter queue"
          >
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                role="tab"
                aria-selected={filter === f.key}
                onClick={() => setFilter(f.key)}
                className={cn(
                  'inline-flex h-8 items-center gap-1.5 rounded-md px-3 text-[13px] font-medium transition-colors duration-[var(--dur-fast)]',
                  filter === f.key ? 'bg-surface-3 text-text' : 'text-text-2 hover:bg-neutral-soft hover:text-text',
                )}
              >
                {f.label}
                <span className="font-mono text-[11px] text-text-3">{counts[f.key]}</span>
              </button>
            ))}
          </div>
          <div className="hidden grid-cols-[130px_minmax(0,1fr)_200px_130px] gap-x-4 border-b border-line bg-surface-2 px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3 lg:grid xl:grid-cols-[150px_minmax(0,1fr)_230px_130px_120px_150px]">
            <span>Reference</span>
            <span>Business · applicant</span>
            <span>
              Status<span className="xl:hidden"> · checks</span>
            </span>
            <span className="hidden xl:block">Document checks</span>
            <span className="hidden xl:block">Last activity</span>
            <span />
          </div>
          {shown.length === 0 ? (
            <p className="px-5 py-12 text-center text-sm text-text-2">
              {filter === 'mine' ? 'You are all caught up. Nothing is waiting for your review.' : 'No applications match this filter.'}
            </p>
          ) : (
            <ul key={filter} className="pf-stagger divide-y divide-line">
              {shown.map((item) => (
                <Row key={item.id} item={item} />
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  )
}
