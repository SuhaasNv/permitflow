import { Link } from 'react-router-dom'

import type { ApplicationView } from '@/api/applications'
import { cn } from '@/lib/cn'

function Mark({ ok, warn }: { ok: boolean; warn?: boolean }) {
  return (
    <span
      className={cn(
        'flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px]',
        ok ? 'bg-success text-white' : warn ? 'bg-error text-white' : 'border-[1.5px] border-line-strong bg-surface',
      )}
      aria-hidden="true"
    >
      {ok ? '✓' : warn ? '!' : ''}
    </span>
  )
}

/** Server-computed completeness (FR-006): percentage plus a checklist of sections and required documents. */
export function CompletionCard({ view }: { view: ApplicationView }) {
  const c = view.completeness
  const base = `/app/applications/${view.id}`
  return (
    <section className="rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]" aria-labelledby="completion-title">
      <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
        <h2 id="completion-title" className="text-base font-semibold">
          Completion
        </h2>
        <span className={cn('text-sm font-semibold tabular-nums', c.is_complete ? 'text-success' : 'text-text-2')}>{c.percent}%</span>
      </div>
      <div className="px-5 pt-4">
        <div
          className="h-2 overflow-hidden rounded-sm bg-neutral-soft"
          role="progressbar"
          aria-valuenow={c.percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Application completion"
        >
          <div
            className={cn('h-full rounded-sm transition-[width] duration-500', c.is_complete ? 'bg-success' : 'bg-primary')}
            style={{ width: `${c.percent}%` }}
          />
        </div>
        <p className="mt-2 text-xs text-text-3">
          {c.sections_complete} of {c.sections_total} sections complete · {c.documents_present} of {c.documents_total} documents uploaded
        </p>
      </div>
      <ul className="px-5 pb-2 pt-3">
        {view.sections.map((s) => (
          <li key={s.key} className="flex items-center gap-2.5 border-b border-line py-2.5 text-sm">
            <Mark ok={s.complete} warn={s.started && !s.complete} />
            <span>{s.title}</span>
            <span className="ml-auto text-xs text-text-3">{s.complete ? 'Complete' : s.started ? 'Needs attention' : 'Not started'}</span>
            {s.editable && !s.complete ? (
              <Link to={`${base}/form/${s.key}`} className="text-xs font-semibold">
                {s.started ? 'Fix' : 'Start'}
              </Link>
            ) : null}
          </li>
        ))}
        {view.document_slots.map((d) => (
          <li key={d.type} className="flex items-center gap-2.5 border-b border-line py-2.5 text-sm last:border-b-0">
            <Mark ok={d.present} />
            <span>{d.label}</span>
            <span className="ml-auto text-xs text-text-3">{d.present ? 'Uploaded' : 'Missing'}</span>
            {d.editable && !d.present ? (
              <Link to={`${base}/documents`} className="text-xs font-semibold">
                Upload
              </Link>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
