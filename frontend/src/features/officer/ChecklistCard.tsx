import { Link } from 'react-router-dom'

import type { OfficerApplication } from '@/api/officer'
import { buttonClasses } from '@/features/shared/Button'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { formatDateTime } from '@/lib/format'
import { useReadOnly } from './readOnly'

/** S-31 summary: the current visit's checklist on the case rail, or the way to open it once the visit is confirmed. */
export function ChecklistCard({ view }: { view: OfficerApplication }) {
  const readOnly = useReadOnly()
  const c = view.checklist
  const to = readOnly ? `/admin/applications/${view.id}/checklist` : `/officer/applications/${view.id}/checklist`
  return (
    <section className="pf-surface" aria-labelledby="checklist-title">
      <div className="flex items-baseline justify-between gap-3 px-5 pt-5">
        <h2 id="checklist-title" className="text-[17px] font-semibold leading-6">
          Site visit checklist
        </h2>
        {c ? (
          <StatusBadge label={c.status === 'submitted' ? 'Submitted' : 'Draft'} tone={c.status === 'submitted' ? 'success' : 'neutral'} />
        ) : null}
      </div>
      <div className="flex flex-col gap-3 px-5 pb-5 pt-2">
        {c ? (
          <>
            <p className="text-sm leading-5">
              Visit {c.visit_no}: {c.counts.assessed} of {c.counts.total} assessed, {c.counts.flagged} flagged
              {c.counts.missing_comments
                ? `, ${c.counts.missing_comments} ${c.counts.missing_comments === 1 ? 'comment' : 'comments'} missing`
                : ''}
              .
            </p>
            <p className="text-[13px] leading-[19px] text-text-3">
              {c.status === 'submitted' && c.submitted_at
                ? `Submitted ${formatDateTime(c.submitted_at)}. The findings are final.`
                : c.updated_at
                  ? `Draft, last saved ${formatDateTime(c.updated_at)}.`
                  : 'Draft.'}
            </p>
            <Link to={to} className={buttonClasses(c.status === 'submitted' || readOnly ? 'secondary' : 'primary')}>
              {c.status === 'submitted' || readOnly ? 'View checklist' : 'Continue checklist'}
            </Link>
          </>
        ) : (
          <>
            <p className="text-[13px] leading-[19px] text-text-2">
              {readOnly
                ? 'Seventeen items in five sections; the officer fills it on site. Nothing has been recorded yet.'
                : 'Seventeen items in five sections, filled on site. It saves as a draft until you submit it.'}
            </p>
            {!readOnly ? (
              <Link to={to} className={buttonClasses('primary')}>
                Open checklist
              </Link>
            ) : null}
          </>
        )}
      </div>
    </section>
  )
}
