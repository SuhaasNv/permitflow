import { Link, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { Alert } from '@/features/shared/Alert'
import { buttonClasses } from '@/features/shared/Button'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { formatDateTime } from '@/lib/format'
import { ApplicationHeader } from './ApplicationHeader'
import { useApplication, useClarifications } from './queries'

const TONE: Record<string, Tone> = {
  'Waiting for your response': 'warning',
  Sent: 'info',
  Clarified: 'success',
  'No longer needed': 'neutral',
}

/** S-18: only the flagged items, the officer's question first on each. Answering and attachments arrive with US-065. */
export function ClarificationPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  const clar = useClarifications(id)

  if (app.isError && app.data === undefined) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/applications" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  if (clar.isError && clar.data === undefined) return <ErrorPanel error={clar.error} onRetry={() => void clar.refetch()} />
  if (!app.data || !clar.data) {
    return (
      <PageSkeleton label="Loading clarification">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="mt-6 h-64" />
      </PageSkeleton>
    )
  }
  const view = app.data
  const c = clar.data
  const open = c.items.filter((i) => i.status === 'Waiting for your response')
  const base = `/app/applications/${id}`

  return (
    <>
      <ApplicationHeader
        view={view}
        crumb="Clarification"
        actions={
          <Link to={base} className={buttonClasses('secondary', 'sm')}>
            Back to the application
          </Link>
        }
      />
      {c.items.length === 0 ? (
        <section className="pf-surface px-5 py-8 text-center" aria-labelledby="clar-empty">
          <h2 id="clar-empty" className="text-[17px] font-semibold">
            Nothing needs your response yet
          </h2>
          <p className="mx-auto mt-1 max-w-[46ch] text-sm leading-[21px] text-text-2">
            When the licensing officer needs more information after the site visit, the items in question appear here with the officer's
            note on each.
          </p>
        </section>
      ) : (
        <>
          <div className="mb-5">
            <Alert
              tone={open.length > 0 ? 'warning' : 'info'}
              title={
                open.length > 0
                  ? `Round ${c.round}: ${open.length} of ${c.items.length} ${c.items.length === 1 ? 'item needs' : 'items need'} your response`
                  : `Round ${c.round}: every item is answered`
              }
            >
              {open.length > 0
                ? 'Answer each item below. Answering and attaching evidence arrives with the next update; until then the officer can be reached through the licensing office.'
                : 'The officer is reading your answers. You will be told here and by notification if anything else is needed.'}
            </Alert>
          </div>
          <ol className="flex flex-col gap-4">
            {c.items.map((item, n) => (
              <li key={item.item_id} className="pf-surface px-5 py-5" id={`item-${item.key}`}>
                <div className="flex flex-wrap items-start gap-3">
                  <span className="font-mono text-[13px] leading-6 text-text-3">{String(n + 1).padStart(2, '0')}</span>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-base font-semibold leading-6">{item.title}</h2>
                    {item.guidance ? <p className="text-[13px] leading-5 text-text-3">{item.guidance}</p> : null}
                  </div>
                  <StatusBadge label={item.status} tone={TONE[item.status] ?? 'neutral'} />
                </div>
                <div className="mt-4 flex flex-col gap-3 sm:pl-[34px]">
                  {item.requests.map((q) => (
                    <div key={q.id} className="rounded-md border border-line bg-surface-2 px-4 py-3">
                      <div className="text-xs font-semibold uppercase tracking-[0.04em] text-text-3">
                        The officer asked{item.requests.length > 1 ? ` (round ${q.round_no})` : ''}
                      </div>
                      <p className="mt-1 text-sm leading-5 text-text">{q.message}</p>
                      <div className="mt-1 text-xs text-text-3">{formatDateTime(q.released_at)}</div>
                    </div>
                  ))}
                  {item.can_respond ? (
                    <p className="text-[13px] leading-[19px] text-text-3">Answering arrives with the next update.</p>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </>
  )
}
