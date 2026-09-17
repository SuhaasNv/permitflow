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

/** Read-only key/value rendering of a saved section using the schema labels. Sections stack with rules, not nested cards. */
export function SectionSummary({
  def,
  state,
  editHref,
  index,
}: {
  def: SectionDef
  state: SectionView
  editHref?: string
  index?: number
}) {
  return (
    <section className="py-6 first:pt-0" aria-labelledby={`summary-${def.key}`}>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {index !== undefined ? <span className="font-mono text-[13px] text-text-3">0{index + 1}</span> : null}
        <h2 id={`summary-${def.key}`} className="text-[17px] font-semibold leading-6">
          {def.title}
        </h2>
        {state.complete ? (
          <StatusBadge label="Complete" tone="success" />
        ) : (
          <StatusBadge label={state.started ? 'Needs attention' : 'Not started'} tone={state.started ? 'warning' : 'neutral'} />
        )}
        {editHref ? (
          <Link to={editHref} className="ml-auto text-[13px] font-semibold">
            Edit
          </Link>
        ) : null}
      </div>
      <dl className="grid gap-x-6 gap-y-2.5 text-sm sm:grid-cols-[220px_minmax(0,1fr)]">
        {def.fields.map((f) => {
          const empty = state.data[f.key] === undefined || state.data[f.key] === null || state.data[f.key] === ''
          return (
            <div key={f.key} className="contents">
              <dt className="text-text-3 sm:py-0.5">{f.label}</dt>
              <dd className={empty ? 'text-text-3 sm:py-0.5' : 'font-medium sm:py-0.5'}>
                {display(f, state.data[f.key])}
                {state.errors[f.key] ? <span className="ml-2 text-xs font-medium text-error">{state.errors[f.key]}</span> : null}
              </dd>
            </div>
          )
        })}
      </dl>
    </section>
  )
}
