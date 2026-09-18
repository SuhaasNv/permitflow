import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { compareMyRevisions } from '@/api/applications'
import { AppError } from '@/api/client'
import { displayValue } from '@/features/operator/SectionSummary'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { formatDateTime } from '@/lib/format'
import { ApplicationHeader } from './ApplicationHeader'
import { FeedbackNotice } from './FeedbackNotice'
import { useApplication, useFormSchema } from './queries'

/** Operator history (S-16, US-019): every revision, every released feedback item by round, and what changed between revisions. */
export function HistoryPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  const schema = useFormSchema()
  const [pair, setPair] = useState<[number, number] | null>(null)
  const compare = useQuery({
    queryKey: ['my-compare', id, pair],
    queryFn: () => compareMyRevisions(id, pair![0], pair![1]),
    enabled: pair !== null,
    staleTime: Infinity,
  })

  if (app.isPending || schema.isPending) {
    return (
      <PageSkeleton label="Loading history">
        <Skeleton className="h-64" />
      </PageSkeleton>
    )
  }
  if (app.isError) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/dashboard" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  if (schema.isError) return <ErrorPanel error={schema.error} onRetry={() => void schema.refetch()} />
  const view = app.data
  const revisions = [...view.revisions].sort((a, b) => b.number - a.number)
  const fieldDef = (sectionKey: string, key: string) =>
    schema.data.sections.find((s) => s.key === sectionKey)?.fields.find((f) => f.key === key)

  return (
    <>
      <ApplicationHeader view={view} crumb="History" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="flex flex-col gap-6">
          <section className="pf-surface overflow-hidden" aria-labelledby="rev-title">
            <div className="border-b border-line px-5 py-4 sm:px-7">
              <h2 id="rev-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
                Revisions
              </h2>
            </div>
            {revisions.length === 0 ? (
              <p className="px-5 py-6 text-sm text-text-2 sm:px-7">Nothing submitted yet. Your first submission becomes Revision 1.</p>
            ) : (
              <ol className="divide-y divide-line">
                {revisions.map((r) => {
                  const previous = view.revisions.find((x) => x.number === r.number - 1)
                  return (
                    <li key={r.number} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 py-3.5 text-sm sm:px-7">
                      <span className="font-mono text-xs text-text-3">R{r.number}</span>
                      <span className="font-medium">Revision {r.number}</span>
                      <span className="text-text-3">{formatDateTime(r.submitted_at)}</span>
                      {r.number === view.revision_count ? <StatusBadge label="Current" tone="info" /> : null}
                      {previous ? (
                        <button
                          type="button"
                          className="ml-auto text-[13px] font-semibold text-text-2 hover:text-text"
                          onClick={() => setPair([previous.number, r.number])}
                        >
                          What changed from Revision {previous.number}
                        </button>
                      ) : (
                        <span className="ml-auto text-xs text-text-3">First submission</span>
                      )}
                    </li>
                  )
                })}
              </ol>
            )}
          </section>

          {pair ? (
            <section className="pf-surface overflow-hidden" aria-labelledby="chg-title">
              <div className="flex items-center gap-3 border-b border-line px-5 py-4 sm:px-7">
                <h2 id="chg-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
                  Revision {pair[0]} to Revision {pair[1]}
                </h2>
                <button type="button" className="ml-auto text-xs font-semibold text-text-2" onClick={() => setPair(null)}>
                  Close
                </button>
              </div>
              {compare.isPending ? (
                <div className="px-5 py-6 sm:px-7">
                  <Skeleton className="h-16" />
                </div>
              ) : compare.isError ? (
                <p className="px-5 py-6 text-sm text-error sm:px-7">Could not load the comparison.</p>
              ) : (
                <div className="divide-y divide-line">
                  {compare.data.sections
                    .filter((s) => s.changed)
                    .map((s) => (
                      <div key={s.key} className="px-5 py-4 sm:px-7">
                        <h3 className="mb-2 text-[15px] font-semibold">{s.title}</h3>
                        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[200px_minmax(0,1fr)_minmax(0,1fr)]">
                          {s.fields.map((f) => {
                            const def = fieldDef(s.key, f.key)
                            return (
                              <div key={f.key} className="contents">
                                <dt className="text-text-3">{f.label}</dt>
                                <dd className="rounded bg-error-soft/60 px-2 py-1 text-text-2 line-through decoration-error/60">
                                  {def ? displayValue(def, f.old) : String(f.old ?? 'Not entered')}
                                </dd>
                                <dd className="rounded bg-success-soft px-2 py-1 font-medium">
                                  {def ? displayValue(def, f.new) : String(f.new ?? 'Not entered')}
                                </dd>
                              </div>
                            )
                          })}
                        </dl>
                      </div>
                    ))}
                  {compare.data.documents
                    .filter((d) => d.change !== 'unchanged')
                    .map((d) => (
                      <div key={d.type} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm sm:px-7">
                        <span className="font-medium">{d.label}</span>
                        <StatusBadge
                          label={d.change === 'replaced' ? 'Replaced' : d.change === 'added' ? 'Added' : 'Removed'}
                          tone="info"
                        />
                        <span className="text-[13px] text-text-3">
                          {d.old ? <span className="line-through">{d.old.filename}</span> : null}
                          {d.old && d.new ? ' → ' : ''}
                          {d.new?.filename}
                        </span>
                      </div>
                    ))}
                  {compare.data.changed_section_count + compare.data.changed_document_count === 0 ? (
                    <p className="px-5 py-4 text-sm text-text-3 sm:px-7">No differences.</p>
                  ) : null}
                </div>
              )}
            </section>
          ) : null}

          {view.feedback.length > 0 ? (
            <FeedbackNotice view={view} />
          ) : (
            <p className="text-sm text-text-3">No feedback from the licensing office yet.</p>
          )}
        </div>
        <aside className="text-[13px] leading-[19px] text-text-2 lg:pt-1">
          <p>
            Every submission is kept as a numbered revision that never changes. Feedback stays attached to the round it was raised in, with
            its state, so nothing is lost between rounds.
          </p>
          <p className="mt-3">
            <Link to={`/app/applications/${id}`} className="font-semibold">
              Back to the application
            </Link>
          </p>
        </aside>
      </div>
    </>
  )
}
