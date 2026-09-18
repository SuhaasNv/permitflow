import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import type { ApplicationSummary } from '@/api/applications'
import { useAuth } from '@/features/auth/AuthContext'
import { Button } from '@/features/shared/Button'
import { EmptyPanel, ErrorPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { greeting } from '@/lib/format'
import { ApplicationCard, bucketOf } from './ApplicationRow'
import type { Bucket } from './ApplicationRow'
import { useApplications, useCreateApplication } from './queries'

const NEED: [string, string][] = [
  ['Business profile (ACRA)', 'Issued within the last 6 months'],
  ['Floor plan of the premises', 'Showing the food preparation area'],
  ['Signed tenancy agreement', 'Covering the full licence period'],
  ['Food hygiene certificate', 'For the business or a named food handler'],
]

const GROUPS: { key: Bucket; title: string; hint: string; tone: 'warning' | 'neutral' | 'info' | 'success' }[] = [
  {
    key: 'waiting',
    title: 'Needs your response',
    hint: 'The licensing office is waiting for you. Only the flagged parts reopen.',
    tone: 'warning',
  },
  { key: 'draft', title: 'Drafts to finish', hint: 'Not yet submitted. Pick up where you left off.', tone: 'neutral' },
  { key: 'office', title: 'With the licensing office', hint: 'Nothing is needed from you right now.', tone: 'info' },
  { key: 'decided', title: 'Decided', hint: 'Final outcomes. The full history stays available.', tone: 'success' },
]

const TONE_DOT: Record<string, string> = {
  warning: 'bg-warning',
  neutral: 'bg-line-strong',
  info: 'bg-info',
  success: 'bg-success',
}

function Group({ title, hint, tone, count, children }: { title: string; hint: string; tone: string; count: number; children: ReactNode }) {
  return (
    <section aria-labelledby={`group-${title}`} className="pf-enter">
      <div className="mb-3 flex items-baseline gap-3">
        <span className={cn('h-2 w-2 shrink-0 translate-y-[-1px] rounded-full', TONE_DOT[tone])} aria-hidden="true" />
        <h2 id={`group-${title}`} className="text-[15px] font-semibold">
          {title}
        </h2>
        <span className="font-mono text-xs text-text-3">{count}</span>
        <span className="hidden text-[13px] text-text-3 sm:inline">· {hint}</span>
      </div>
      <ul className="pf-stagger grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">{children}</ul>
    </section>
  )
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true" aria-label="Loading dashboard">
      <div className="flex flex-col gap-3">
        <Skeleton className="h-4 w-40" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <Skeleton className="h-4 w-48" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    </div>
  )
}

function summaryLine(apps: ApplicationSummary[]): ReactNode {
  const counts: Record<Bucket, number> = { waiting: 0, draft: 0, office: 0, decided: 0 }
  for (const a of apps) counts[bucketOf(a)] += 1
  const parts: ReactNode[] = []
  if (counts.waiting) {
    parts.push(
      <span key="w" className="font-semibold text-warning">
        {counts.waiting} {counts.waiting === 1 ? 'needs' : 'need'} your response
      </span>,
    )
  }
  if (counts.draft) parts.push(`${counts.draft} ${counts.draft === 1 ? 'draft' : 'drafts'}`)
  if (counts.office) parts.push(`${counts.office} with the licensing office`)
  if (counts.decided) parts.push(`${counts.decided} decided`)
  return (
    <>
      <span className="font-semibold text-text">
        {apps.length} {apps.length === 1 ? 'application' : 'applications'}
      </span>
      {parts.map((p, i) => (
        <span key={i}>
          {' · '}
          {p}
        </span>
      ))}
    </>
  )
}

