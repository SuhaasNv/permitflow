import { useState } from 'react'

import type { AuditEvent } from '@/api/officer'
import { Button } from '@/features/shared/Button'
import { Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'
import { useAuditTrail } from './queries'

const FAMILY: Record<string, { label: string; tone: string }> = {
  status: { label: 'Status', tone: 'bg-info' },
  revision: { label: 'Revision', tone: 'bg-ink' },
  feedback: { label: 'Feedback', tone: 'bg-warning' },
  document: { label: 'Document', tone: 'bg-line-strong' },
  verification: { label: 'Check', tone: 'bg-success' },
  section: { label: 'Section', tone: 'bg-line-strong' },
  application: { label: 'Application', tone: 'bg-ink' },
}

function family(type: string): string {
  return type.split('.')[0] ?? type
}

/** Append-only audit trail (S-25, FR-025): every event with actor, time and a plain sentence; filter by family. */
export function AuditTrail({ applicationId }: { applicationId: string }) {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState<string>('all')
  const audit = useAuditTrail(applicationId, open)
  const events = audit.data?.events ?? []
  const families = [...new Set(events.map((e) => family(e.event_type)))]
  const shown = events.filter((e) => filter === 'all' || family(e.event_type) === filter)

  return (
    <section className="pf-surface overflow-hidden" aria-labelledby="audit-title">
      <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-4 sm:px-7">
        <h2 id="audit-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
          Audit trail
        </h2>
        <span className="text-xs text-text-3">Append-only. Nothing here can be edited or removed.</span>
        <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
          {open ? 'Hide' : 'Show'}
        </Button>
      </div>
      {!open ? null : audit.isPending ? (
        <div className="flex flex-col gap-3 px-5 py-6 sm:px-7" aria-busy="true" aria-label="Loading audit trail">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
        </div>
      ) : audit.isError ? (
        <p className="px-5 py-6 text-sm text-error sm:px-7">Could not load the audit trail. Try again.</p>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-1 border-b border-line px-3 py-2 sm:px-5" role="group" aria-label="Filter events">
            {['all', ...families].map((f) => (
              <button
                key={f}
                type="button"
                aria-pressed={filter === f}
                onClick={() => setFilter(f)}
                className={cn(
                  'inline-flex h-9 items-center rounded-md px-2.5 text-[12px] font-medium transition-colors duration-[var(--dur-fast)] sm:h-7',
                  filter === f ? 'bg-surface-3 text-text' : 'text-text-2 hover:bg-neutral-soft hover:text-text',
                )}
              >
                {f === 'all' ? `All ${events.length}` : (FAMILY[f]?.label ?? f)}
              </button>
            ))}
          </div>
          <ol className="divide-y divide-line">
            {shown.map((e: AuditEvent) => (
              <li
                key={e.id}
                className="grid grid-cols-[16px_minmax(0,1fr)] gap-x-3 px-5 py-3 sm:px-7 xl:grid-cols-[16px_170px_minmax(0,1fr)_200px]"
              >
                <span
                  className={cn('mt-[7px] h-[7px] w-[7px] rounded-full', FAMILY[family(e.event_type)]?.tone ?? 'bg-line-strong')}
                  aria-hidden="true"
                />
                <span className="font-mono text-[12px] leading-[22px] text-text-3">{e.event_type}</span>
                <span className="col-start-2 text-sm xl:col-start-3">{e.summary}</span>
                <span className="col-start-2 text-[12px] text-text-3 xl:col-start-4 xl:text-right">
                  {e.actor_name ? `${e.actor_name} (${e.actor_role})` : 'System'} · {formatDateTime(e.created_at)}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  )
}
