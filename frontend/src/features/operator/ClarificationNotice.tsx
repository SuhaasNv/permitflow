import { Link } from 'react-router-dom'

import type { ApplicationView } from '@/api/applications'
import { buttonClasses } from '@/features/shared/Button'
import { cn } from '@/lib/cn'

/** After the site visit: what the licensing officer still needs, on top of the application (US-064). */
export function ClarificationNotice({ view }: { view: ApplicationView }) {
  const c = view.clarification
  if (!c) return null
  // Items count as open for the operator only while the office is waiting for them: a case rejected
  // or withdrawn mid-round keeps its questions on record but asks for nothing.
  const open = c.can_respond ? c.open_count : 0
  const title =
    open > 0
      ? `The licensing officer needs more information on ${open} ${open === 1 ? 'item' : 'items'} after the site visit`
      : c.answered_count > 0
        ? 'Your answers were sent to the licensing office'
        : c.open_count > 0
          ? 'Clarification after the site visit was not completed'
          : 'Clarification after the site visit'
  return (
    <section className={cn('pf-surface overflow-hidden', open > 0 && 'border-warning-line')} aria-labelledby="clarification-notice-title">
      <div className={cn('flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-4', open > 0 && 'bg-warning-soft/50')}>
        <div className="min-w-0 flex-1">
          <h2 id="clarification-notice-title" className="text-[15px] font-semibold">
            {title}
          </h2>
          <p className="mt-0.5 text-[13px] leading-[19px] text-text-2">
            {open > 0
              ? `Round ${c.round}. Only the items in question are shown; answer each one, then send. The form and documents stay as submitted.`
              : c.answered_count > 0
                ? `Round ${c.round}. The officer is reading your answers; you will be told if anything else is needed.`
                : c.open_count > 0
                  ? 'The application closed before the questions were answered. They stay on record under History.'
                  : 'Every item is clarified.'}
          </p>
        </div>
        <Link to={`/app/applications/${view.id}/clarification`} className={buttonClasses(open > 0 ? 'primary' : 'secondary')}>
          {open > 0 ? `Respond to clarification (${open} ${open === 1 ? 'item' : 'items'})` : 'View clarification'}
        </Link>
      </div>
    </section>
  )
}
