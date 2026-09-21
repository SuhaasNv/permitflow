import { skipToken, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { compareMyRevisions } from '@/api/applications'
import { AppError } from '@/api/client'
import { displayValue } from '@/features/operator/SectionSummary'
import { VisitRounds } from '@/features/shared/SiteVisit'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { formatDateTime } from '@/lib/format'
import { ApplicationHeader } from './ApplicationHeader'
import { FeedbackNotice } from './FeedbackNotice'
import { useApplication, useClarifications, useFormSchema } from './queries'

/** Operator history (S-16, US-019): every revision, every released feedback item by round, and what changed between revisions. */
export function HistoryPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  const schema = useFormSchema()
  const clar = useClarifications(id, app.data?.clarification != null)
  const [pair, setPair] = useState<[number, number] | null>(null)
  const compare = useQuery({
    queryKey: ['my-compare', id, pair],
    // skipToken instead of `enabled` plus a non-null assertion: the query is typed as never running without a pair.
    queryFn: pair ? () => compareMyRevisions(id, pair[0], pair[1]) : skipToken,
    staleTime: Infinity,
  })

  if (app.isPending || schema.isPending) {
    return (
      <PageSkeleton label="Loading history">
        <Skeleton className="h-64" />
      </PageSkeleton>
    )
  }
  // A failed background refetch keeps the cached view (and any unsaved work); only a first load can fail the page.
  if (app.isError && app.data === undefined) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/applications" backLabel="Back to my applications" />
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

          {clar.data && clar.data.items.length > 0 ? (
            <section className="pf-surface overflow-hidden" aria-labelledby="clar-history-title">
              <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-4 sm:px-7">
                <h2 id="clar-history-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
                  Clarification after the site visit
                </h2>
                <span className="text-xs text-text-3">
                  Visit {clar.data.visit_no} · round {clar.data.round} · {clar.data.items.length}{' '}
                  {clar.data.items.length === 1 ? 'item' : 'items'}
                </span>
              </div>
              <ol className="divide-y divide-line">
                {clar.data.items.map((item) => (
                  <li key={item.item_id} className="px-5 py-4 sm:px-7">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-[15px] font-semibold">{item.title}</h3>
                      <StatusBadge
                        label={item.status}
                        tone={
                          item.status === 'Clarified'
                            ? 'success'
                            : item.status === 'Sent'
                              ? 'info'
                              : item.status === 'Waiting for your response'
                                ? 'warning'
                                : 'neutral'
                        }
                      />
                    </div>
                    <ol className="mt-3 flex flex-col gap-2 text-sm">
                      {item.requests.map((q) => {
                        const answer = item.responses.find((r) => r.round_no === q.round_no)
                        return (
                          <li key={q.id} className="flex flex-col gap-1 border-l-2 border-line pl-3">
                            <span>
                              <span className="font-semibold">The officer asked</span> <span className="text-text-2">{q.message}</span>
                            </span>
                            <span className="text-xs text-text-3">
                              Round {q.round_no} · {formatDateTime(q.released_at)}
                            </span>
                            {answer ? (
                              <>
                                <span>
                                  <span className="font-semibold">You answered</span>{' '}
                                  <span className="whitespace-pre-wrap text-text-2">{answer.message}</span>
                                </span>
                                <span className="text-xs text-text-3">
                                  {answer.sent_at ? `Sent ${formatDateTime(answer.sent_at)}` : 'Draft, never sent'}
                                  {answer.attachments.length ? ` · ${answer.attachments.map((a) => a.original_filename).join(', ')}` : ''}
                                </span>
                              </>
                            ) : null}
                          </li>
                        )
                      })}
                    </ol>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          {view.site_visit ? (
            <section className="pf-surface overflow-hidden" aria-labelledby="visit-history-title">
              <div className="flex flex-wrap items-center gap-3 border-b border-line px-5 py-4 sm:px-7">
                <h2 id="visit-history-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
                  Site visit
                </h2>
                <StatusBadge
                  label={view.site_visit.status_label}
                  tone={view.site_visit.status === 'confirmed' || view.site_visit.status === 'done' ? 'success' : 'info'}
                />
                <span className="text-xs text-text-3">
                  Visit {view.site_visit.visit_no} · {view.site_visit.rounds.length}{' '}
                  {view.site_visit.rounds.length === 1 ? 'round' : 'rounds'}
                </span>
              </div>
              <div className="px-5 py-5 sm:px-7">
                <p className="mb-4 text-sm font-semibold">{view.site_visit.when}</p>
                <VisitRounds rounds={view.site_visit.rounds} reader="operator" />
              </div>
            </section>
          ) : null}
        </div>
        <aside className="text-[13px] leading-[19px] text-text-2 lg:pt-1">
          <p>
            Every submission is kept as a numbered revision that never changes. Feedback stays attached to the round it was raised in, with
            its state, so nothing is lost between rounds.
          </p>
          <p className="mt-3">
            <Link to={`/app/applications/${id}`} className="inline-block py-2 font-semibold sm:py-0">
              Back to the application
            </Link>
          </p>
        </aside>
      </div>
    </>
  )
}
