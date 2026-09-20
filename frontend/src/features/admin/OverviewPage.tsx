import { Link } from 'react-router-dom'

import type { AdminOverview, Checks, StatusCount, Today } from '@/api/admin'
import { Button, buttonClasses } from '@/features/shared/Button'
import { PageHeader } from '@/features/shared/PageHeader'
import { StatStrip } from '@/features/shared/StatStrip'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { formatDate, formatDateTime } from '@/lib/format'
import { useAdminOverview } from './queries'

const BAR_TONE: Record<string, string> = {
  info: 'bg-info',
  warning: 'bg-warning',
  success: 'bg-success',
  error: 'bg-error',
  neutral: 'bg-line-strong',
  primary: 'bg-primary',
}

function seconds(value: number | null): string {
  return value === null ? 'no runs yet' : `${value.toFixed(1)} s`
}

function Row({ label, value, muted }: { label: string; value: string | number; muted?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line py-2 last:border-b-0">
      <dt className="text-sm text-text-2">{label}</dt>
      <dd className={cn('text-sm font-semibold tabular-nums', muted ? 'text-text-3' : 'text-text')}>{value}</dd>
    </div>
  )
}

/** Applications by internal status: every status, drafts as one row the officers never see, a bar per row. */
function StatusTable({ counts }: { counts: StatusCount[] }) {
  const max = Math.max(1, ...counts.map((c) => c.count))
  return (
    <section className="pf-surface overflow-hidden" aria-labelledby="status-title">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line px-5 py-4">
        <div>
          <div className="pf-eyebrow">Applications by status</div>
          <h2 id="status-title" className="mt-1 text-[17px] font-semibold leading-6">
            Officer labels
          </h2>
        </div>
        <span className="text-xs text-text-3">{counts.length} statuses</span>
      </div>
      <table className="w-full text-sm">
        <thead className="sr-only">
          <tr>
            <th scope="col">Status</th>
            <th scope="col">Count</th>
            <th scope="col">Share</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {counts.map((c) => (
            <tr key={c.status} className={cn(c.count === 0 && 'text-text-3')}>
              <th scope="row" className="px-5 py-2.5 text-left font-normal">
                <span className="inline-flex items-center gap-2">
                  <span className={cn('h-[7px] w-[7px] rounded-full', BAR_TONE[c.tone] ?? 'bg-line-strong')} aria-hidden="true" />
                  {c.label}
                  {c.turn === 'draft' ? <span className="text-xs text-text-3">(not visible to officers)</span> : null}
                </span>
              </th>
              <td className="w-16 px-3 py-2.5 text-right font-semibold tabular-nums">{c.count}</td>
              <td className="hidden w-[36%] px-5 py-2.5 sm:table-cell">
                <div className="h-2 w-full overflow-hidden rounded-full bg-surface-3" aria-hidden="true">
                  <div
                    className={cn('h-2 rounded-full', BAR_TONE[c.tone] ?? 'bg-line-strong')}
                    style={{ width: `${(c.count / max) * 100}%` }}
                  />
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function ChecksPanel({ checks }: { checks: Checks }) {
  return (
    <section className="pf-surface" aria-labelledby="checks-title">
      <div className="flex items-baseline justify-between gap-3 border-b border-line px-5 py-4">
        <h2 id="checks-title" className="text-[17px] font-semibold leading-6">
          Document checks
        </h2>
        <span className="text-xs text-text-3">
          {checks.failed_or_unavailable} of {checks.runs} failed
        </span>
      </div>
      <div className="px-5 py-3">
        <dl>
          <Row label="Checks run" value={checks.runs} />
          <Row label="Verified" value={checks.verified} />
          <Row label="Issues found" value={checks.issues_found} />
          <Row label="Needs officer review" value={checks.needs_review} />
          <Row label="Could not read" value={checks.unreadable} />
          <Row label="Failed or unavailable" value={checks.failed_or_unavailable} />
          {checks.still_running > 0 ? <Row label="Still running" value={checks.still_running} muted /> : null}
          <Row label="Average time" value={seconds(checks.average_seconds)} />
          <Row label="Slowest 5 % of checks" value={seconds(checks.p95_seconds)} />
        </dl>
        <p className="mt-3 text-[13px] leading-[18px] text-text-3">
          Last 24 hours. Provider: {checks.provider}
          {checks.model ? `, ${checks.model}` : ''}. Checks are advisory: the decision is the officer's.
        </p>
      </div>
    </section>
  )
}

function TodayPanel({ today }: { today: Today }) {
  const share = today.runs_per_day_quota > 0 ? Math.min(1, today.runs_today / today.runs_per_day_quota) : 0
  return (
    <section className="pf-surface" aria-labelledby="today-title">
      <div className="flex items-baseline justify-between gap-3 border-b border-line px-5 py-4">
        <h2 id="today-title" className="text-[17px] font-semibold leading-6">
          Today
        </h2>
        <span className="text-xs text-text-3">Singapore calendar day, {formatDate(today.day)}</span>
      </div>
      <div className="px-5 py-3">
        <dl>
          <Row label="Submissions" value={today.submissions} />
          <Row label="Resubmissions" value={today.resubmissions} />
          <Row label="Checklists submitted" value={today.checklists_submitted} />
          <Row label="Clarification rounds sent" value={today.clarification_rounds} />
        </dl>
        <div className="mt-4 flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between gap-3 text-[13px]">
            <span className="font-medium">Document checks against the platform quota</span>
            <span className="tabular-nums text-text-3">
              {today.runs_today} of {today.runs_per_day_quota > 0 ? today.runs_per_day_quota.toLocaleString('en-SG') : 'no limit'}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3" aria-hidden="true">
            <div className={cn('h-1.5 rounded-full', share >= 0.8 ? 'bg-warning' : 'bg-info')} style={{ width: `${share * 100}%` }} />
          </div>
        </div>
      </div>
    </section>
  )
}

function IdleTable({ overview }: { overview: AdminOverview }) {
  const rows = overview.idle
  return (
    <section className="pf-surface overflow-hidden" aria-labelledby="idle-title">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line px-5 py-4">
        <div>
          <div className="pf-eyebrow">Idle for more than 7 days</div>
          <h2 id="idle-title" className="mt-1 text-[17px] font-semibold leading-6">
            Ten longest, in Singapore calendar days
          </h2>
        </div>
        <span className="text-xs text-text-3">
          {overview.totals.idle_over_7_days} {overview.totals.idle_over_7_days === 1 ? 'application' : 'applications'}
        </span>
      </div>
      {rows.length === 0 ? (
        <p className="px-5 py-5 text-sm text-text-2">
          Nothing has been idle for more than seven days. Every open application moved this week.
        </p>
      ) : (
        <ul className="divide-y divide-line">
          {rows.map((row) => (
            <li
              key={row.id}
              className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 px-5 py-3 sm:grid-cols-[130px_minmax(0,1fr)_200px_70px_120px_80px] sm:items-center"
            >
              <span className="font-mono text-[13px] text-text-2">{row.reference_no}</span>
              <span className="row-start-2 truncate text-sm sm:row-start-auto">
                {row.business_name ?? <span className="text-text-3">Business name not entered</span>}
              </span>
              <span className="row-start-3 sm:row-start-auto">
                <StatusBadge label={row.label} tone={row.tone} className="h-auto min-h-6 whitespace-normal py-0.5 text-left leading-4" />
              </span>
              <span className="text-right text-sm font-semibold tabular-nums text-primary">{row.days_idle} d</span>
              <span className="row-start-3 text-[13px] text-text-3 sm:row-start-auto" title={formatDateTime(row.last_activity_at)}>
                {formatDate(row.last_activity_at)}
              </span>
              <span className="row-start-1 col-start-2 text-right sm:row-start-auto sm:col-start-auto">
                <Link to={`/admin/applications/${row.id}`} className={buttonClasses('ghost', 'sm')}>
                  Open
                </Link>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

/** Operations overview (S-40, US-070): counts, the idle list, today's numbers and check health. */
export function AdminOverviewPage() {
  const overview = useAdminOverview()
  const data = overview.data
  const summary = data
    ? `${data.totals.applications} ${data.totals.applications === 1 ? 'application' : 'applications'} · ${data.totals.with_office} with the office · ${data.totals.waiting_on_operators} waiting on operators`
    : 'Is anything stuck, are the checks working.'

  return (
    <>
      <PageHeader
        eyebrow="Administrator"
        title="Operations overview"
        subtitle={summary}
        meta={data ? <span>Numbers as of {formatDateTime(data.as_of)} SGT · refreshes every 60 s</span> : null}
        actions={
          <Button
            variant="secondary"
            size="sm"
            loading={overview.isFetching && !overview.isPending}
            onClick={() => void overview.refetch()}
          >
            Refresh
          </Button>
        }
      />
      {overview.isPending ? (
        <div className="flex flex-col gap-5" aria-busy="true" aria-label="Loading overview">
          <div className="pf-surface grid grid-cols-2 gap-px lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="flex flex-col gap-2 px-5 py-4">
                <Skeleton className="h-8 w-12" />
                <Skeleton className="h-3 w-24" />
              </div>
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      ) : overview.isError ? (
        <ErrorPanel error={overview.error} onRetry={() => void overview.refetch()} />
      ) : (
        <Loaded data={overview.data} />
      )}
    </>
  )
}

function Loaded({ data }: { data: AdminOverview }) {
  return (
    <div className="flex flex-col gap-5">
      <StatStrip
        cells={[
          {
            value: data.totals.applications,
            label: 'Applications',
            context: `${data.totals.submitted} submitted, ${data.totals.drafts} drafts`,
          },
          { value: data.totals.with_office, label: 'With the office', context: 'Waiting on an officer' },
          { value: data.totals.waiting_on_operators, label: 'Waiting on operators', context: 'Resubmission or clarification' },
          {
            value: data.totals.idle_over_7_days,
            label: 'Idle over 7 days',
            context: data.idle[0] ? `Oldest since ${formatDate(data.idle[0].last_activity_at)}` : 'Nothing is stuck',
            hot: data.totals.idle_over_7_days > 0,
          },
        ]}
      />
      <div className="grid items-start gap-5 lg:grid-cols-2">
        <StatusTable counts={data.counts} />
        <div className="flex flex-col gap-5">
          <ChecksPanel checks={data.checks} />
          <TodayPanel today={data.today} />
        </div>
      </div>
      <IdleTable overview={data} />
    </div>
  )
}
