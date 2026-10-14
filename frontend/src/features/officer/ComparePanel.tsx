import { useState } from 'react'

import type { OfficerApplication } from '@/api/officer'
import { useFormSchema } from '@/features/operator/queries'
import { displayValue } from '@/features/operator/SectionSummary'
import { Button } from '@/features/shared/Button'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { Skeleton } from '@/features/shared/states'
import { cn } from '@/lib/cn'
import { useCompare } from './queries'

const CHANGE_LABEL: Record<string, string> = {
  replaced: 'Replaced',
  added: 'Added',
  removed: 'Removed',
  unchanged: 'Unchanged',
}

const HEADER = 'block text-left align-top text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3'
/** Stacked below sm, where the column headers are hidden: each value says which revision it is from. */
const MOBILE_LABEL = 'mb-0.5 block text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3 sm:hidden'

/** Revision compare (S-23, FR-022): field-level old → new for changed sections, document add/remove/replace.
 *  Defaults to current vs previous; any two revisions can be picked (SCOPE S4). */
export function ComparePanel({ view }: { view: OfficerApplication }) {
  const numbers = view.revisions.map((r) => r.number)
  const [from, setFrom] = useState<number>(view.previous_revision_number ?? numbers[0] ?? 1)
  const [to, setTo] = useState<number>(view.current_revision_number)
  const [showUnchanged, setShowUnchanged] = useState(false)
  const compare = useCompare(view.id, from, to)
  const schema = useFormSchema()

  if (numbers.length < 2) {
    return (
      <section className="pf-surface px-5 py-5 sm:px-7" aria-labelledby="compare-title">
        <h2 id="compare-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
          Compare revisions
        </h2>
        <p className="mt-2 text-sm text-text-2">Only one revision so far. A comparison appears after the first resubmission.</p>
      </section>
    )
  }

  const fieldDef = (sectionKey: string, key: string) =>
    schema.data?.sections.find((s) => s.key === sectionKey)?.fields.find((f) => f.key === key)

  return (
    <section className="pf-surface overflow-hidden" aria-labelledby="compare-title">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line px-5 py-3.5 sm:px-7">
        <h2 id="compare-title" className="text-[13px] font-semibold uppercase tracking-[0.06em] text-text-3">
          Compare revisions
        </h2>
        <div className="flex items-center gap-2 text-[13px]">
          <label className="text-text-3" htmlFor="cmp-from">
            From
          </label>
          <select
            id="cmp-from"
            className="h-8 rounded-md border border-line-strong bg-surface px-2 text-[13px]"
            value={from}
            onChange={(e) => setFrom(Number(e.target.value))}
          >
            {numbers.map((n) => (
              <option key={n} value={n}>
                Revision {n}
              </option>
            ))}
          </select>
          <label className="text-text-3" htmlFor="cmp-to">
            to
          </label>
          <select
            id="cmp-to"
            className="h-8 rounded-md border border-line-strong bg-surface px-2 text-[13px]"
            value={to}
            onChange={(e) => setTo(Number(e.target.value))}
          >
            {numbers.map((n) => (
              <option key={n} value={n}>
                Revision {n}
              </option>
            ))}
          </select>
        </div>
        <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setShowUnchanged((v) => !v)}>
          {showUnchanged ? 'Hide unchanged' : 'Show unchanged'}
        </Button>
      </div>
      {from === to ? (
        <p className="px-5 py-6 text-sm text-text-2 sm:px-7">Pick two different revisions.</p>
      ) : compare.isPending ? (
        <div className="flex flex-col gap-3 px-5 py-6 sm:px-7" role="status" aria-busy="true" aria-label="Loading comparison">
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-24" />
        </div>
      ) : compare.isError ? (
        <p className="px-5 py-6 text-sm text-error sm:px-7">Could not load the comparison. Try again.</p>
      ) : (
        <div className="divide-y divide-line">
          <p className="px-5 py-3 text-[13px] text-text-2 sm:px-7">
            <span className="font-semibold text-text">{compare.data.changed_section_count}</span>{' '}
            {compare.data.changed_section_count === 1 ? 'section' : 'sections'} and{' '}
            <span className="font-semibold text-text">{compare.data.changed_document_count}</span>{' '}
            {compare.data.changed_document_count === 1 ? 'document' : 'documents'} changed between Revision {compare.data.from_revision} and
            Revision {compare.data.to_revision}.
          </p>
          {compare.data.sections
            .filter((s) => s.changed || showUnchanged)
            .map((s) => (
              <div key={s.key} className="px-5 py-4 sm:px-7">
                <div className="mb-2 flex items-center gap-3">
                  <h3 className="text-[15px] font-semibold">{s.title}</h3>
                  {s.changed ? (
                    <StatusBadge label={`${s.fields.length} ${s.fields.length === 1 ? 'field' : 'fields'} changed`} tone="info" />
                  ) : (
                    <span className="text-xs text-text-3">Unchanged</span>
                  )}
                </div>
                {s.fields.length > 0 ? (
                  // A real table: column headers name the two revisions, the field name heads its row. Below sm the
                  // cells stack (display: block), so the roles are restated to keep the table semantics.
                  <table role="table" className="-mb-2 block w-full text-left text-sm sm:table sm:table-fixed">
                    <caption className="sr-only">Fields changed in {s.title}</caption>
                    <colgroup>
                      <col className="sm:w-[200px]" />
                      <col />
                      <col />
                    </colgroup>
                    <thead role="rowgroup" className="sr-only sm:not-sr-only sm:table-header-group">
                      <tr role="row" className="sm:table-row">
                        <th role="columnheader" scope="col" className={cn(HEADER, 'sm:table-cell')}>
                          Field
                        </th>
                        <th role="columnheader" scope="col" className={cn(HEADER, 'sm:table-cell sm:pl-6')}>
                          Revision {compare.data.from_revision}
                        </th>
                        <th role="columnheader" scope="col" className={cn(HEADER, 'sm:table-cell sm:pl-6')}>
                          Revision {compare.data.to_revision}
                        </th>
                      </tr>
                    </thead>
                    <tbody role="rowgroup" className="block sm:table-row-group">
                      {s.fields.map((f) => {
                        const def = fieldDef(s.key, f.key)
                        return (
                          <tr key={f.key} role="row" className="block sm:table-row">
                            <th role="rowheader" scope="row" className="block pb-2 text-left align-top font-normal text-text-3 sm:table-cell">
                              {f.label}
                            </th>
                            <td role="cell" className="block pb-2 align-top sm:table-cell sm:pl-6">
                              <div className="rounded bg-error-soft/60 px-2 py-1 text-text-2">
                                <span className={MOBILE_LABEL}>Revision {compare.data.from_revision}</span>
                                <span className="line-through decoration-error/60">
                                  {def ? displayValue(def, f.old) : String(f.old ?? 'Not entered')}
                                </span>
                              </div>
                            </td>
                            <td role="cell" className="block pb-2 align-top sm:table-cell sm:pl-6">
                              <div className="rounded bg-success-soft px-2 py-1 font-medium">
                                <span className={MOBILE_LABEL}>Revision {compare.data.to_revision}</span>
                                {def ? displayValue(def, f.new) : String(f.new ?? 'Not entered')}
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                ) : null}
              </div>
            ))}
          <div className="px-5 py-4 sm:px-7">
            <h3 className="mb-2 text-[15px] font-semibold">Documents</h3>
            <ul className="divide-y divide-line">
              {compare.data.documents
                .filter((d) => d.change !== 'unchanged' || showUnchanged)
                .map((d) => (
                  <li key={d.type} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2 text-sm">
                    <span className="min-w-[180px] font-medium">{d.label}</span>
                    <StatusBadge label={CHANGE_LABEL[d.change] ?? d.change} tone={d.change === 'unchanged' ? 'neutral' : 'info'} />
                    <span className={cn('text-[13px] text-text-3', d.change === 'unchanged' && 'hidden')}>
                      {d.old ? <span className="line-through">{d.old.filename}</span> : null}
                      {d.old && d.new ? ' → ' : ''}
                      {d.new ? <span className="text-text">{d.new.filename}</span> : null}
                    </span>
                  </li>
                ))}
              {compare.data.changed_document_count === 0 && !showUnchanged ? (
                <li className="py-2 text-sm text-text-3">No document changed.</li>
              ) : null}
            </ul>
          </div>
        </div>
      )}
    </section>
  )
}
