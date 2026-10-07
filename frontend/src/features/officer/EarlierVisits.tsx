import { Link } from 'react-router-dom'

import type { OfficerApplication } from '@/api/officer'
import { buttonClasses } from '@/features/shared/Button'
import { VisitRounds } from '@/features/shared/SiteVisit'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { formatDateTime } from '@/lib/format'
import { ClarificationRail } from './ClarificationRail'
import { useReadOnly } from './readOnly'

/** Visits before the active one (a second visit after Return to review): the appointment rounds, the checklist and
 * the clarification threads of each, read-only and folded, so nothing of the first visit is lost (UAT run 5, F17, F18). */
export function EarlierVisits({ view }: { view: OfficerApplication }) {
  const readOnly = useReadOnly()
  if (view.earlier_visits.length === 0) return null
  const base = readOnly ? `/admin/applications/${view.id}` : `/officer/applications/${view.id}`
  return (
    <section className="pf-surface overflow-hidden" aria-labelledby="earlier-visits-title">
      <div className="border-b border-line px-5 py-4 sm:px-7">
        <h2 id="earlier-visits-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
          Earlier visits
        </h2>
      </div>
      <div className="divide-y divide-line">
        {view.earlier_visits.map((v) => (
          <details key={v.visit_no} className="group">
            <summary className="flex cursor-pointer list-none flex-wrap items-center gap-x-3 gap-y-1 px-5 py-3.5 text-sm sm:px-7">
              <span className="font-semibold">Visit {v.visit_no}</span>
              {v.site_visit ? <span className="text-text-2">{v.site_visit.when}</span> : null}
              {v.checklist ? (
                <span className="text-text-3">
                  {v.checklist.counts.assessed} of {v.checklist.counts.total} assessed, {v.checklist.counts.flagged} flagged
                </span>
              ) : null}
              <span className="ml-auto text-[13px] font-semibold text-text-2 group-open:hidden">Show</span>
              <span className="ml-auto hidden text-[13px] font-semibold text-text-2 group-open:inline">Hide</span>
            </summary>
            <div className="flex flex-col gap-5 px-5 pb-5 sm:px-7">
              {v.site_visit ? (
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-[15px] font-semibold">Appointment</h3>
                    <StatusBadge label={v.site_visit.status_label} tone={v.site_visit.status === 'done' ? 'success' : 'neutral'} />
                  </div>
                  <VisitRounds rounds={v.site_visit.rounds} reader="officer" />
                </div>
              ) : null}
              {v.checklist ? (
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-[15px] font-semibold">Checklist</h3>
                  <span className="text-[13px] text-text-3">
                    {v.checklist.status === 'submitted' && v.checklist.submitted_at
                      ? `Submitted ${formatDateTime(v.checklist.submitted_at)}`
                      : 'Draft, never submitted'}
                  </span>
                  <Link to={`${base}/checklist?visit=${v.visit_no}`} className={buttonClasses('secondary', 'sm')}>
                    View visit {v.visit_no} checklist
                  </Link>
                </div>
              ) : null}
              {v.clarification ? (
                <div className="rounded-md border border-line">
                  <ClarificationRail view={view} clarification={v.clarification} embedded />
                </div>
              ) : null}
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}
