import { Link } from 'react-router-dom'

import type { ApplicationView, OperatorFeedback } from '@/api/applications'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { cn } from '@/lib/cn'

const RESOLUTION: Record<OperatorFeedback['resolution'], { label: string; tone: Tone; hint: string }> = {
  open: { label: 'Needs your change', tone: 'warning', hint: 'Update this, then resubmit.' },
  addressed: { label: 'Changed, awaiting review', tone: 'info', hint: 'Your change was sent with your latest revision.' },
  resolved: { label: 'Resolved by the officer', tone: 'success', hint: '' },
}

export function targetHref(view: ApplicationView, item: OperatorFeedback): string {
  const base = `/app/applications/${view.id}`
  return item.target_type === 'section' && item.section_key
    ? `${base}/form/${item.section_key}`
    : `${base}/documents#slot-${item.document_type ?? ''}`
}

/** Feedback from the licensing office, on top of the application (S-15). Open items link to their target. */
export function FeedbackNotice({ view, compact = false }: { view: ApplicationView; compact?: boolean }) {
  if (view.feedback.length === 0) return null
  const open = view.feedback.filter((f) => f.resolution === 'open')
  const rest = view.feedback.filter((f) => f.resolution !== 'open')
  return (
    <section className={cn('pf-surface overflow-hidden', open.length > 0 && 'border-warning-line')} aria-labelledby="feedback-notice-title">
      <div
        className={cn(
          'flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-line px-5 py-3.5',
          open.length > 0 && 'bg-warning-soft/50',
        )}
      >
        <h2 id="feedback-notice-title" className="text-[15px] font-semibold">
          {open.length > 0
            ? `The licensing office asked for ${open.length} ${open.length === 1 ? 'change' : 'changes'}`
            : 'Feedback from the licensing office'}
        </h2>
        {open.length > 0 ? (
          <span className="text-[13px] text-text-2">
            Only the flagged parts are open for editing. Everything else is kept as submitted.
          </span>
        ) : null}
      </div>
      <ul className="divide-y divide-line">
        {[...open, ...(compact ? [] : rest)].map((f) => (
          <li key={f.id} className="flex gap-4 px-5 py-4">
            <span
              className={cn(
                'mt-[7px] h-[7px] w-[7px] shrink-0 rounded-full',
                f.resolution === 'open' ? 'bg-warning' : f.resolution === 'addressed' ? 'bg-info' : 'bg-success',
              )}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <span className="text-[15px] font-semibold">{f.target_label}</span>
                <StatusBadge label={RESOLUTION[f.resolution].label} tone={RESOLUTION[f.resolution].tone} />
                <span className="text-xs text-text-3">Round {f.round}</span>
              </div>
              <p className="mt-1 text-sm leading-[21px] text-text-2">{f.message}</p>
            </div>
            {f.resolution === 'open' && view.can_edit ? (
              <Link to={targetHref(view, f)} className="shrink-0 self-center text-[13px] font-semibold">
                {f.target_type === 'section' ? 'Edit section' : 'Replace document'}
              </Link>
            ) : null}
          </li>
        ))}
      </ul>
      {compact && rest.length > 0 ? (
        <p className="border-t border-line px-5 py-2.5 text-xs text-text-3">
          {rest.length} earlier {rest.length === 1 ? 'item' : 'items'} addressed or resolved.
        </p>
      ) : null}
    </section>
  )
}
