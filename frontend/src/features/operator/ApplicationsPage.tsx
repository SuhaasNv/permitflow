import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { ApplicationSummary } from '@/api/applications'
import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { PageHeader } from '@/features/shared/PageHeader'
import { SearchBox } from '@/features/shared/SearchBox'
import { EmptyPanel, ErrorPanel, Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { matchesQuery } from '@/lib/search'
import { ApplicationRow, bucketOf } from './ApplicationRow'
import type { Bucket } from './ApplicationRow'
import { useApplications, useCreateApplication } from './queries'

type Filter = 'all' | Bucket

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'waiting', label: 'Needs my response' },
  { key: 'draft', label: 'Drafts' },
  { key: 'office', label: 'With the office' },
  { key: 'decided', label: 'Decided' },
]

/** My applications: the complete list as a table with a client-side status filter and search. Sorted by last update (server order). */
export function ApplicationsPage() {
  const navigate = useNavigate()
  const apps = useApplications()
  const create = useCreateApplication()
  const [filter, setFilter] = useState<Filter>('all')
  const [query, setQuery] = useState('')

  const counts = useMemo(() => {
    const c: Record<Filter, number> = { all: 0, waiting: 0, draft: 0, office: 0, decided: 0 }
    for (const a of apps.data ?? []) {
      c.all += 1
      c[bucketOf(a)] += 1
    }
    return c
  }, [apps.data])

  const shown: ApplicationSummary[] = (apps.data ?? []).filter(
    (a) => (filter === 'all' || bucketOf(a) === filter) && matchesQuery(query, [a.reference_no, a.business_name, a.premises_summary]),
  )

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
      New application
    </Button>
  )

  return (
    <>
      <PageHeader
        eyebrow="Operator"
        title="My applications"
        subtitle="Every application you have started, newest activity first."
        actions={newApplication}
      />
      {create.isError ? (
        <div className="mb-4">
          <Alert
            tone="error"
            title="Could not start a new application"
            action={
              <Button size="sm" variant="secondary" onClick={() => create.reset()}>
                Dismiss
              </Button>
            }
          >
            {create.error.message}
            {create.error instanceof AppError && create.error.details?.code === 'draft_limit' ? '' : ' Press New application to try again.'}
          </Alert>
        </div>
      ) : null}
      {apps.isPending ? (
        <div className="pf-surface overflow-hidden" aria-busy="true" aria-label="Loading applications">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="grid grid-cols-[168px_minmax(0,1fr)_220px_120px] gap-4 border-b border-line px-5 py-5 last:border-b-0">
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
          description="Start a new application to apply for a Food Establishment Licence."
          action={newApplication}
        />
      ) : (
        <section className="pf-surface overflow-hidden" aria-label="Applications">
          <div className="flex flex-wrap items-center gap-2 border-b border-line px-3 py-2.5 sm:px-4">
            <div className="flex flex-wrap items-center gap-1" role="tablist" aria-label="Filter by status">
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  role="tab"
                  aria-selected={filter === f.key}
                  onClick={() => setFilter(f.key)}
                  className={cn(
                    'inline-flex h-10 items-center gap-1.5 rounded-md px-3 text-[13px] font-medium transition-colors duration-[var(--dur-fast)] sm:h-8',
                    filter === f.key ? 'bg-surface-3 text-text' : 'text-text-2 hover:bg-neutral-soft hover:text-text',
                  )}
                >
                  {f.label}
                  <span className="font-mono text-[11px] text-text-3">{counts[f.key]}</span>
                </button>
              ))}
            </div>
            <SearchBox
              value={query}
              onChange={setQuery}
              label="Search reference, business or address"
              placeholder="Search applications"
              className="w-full sm:ml-auto sm:w-72"
            />
          </div>
          <div className="hidden grid-cols-[168px_minmax(0,1fr)_220px_120px_112px] gap-x-4 border-b border-line bg-surface-2 px-5 py-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3 lg:grid">
            <span>Reference</span>
            <span>Business</span>
            <span>Status</span>
            <span>Updated</span>
            <span />
          </div>
          {shown.length === 0 ? (
            <p className="px-5 py-10 text-center text-sm text-text-2">
              {query.trim() ? (
                <>
                  No applications match "{query.trim()}".{' '}
                  <button type="button" className="font-semibold text-text-2 hover:text-text" onClick={() => setQuery('')}>
                    Clear search
                  </button>
                </>
              ) : (
                'No applications match this filter.'
              )}
            </p>
          ) : (
            <ul key={filter} className="pf-stagger divide-y divide-line">
              {shown.map((app) => (
                <ApplicationRow key={app.id} app={app} />
              ))}
            </ul>
          )}
        </section>
      )}
    </>
  )
}
