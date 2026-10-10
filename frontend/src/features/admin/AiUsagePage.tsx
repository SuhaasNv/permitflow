import { useInfiniteQuery } from '@tanstack/react-query'
import { useId, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import type { AiUsageQuery, AiUsageRow } from '@/api/aiUsage'
import { downloadAiUsageCsv, getAiUsage } from '@/api/aiUsage'
import { Button } from '@/features/shared/Button'
import { inputClasses } from '@/features/shared/Field'
import { PageHeader } from '@/features/shared/PageHeader'
import type { Tone } from '@/features/shared/StatusBadge'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { formatDate, formatDateTime, todayInSingapore } from '@/lib/format'
import { useAdminUsers } from './queries'

type Range = 'today' | '7' | '30' | 'custom'

const RANGES: { value: Range; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: '7', label: '7 days' },
  { value: '30', label: '30 days' },
  { value: 'custom', label: 'Custom' },
]

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const DAY = /^\d{4}-\d{2}-\d{2}$/

const OUTCOMES: Record<string, { label: string; tone: Tone }> = {
  verified: { label: 'Verified', tone: 'success' },
  issues_found: { label: 'Issues found', tone: 'warning' },
  needs_review: { label: 'Needs officer review', tone: 'warning' },
  unreadable: { label: 'Could not read', tone: 'neutral' },
  failed: { label: 'Check failed', tone: 'error' },
  dead: { label: 'Check failed', tone: 'error' },
  unavailable: { label: 'Check unavailable', tone: 'neutral' },
  pending: { label: 'Waiting', tone: 'neutral' },
  running: { label: 'Checking', tone: 'info' },
}

const DOCUMENT_TYPES: Record<string, string> = {
  business_profile: 'Business profile (ACRA)',
  floor_plan: 'Floor plan',
  tenancy_agreement: 'Tenancy agreement',
  food_hygiene_certificate: 'Food hygiene certificate',
}

const number = new Intl.NumberFormat('en-GB')

/** US dollars exactly as stored: "0.00160000" is US$0.0016, "0.64000000" is US$0.64 (no rounding, no float). */
export function usd(value: string): string {
  const [whole = '0', fraction = ''] = value.split('.')
  return `US$${number.format(Number(whole))}.${fraction.replace(/0+$/, '').padEnd(2, '0')}`
}

const seconds = (ms: number): string => `${(ms / 1000).toFixed(1)} s`

