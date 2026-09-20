import { useState } from 'react'
import { Link } from 'react-router-dom'

import type { FeedEvent } from '@/api/admin'
import { Button } from '@/features/shared/Button'
import { PageHeader } from '@/features/shared/PageHeader'
import { EmptyPanel, ErrorPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'
import { useAuditFeed } from './queries'

const FAMILY: Record<string, { label: string; tone: string }> = {
  application: { label: 'Application', tone: 'bg-ink' },
  section: { label: 'Section', tone: 'bg-line-strong' },
  document: { label: 'Document', tone: 'bg-line-strong' },
  verification: { label: 'Check', tone: 'bg-success' },
  revision: { label: 'Revision', tone: 'bg-ink' },
  status: { label: 'Status', tone: 'bg-info' },
  feedback: { label: 'Feedback', tone: 'bg-warning' },
  site_visit: { label: 'Site visit', tone: 'bg-info' },
  checklist: { label: 'Checklist', tone: 'bg-success' },
  clarification: { label: 'Clarification', tone: 'bg-warning' },
  licence: { label: 'Licence', tone: 'bg-success' },
  user: { label: 'User', tone: 'bg-primary' },
}

export function family(type: string): string {
  return type.split('.')[0] ?? type
}

function who(e: FeedEvent): string {
  if (!e.actor_name) return 'System'
  const role = e.actor_role === 'admin' ? 'administrator' : e.actor_role === 'officer' ? 'officer' : 'operator'
  return `${e.actor_name} · ${role}`
}

/** Activity (S-42, US-072): the newest audit events across every application and every user change. */
export function AdminActivityPage() {
  const feed = useAuditFeed()
  const [filter, setFilter] = useState('all')
  const events = feed.data?.pages.flatMap((p) => p.events) ?? []
  const families = [...new Set(events.map((e) => family(e.event_type)))]
  const shown = events.filter((e) => filter === 'all' || family(e.event_type) === filter)

  return (
    <>
      <PageHeader
        eyebrow="Administrator"
        title="Activity"
        subtitle="The latest audit events across every application and every user change."
        meta={<span>Append-only. Nothing here can be edited or removed.</span>}
      />
      {feed.isPending ? (
        <div className="pf-surface flex flex-col gap-3 px-5 py-6" aria-busy="true" aria-label="Loading activity">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
        </div>
      ) : feed.isError ? (
        <ErrorPanel error={feed.error} onRetry={() => void feed.refetch()} />
      ) : events.length === 0 ? (
        <EmptyPanel
          title="Nothing has happened yet"
          description="Events appear here the moment anyone acts on an application or an account."
        />
      ) : (
        <section className="pf-surface overflow-hidden" aria-label="Activity">
          <div className="flex flex-wrap items-center gap-1 border-b border-line px-3 py-2 sm:px-4" role="group" aria-label="Event family">
            {['all', ...families].map((f) => (
              <button
                key={f}
                type="button"
                aria-pressed={filter === f}
                onClick={() => setFilter(f)}
                className={cn(
                  'inline-flex h-10 items-center rounded-md px-2.5 text-[12px] font-medium transition-colors duration-[var(--dur-fast)] sm:h-7',
                  filter === f ? 'bg-surface-3 text-text' : 'text-text-2 hover:bg-neutral-soft hover:text-text',
                )}
              >
                {f === 'all' ? `All ${events.length}` : (FAMILY[f]?.label ?? f)}
              </button>
            ))}
          </div>
          <ol className="divide-y divide-line">
            {shown.map((e) => (
              <li
                key={e.id}
                className="grid grid-cols-[16px_minmax(0,1fr)] gap-x-3 px-5 py-3 sm:px-6 xl:grid-cols-[16px_110px_170px_minmax(0,1fr)_180px_120px]"
              >
                <span
                  className={cn('mt-[7px] h-[7px] w-[7px] rounded-full', FAMILY[family(e.event_type)]?.tone ?? 'bg-line-strong')}
                  aria-hidden="true"
                />
                <span className="text-[12px] leading-[22px] tabular-nums text-text-3">{formatDateTime(e.created_at)}</span>
                <span className="col-start-2 min-w-0 break-all font-mono text-[12px] leading-[22px] text-text-3 xl:col-start-3">
                  {e.event_type}
                </span>
                <span className="col-start-2 text-sm leading-[22px] xl:col-start-4">{e.summary}</span>
                <span className="col-start-2 text-[12px] leading-[22px] text-text-3 xl:col-start-5">{who(e)}</span>
                <span className="col-start-2 text-[12px] leading-[22px] xl:col-start-6 xl:text-right">
                  {e.application_id && e.reference_no ? (
                    <Link to={`/admin/applications/${e.application_id}`} className="font-mono text-text no-underline hover:underline">
                      {e.reference_no}
                    </Link>
                  ) : (
                    <span className="text-text-3">no case</span>
                  )}
                </span>
              </li>
            ))}
          </ol>
          <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
            <span className="text-xs text-text-3">
              {events.length} {events.length === 1 ? 'event' : 'events'} loaded
              {filter !== 'all' ? `, ${shown.length} shown` : ''}
            </span>
            {feed.hasNextPage ? (
              <Button variant="ghost" size="sm" loading={feed.isFetchingNextPage} onClick={() => void feed.fetchNextPage()}>
                Show older activity
              </Button>
            ) : (
              <span className="text-xs text-text-3">That is everything.</span>
            )}
          </div>
        </section>
      )}
    </>
  )
}