/** Dashboard: what needs attention today, grouped by who is waiting on whom. The full list lives on My applications. */
export function OperatorDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const apps = useApplications()
  const create = useCreateApplication()
  const firstName = user?.full_name.split(' ').slice(-2).join(' ') ?? ''

  const newApplication = (
    <Button
      loading={create.isPending}
      onClick={() => {
        if (create.isPending) return
        create.mutate(undefined, {
          onSuccess: (view) => navigate(`/app/applications/${view.id}`),
        })
      }}
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

  const grouped: Record<Bucket, ApplicationSummary[]> = { waiting: [], draft: [], office: [], decided: [] }
  for (const a of apps.data ?? []) grouped[bucketOf(a)].push(a)
  const decidedShown = grouped.decided.slice(0, 3)

  return (
    <>
      <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="font-display text-[36px] leading-[1.05] sm:text-[42px]">
            {greeting()}, {firstName}
          </h1>
          <p className="mt-3 text-[15px] leading-[22px] text-text-2">
            {apps.data && apps.data.length > 0 ? summaryLine(apps.data) : 'Here is what needs your attention today.'}
          </p>
        </div>
        <div className="shrink-0">{newApplication}</div>
      </div>
      {create.isError ? (
        <div className="mb-4">
          <ErrorPanel error={create.error} onRetry={() => create.reset()} />
        </div>
      ) : null}
      {apps.isPending ? (
        <DashboardSkeleton />
      ) : apps.isError ? (
        <ErrorPanel error={apps.error} onRetry={() => void apps.refetch()} />
      ) : apps.data.length === 0 ? (
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
          <EmptyPanel
            title="No applications yet"
            description="Start a new application to apply for a Food Establishment Licence. It takes about 20 minutes and you can save a draft at any point."
            action={newApplication}
          />
          <WhatYouNeed />
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="flex flex-col gap-9">
            {GROUPS.filter((g) => g.key !== 'decided' && grouped[g.key].length > 0).map((g) => (
              <Group key={g.key} title={g.title} hint={g.hint} tone={g.tone} count={grouped[g.key].length}>
                {grouped[g.key].map((app) => (
                  <ApplicationCard key={app.id} app={app} />
                ))}
              </Group>
            ))}
            {grouped.decided.length > 0 ? (
              <Group title="Decided" hint="Final outcomes. The full history stays available." tone="success" count={grouped.decided.length}>
                {decidedShown.map((app) => (
                  <ApplicationCard key={app.id} app={app} />
                ))}
              </Group>
            ) : null}
            {grouped.waiting.length === 0 && grouped.draft.length === 0 ? (
              <p className="text-[15px] text-text-2">
                Nothing needs your attention right now. The licensing office will notify you when something changes.
              </p>
            ) : null}
            <Link to="/app/applications" className="inline-flex items-center gap-1 self-start text-[13px] font-semibold">
              See all applications
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
              >
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
          </div>
          <aside className="flex flex-col gap-6 lg:sticky lg:top-[88px] lg:self-start">
            <WhatYouNeed />
          </aside>
        </div>
      )}
    </>
  )
}

function WhatYouNeed() {
  return (
    <section className="pf-surface" aria-labelledby="need-title">
      <div className="flex items-baseline justify-between px-5 pt-4">
        <h2 id="need-title" className="text-[15px] font-semibold">
          Documents you will need
        </h2>
        <span className="font-mono text-xs text-text-3">4</span>
      </div>
      <ol className="mt-2 divide-y divide-line px-5 pb-2">
        {NEED.map(([title, sub], i) => (
          <li key={title} className="flex items-start gap-3 py-2.5 text-sm">
            <span className="mt-0.5 font-mono text-xs text-text-3">0{i + 1}</span>
            <div className="min-w-0">
              <div className="font-medium">{title}</div>
              <div className="text-[13px] text-text-3">{sub}</div>
            </div>
          </li>
        ))}
      </ol>
      <p className="border-t border-line px-5 py-3 text-xs leading-[18px] text-text-3">
        PDF is recommended: it is the only format the automatic check can read. Up to 10 MB each.
      </p>
    </section>
  )
}