function shift(day: string, by: number): string {
  const d = new Date(`${day}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + by)
  return d.toISOString().slice(0, 10)
}

/** The Singapore days a range names; a custom range is whatever the two dates hold. */
function span(range: Range, from: string, to: string, today: string = todayInSingapore()): { from: string; to: string } {
  if (range === 'custom') return { from, to }
  return { from: range === 'today' ? today : shift(today, range === '7' ? -6 : -29), to: today }
}

/** The one pulse placeholder: flat, no gradient, still under reduced motion. */
function Pulse({ className }: { className: string }) {
  return <span className={cn('block animate-pulse rounded-md bg-surface-3 motion-reduce:animate-none', className)} aria-hidden="true" />
}

const COLUMNS = `min-[1400px]:grid-cols-[104px_minmax(0,1fr)_minmax(0,1.25fr)_minmax(0,1.05fr)_160px_70px_84px_64px] min-[1400px]:gap-x-4`
const ROW = `grid grid-cols-1 gap-x-3 gap-y-1.5 px-4 py-3.5 min-[768px]:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] min-[768px]:items-center min-[768px]:px-6 ${COLUMNS} min-[1400px]:py-3`
// At tablet width the cells sit in a 3 x 3 grid; at the wide table every cell takes the next column.
const AT = `min-[1400px]:col-auto min-[1400px]:row-auto min-[1400px]:row-span-1`
const CELL = {
  time: `min-[768px]:col-start-1 min-[768px]:row-start-1 ${AT}`,
  person: `min-[768px]:col-start-1 min-[768px]:row-start-2 ${AT}`,
  app: `min-[768px]:col-start-2 min-[768px]:row-start-1 ${AT}`,
  doc: `min-[768px]:col-start-2 min-[768px]:row-start-2 ${AT}`,
  out: `min-[768px]:col-start-3 min-[768px]:row-start-1 min-[768px]:row-span-2 ${AT}`,
  metric: `min-[768px]:row-start-3 ${AT} min-[1400px]:justify-end min-[1400px]:text-sm`,
}

function Metric({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span role="cell" className={cn('inline-flex items-baseline gap-1.5 text-[13px] text-text-2 tabular-nums', CELL.metric)}>
      <span className={`text-xs text-text-3 min-[1400px]:hidden`}>{label}</span>
      {children}
    </span>
  )
}

function Row({ row }: { row: AiUsageRow }) {
  const outcome = OUTCOMES[row.outcome] ?? { label: row.outcome, tone: 'neutral' as const }
  return (
    <li role="row" className={ROW}>
      <span role="cell" className={cn('text-[13px] text-text-3 tabular-nums', CELL.time)}>
        {formatDateTime(row.created_at)}
      </span>
      <span role="cell" className={cn('text-sm font-semibold', CELL.person)}>
        {row.user_name ?? 'System'}
      </span>
      <span role="cell" className={cn('min-w-0 break-words', CELL.app)}>
        {row.application_id && row.reference_no ? (
          <Link to={`/admin/applications/${row.application_id}`} className="font-mono text-[13px]">
            {row.reference_no}
          </Link>
        ) : (
          <span className="text-[13px] text-text-3">Deleted draft</span>
        )}
      </span>
      <span role="cell" className={cn('text-sm text-text-2', CELL.doc)}>
        {DOCUMENT_TYPES[row.document_type] ?? row.document_type.replaceAll('_', ' ')}
      </span>
      <span role="cell" className={CELL.out}>
        <StatusBadge label={outcome.label} tone={outcome.tone} />
      </span>
      <Metric label="Tokens">{number.format(row.input_tokens + row.output_tokens)}</Metric>
      <Metric label="Cost">{usd(row.cost_usd)}</Metric>
      <Metric label="Duration">{seconds(row.latency_ms)}</Metric>
    </li>
  )
}

const HEADINGS = ['Time', 'Person', 'Application', 'Document type', 'Outcome', 'Tokens', 'Cost', 'Duration']

function SkeletonRows() {
  return (
    <ul role="status" aria-busy="true" aria-label="Loading checks" className="divide-y divide-line">
      {[0, 1, 2, 3, 4].map((i) => (
        <li key={i} className={cn(ROW, 'items-center')}>
          {[...Array(8).keys()].map((c) => (
            <Pulse key={c} className={cn('h-3.5', c === 4 ? 'h-5.5 w-24' : 'w-3/5', c > 4 && 'w-12 justify-self-end')} />
          ))}
        </li>
      ))}
    </ul>
  )
}

function Label({ htmlFor, children, note }: { htmlFor?: string; children: ReactNode; note?: string }) {
  return (
    <label htmlFor={htmlFor} className="flex items-baseline gap-1.5 text-[13px] font-semibold leading-[18px] text-text">
      {children}
      {note ? <span className="text-xs font-normal text-text-3">{note}</span> : null}
    </label>
  )
}

/** The admin's AI usage page (US-100): today against the daily cap, the filtered totals, and the checks behind them. */
export function AiUsagePage() {
  const [params, setParams] = useSearchParams()
  const ids = { person: useId(), application: useId(), from: useId(), to: useId(), refs: useId() }
  const users = useAdminUsers()

  // The filters live in the URL, so a view can be shared; anything malformed counts as not set.
  const user = params.get('user') ?? ''
  const application = UUID.test(params.get('application') ?? '') ? (params.get('application') ?? '') : ''
  const rawRange = params.get('range')
  const range: Range = rawRange === '7' || rawRange === '30' || rawRange === 'custom' ? rawRange : 'today'
  const day = (key: string): string => (DAY.test(params.get(key) ?? '') ? (params.get(key) ?? '') : '')
  const { from, to } = span(range, day('from'), day('to'))
  const reversed = Boolean(from && to && from > to)
  const query: AiUsageQuery = { user, application, from, to }

  const set = (patch: Record<string, string>) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(patch)) if (v) next.set(k, v)
    else next.delete(k)
    setParams(next, { replace: true })
  }

  // The server filters by application id; the box takes a reference, resolved from the checks seen so far.
  const [known, setKnown] = useState<Record<string, string>>({})
  const [draft, setDraft] = useState<string | null>(null)
  const usage = useInfiniteQuery({
    queryKey: ['admin', 'ai-usage', query],
    queryFn: async ({ pageParam }) => {
      const page = await getAiUsage(query, pageParam)
      const found = page.items.filter((r) => r.reference_no && r.application_id)
      setKnown((prev) => ({ ...prev, ...Object.fromEntries(found.map((r) => [r.reference_no?.toUpperCase(), r.application_id])) }))
      return page
    },
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
    enabled: !reversed,
  })
  const first = usage.data?.pages[0]
  const items = usage.data?.pages.flatMap((p) => p.items) ?? []
  const references = Object.keys(known)
  const shownApplication = draft ?? (application ? (references.find((k) => known[k] === application) ?? application) : '')
  const unresolved = draft !== null && draft.trim() !== '' && !application

  const setApplication = (text: string) => {
    setDraft(text)
    const t = text.trim()
    set({ application: UUID.test(t) ? t.toLowerCase() : (known[t.toUpperCase()] ?? '') })
  }

  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const exportCsv = () => {
    setExporting(true)
    setExportError(null)
    downloadAiUsageCsv(query)
      .catch((e: unknown) => setExportError(e instanceof Error ? e.message : 'Could not export the checks. Try again.'))
      .finally(() => setExporting(false))
  }

  const filtered = Boolean(user || application || range !== 'today')
  const clear = () => {
    setDraft(null)
    setParams({}, { replace: true })
  }
  const person = users.data?.users.find((u) => u.id === user)?.full_name
  const when = range === 'today' ? 'today' : from && to && from === to ? `on ${formatDate(from)}` : `between ${from ? formatDate(from) : 'the start'} and ${to ? formatDate(to) : 'today'}`

  const cap = first?.today.daily_cap ?? 0
  const used = first?.today.runs ?? 0
  const totals = first?.totals
  const checks = (n: number) => `${number.format(n)} ${n === 1 ? 'check' : 'checks'}`

  return (
    <>
      <PageHeader
        eyebrow="Administrator"
        title="AI usage"
        subtitle="What each automatic document check cost, who ran it and how it ended. Checks are advisory: the decision stays with the officer."
        actions={
          <Button variant="secondary" size="sm" className="w-full sm:w-auto" onClick={exportCsv} loading={exporting} disabled={reversed || usage.isPending}>
            Export CSV
          </Button>
        }
      />
      {exportError ? (
        <p role="alert" className="-mt-3 mb-4 text-[13px] font-medium text-error">
          {exportError}
        </p>
      ) : null}

      <div className="flex flex-col gap-5">
        {first ? (
          <section className="pf-surface px-4 py-5 sm:px-7 sm:py-6" aria-label="Today against the daily cap">
            <div className="pf-eyebrow">Today against the daily cap</div>
            <div className="mb-3 mt-2 flex flex-wrap items-baseline gap-x-3">
              <span className={`text-[64px] font-semibold leading-none tracking-[-0.03em] tabular-nums min-[1400px]:text-[84px]`}>{number.format(used)}</span>
              <span className="text-base text-text-2 tabular-nums">of {number.format(cap)} checks</span>
            </div>
            <div
              role="img"
              aria-label={`${number.format(used)} of ${number.format(cap)} checks used today`}
              className="h-1.5 overflow-hidden rounded-[3px] bg-surface-3"
            >
              <div className="h-full rounded-[3px] bg-info" style={{ width: `${cap > 0 ? Math.min(100, (used / cap) * 100) : 0}%` }} />
            </div>
            <p className="mt-2.5 text-[13px] leading-[19px] text-text-2">
              {number.format(Math.max(0, cap - used))} left · resets at midnight, Singapore time · the cap is set in <Link to="/admin/settings">Settings</Link>
            </p>
            {totals ? (
              <p className="mt-4 border-t border-line pt-3.5 text-[15px] leading-[22px] text-text-2" aria-label="Totals for the selected range">
                <b className="font-semibold text-text">{checks(totals.runs)}</b> · {number.format(totals.input_tokens + totals.output_tokens)} tokens (
                {number.format(totals.input_tokens)} in, {number.format(totals.output_tokens)} out) ·{' '}
                <b className="font-semibold text-text">{usd(totals.cost_usd)}</b>
              </p>
            ) : null}
          </section>
        ) : usage.isPending && !reversed ? (
          <section className="pf-surface flex flex-col gap-3 px-4 py-5 sm:px-7 sm:py-6" aria-busy="true" aria-label="Loading totals">
            <div className="pf-eyebrow">Today against the daily cap</div>
            <Pulse className="h-[52px] w-32" />
            <Pulse className="h-1.5 w-full" />
            <Pulse className="h-3 w-3/5" />
            <Pulse className="mt-2 h-3.5 w-4/5" />
          </section>
        ) : null}

        <section className="pf-surface overflow-hidden" aria-label="Checks">
          <div
            role="group"
            aria-label="Filters"
            className={`grid grid-cols-1 gap-x-4 gap-y-3.5 border-b border-line p-4 min-[768px]:grid-cols-2 min-[768px]:px-6 min-[1400px]:grid-cols-[230px_minmax(0,1fr)_auto_150px_150px] min-[1400px]:items-end`}
          >
            <div className="flex flex-col gap-1.5">
              <Label htmlFor={ids.person}>Person</Label>
              <select
                id={ids.person}
                value={user}
                onChange={(e) => set({ user: e.target.value })}
                className={inputClasses()}
              >
                <option value="">All people</option>
                {users.data?.users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor={ids.application}>Application</Label>
              <input
                id={ids.application}
                type="text"
                list={ids.refs}
                value={shownApplication}
                onChange={(e) => setApplication(e.target.value)}
                placeholder="PF-2026-001109"
                autoComplete="off"
                spellCheck={false}
                aria-describedby={unresolved ? `${ids.application}-help` : undefined}
                className={cn(inputClasses(), 'font-mono text-sm')}
              />
              <datalist id={ids.refs}>
                {references.map((r) => (
                  <option key={r} value={r} />
                ))}
              </datalist>
              {unresolved ? (
                <p id={`${ids.application}-help`} className="text-[13px] leading-[18px] text-text-3">
                  No application with this reference among the checks seen so far. Not applied.
                </p>
              ) : null}
            </div>
            <div role="group" aria-labelledby={`${ids.person}-range`} className="flex flex-col gap-1.5 min-[768px]:col-span-2 min-[1400px]:col-span-1">
              <span id={`${ids.person}-range`} className="flex items-baseline gap-1.5 text-[13px] font-semibold leading-[18px] text-text">
                Day range<span className="text-xs font-normal text-text-3">Singapore time</span>
              </span>
              <div className="flex flex-wrap gap-1">
                {RANGES.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    aria-pressed={range === r.value}
                    onClick={() => (r.value === 'custom' ? set({ range: 'custom', from, to }) : set({ range: r.value === 'today' ? '' : r.value, from: '', to: '' }))}
                    className={cn(
                      'min-h-[44px] rounded-md px-3.5 text-[13px] font-medium text-text-2 transition-colors hover:text-text xl:min-h-10',
                      range === r.value && 'bg-surface-3 font-semibold text-text',
                    )}
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor={ids.from}>From</Label>
              <input
                id={ids.from}
                type="date"
                value={from}
                max={to || undefined}
                onChange={(e) => set({ range: 'custom', from: e.target.value, to })}
                className={inputClasses()}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor={ids.to}>To</Label>
              <input
                id={ids.to}
                type="date"
                value={to}
                min={from || undefined}
                aria-invalid={reversed || undefined}
                aria-describedby={reversed ? `${ids.to}-error` : undefined}
                onChange={(e) => set({ range: 'custom', from, to: e.target.value })}
                className={inputClasses(reversed)}
              />
              {reversed ? (
                <p id={`${ids.to}-error`} role="alert" className="text-[13px] font-medium leading-[18px] text-error">
                  The start day is after the end day.
                </p>
              ) : null}
            </div>
          </div>

          {usage.isPending && !reversed ? (
            <SkeletonRows />
          ) : usage.isError ? (
            <div className="p-4">
              <ErrorPanel error={usage.error} onRetry={() => void usage.refetch()} />
            </div>
          ) : items.length === 0 && first ? (
            <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
              <h2 className="text-[17px] font-semibold leading-6">No checks match these filters</h2>
              <p className="mb-2 max-w-[52ch] text-sm text-text-2">
                {`No document checks ${person ? `by ${person} ` : ''}${application ? `on ${shownApplication} ` : ''}${when}. Try a wider day range${filtered ? ', or clear the filters' : ''}.`}
              </p>
              {filtered ? (
                <Button variant="secondary" onClick={clear}>
                  Clear filters
                </Button>
              ) : null}
            </div>
          ) : first ? (
            <>
              <div role="table" aria-label="Checks" className="text-sm">
                <div
                  role="row"
                  className={`hidden border-b border-line bg-surface-2 px-6 py-3 text-xs font-semibold uppercase leading-4 tracking-[0.04em] text-text-3 min-[1400px]:grid ${COLUMNS}`}
                >
                  {HEADINGS.map((h, i) => (
                    <span key={h} role="columnheader" className={i > 4 ? 'text-right' : undefined}>
                      {h}
                    </span>
                  ))}
                </div>
                <ul role="rowgroup" className="divide-y divide-line">
                  {items.map((r) => (
                    <Row key={r.id} row={r} />
                  ))}
                </ul>
              </div>
              <div className="flex items-center justify-between gap-3 border-t border-line bg-surface-2 px-4 py-1.5 min-[768px]:px-6">
                <span className="text-[13px] text-text-3">
                  Showing {number.format(items.length)} of {checks(first.totals.runs)}
                </span>
                {usage.hasNextPage ? (
                  <Button variant="ghost" size="sm" loading={usage.isFetchingNextPage} onClick={() => void usage.fetchNextPage()}>
                    Show older checks
                  </Button>
                ) : null}
              </div>
              {usage.isFetchNextPageError ? (
                <p role="alert" className="px-4 pb-3 text-[13px] font-medium text-error min-[768px]:px-6">
                  Could not load older checks. Try again.
                </p>
              ) : null}
              <p className="border-t border-line px-4 pb-4 pt-3 text-xs leading-[18px] text-text-3 min-[768px]:px-6">
                Export CSV includes all {checks(first.totals.runs)} in this range
                {items.length < first.totals.runs ? `, not only the ${number.format(items.length)} shown` : ''}. A cell that starts with =, +, - or @ is prefixed so a spreadsheet
                never runs it.
              </p>
            </>
          ) : null}
        </section>
      </div>
    </>
  )
}
