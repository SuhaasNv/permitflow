import { Link } from 'react-router-dom'

import type { SectionView } from '@/api/applications'
import type { SectionDef } from '@/api/formSchema'
import { StatusBadge } from '@/features/shared/StatusBadge'

function display(def: SectionDef['fields'][number], value: unknown): string {
  if (value === undefined || value === null || value === '') return 'Not entered'
  if (def.kind === 'checkbox') return value === true ? 'Confirmed' : 'Not confirmed'
  if (def.kind === 'select') return def.options.find((o) => o.value === value)?.label ?? String(value)
  if (def.kind === 'date' && typeof value === 'string') {
    const [y, m, d] = value.split('-')
    return d && m && y
      ? `${Number(d)} ${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][Number(m) - 1]} ${y}`
      : value
  }
  return String(value)
}

/** Read-only key/value rendering of a saved section using the schema labels. */
export function SectionSummary({ def, state, editHref }: { def: SectionDef; state: SectionView; editHref?: string }) {
  return (
    <section className="rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]" aria-labelledby={`summary-${def.key}`}>
      <div className="flex items-center gap-3 border-b border-line px-5 py-3.5">
        <h2 id={`summary-${def.key}`} className="text-base font-semibold">
          {def.title}
        </h2>
        {state.complete ? (
          <StatusBadge label="Complete" tone="success" />
        ) : (
          <StatusBadge label={state.started ? 'Needs attention' : 'Not started'} tone={state.started ? 'error' : 'neutral'} />
        )}
        {editHref ? (
          <Link to={editHref} className="ml-auto text-[13px] font-semibold">
            Edit
          </Link>
        ) : null}
      </div>
      <dl className="grid gap-x-4 gap-y-2 px-5 py-4 text-sm sm:grid-cols-[200px_minmax(0,1fr)]">
        {def.fields.map((f) => (
          <div key={f.key} className="contents">
            <dt className="text-text-3">{f.label}</dt>
            <dd className="font-medium">
              {display(f, state.data[f.key])}
              {state.errors[f.key] ? <span className="ml-2 text-xs font-medium text-error">{state.errors[f.key]}</span> : null}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
