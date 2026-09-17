import { Link } from 'react-router-dom'

import type { ApplicationView } from '@/api/applications'
import { cn } from '@/lib/cn'

function Mark({ ok, warn }: { ok: boolean; warn?: boolean }) {
  return (
    <span
      className={cn(
        'flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full text-[10px] transition-colors duration-[var(--dur-base)]',
        ok ? 'bg-success text-white' : warn ? 'bg-warning text-white' : 'border-[1.5px] border-line-strong bg-surface',
      )}
      aria-hidden="true"
    >
      {ok ? (
        <svg
          width="10"
          height="10"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M20 6 9 17l-5-5" />
        </svg>
      ) : warn ? (
        '!'
      ) : (
        ''
      )}
    </span>
  )
}

/** Server-computed completeness (FR-006): percentage plus a checklist of sections and required documents. */
export function CompletionCard({ view }: { view: ApplicationView }) {
  const c = view.completeness
  const base = `/app/applications/${view.id}`
  return (
    <section className="pf-surface" aria-labelledby="completion-title">
      <div className="px-5 pt-5">
        <div className="flex items-baseline justify-between">
          <h2 id="completion-title" className="text-[15px] font-semibold">
            Completion
          </h2>
          <span className={cn('font-mono text-[22px] font-medium tabular-nums leading-7', c.is_complete ? 'text-success' : 'text-text')}>
            {c.percent}%
          </span>
        </div>
        <div
          className="mt-3 h-1.5 overflow-hidden rounded-full bg-surface-3"
          role="progressbar"
          aria-valuenow={c.percent}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Application completion"
        >
          <div
            className={cn(
              'h-full rounded-full transition-[width] duration-[600ms] ease-[var(--ease-out)]',
              c.is_complete ? 'bg-success' : 'bg-text',
            )}
            style={{ width: `${c.percent}%` }}
          />
        </div>
        <p className="mt-2.5 text-xs leading-[18px] text-text-3">
          {c.sections_complete} of {c.sections_total} sections · {c.documents_present} of {c.documents_total} documents
        </p>
      </div>
      <ul className="mt-4 divide-y divide-line border-t border-line px-5 pb-2">
        {view.sections.map((s) => (
          <li key={s.key} className="flex items-center gap-2.5 py-2.5 text-sm">
            <Mark ok={s.complete} warn={s.started && !s.complete} />
            <span className="min-w-0 flex-1 truncate">{s.title}</span>
            <span className="text-xs text-text-3">{s.complete ? 'Complete' : s.started ? 'Needs attention' : 'Not started'}</span>
            {s.editable && !s.complete ? (
              <Link to={`${base}/form/${s.key}`} className="text-xs font-semibold">
                {s.started ? 'Fix' : 'Start'}
              </Link>
            ) : null}
          </li>
        ))}
        {view.document_slots.map((d) => (
          <li key={d.type} className="flex items-center gap-2.5 py-2.5 text-sm">
            <Mark ok={d.present} />
            <span className="min-w-0 flex-1 truncate">{d.label}</span>
            <span className="text-xs text-text-3">{d.present ? 'Uploaded' : 'Missing'}</span>
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
