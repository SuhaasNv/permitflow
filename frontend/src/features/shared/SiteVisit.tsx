import { AppError } from '@/api/client'
import type { SiteVisitProposal, SiteVisitSlot } from '@/api/siteVisit'
import { SLOT_OPTIONS } from '@/api/siteVisit'
import { cn } from '@/lib/cn'
import { formatDateTime } from '@/lib/format'

/** The per-field messages of a 422 (`details.fields`), empty for any other error. */
export function fieldErrorsOf(error: unknown): Record<string, string> {
  if (!(error instanceof AppError) || error.status !== 422) return {}
  const fields = error.details?.fields
  if (typeof fields !== 'object' || fields === null) return {}
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(fields)) if (typeof value === 'string') out[key] = value
  return out
}

/** "2026-09-22" for a local calendar date. */
export function isoDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Bounds for the native date input: from `earliest` (or tomorrow) to 60 days out. The server has the last word. */
export function dateBounds(earliest?: string | null, now: Date = new Date()): { min: string; max: string } {
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1)
  const max = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 60)
  return { min: earliest ?? isoDate(tomorrow), max: isoDate(max) }
}

export interface SlotControlProps {
  value: SiteVisitSlot
  onChange: (slot: SiteVisitSlot) => void
  disabled?: boolean
}

/** Two pressable cards, morning and afternoon, with the hours under each. */
export function SlotControl({ value, onChange, disabled }: SlotControlProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[13px] font-semibold leading-[18px]">Slot</span>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Slot">
        {SLOT_OPTIONS.map((o) => {
          const on = o.value === value
          return (
            <button
              key={o.value}
              type="button"
              aria-pressed={on}
              disabled={disabled}
              onClick={() => onChange(o.value)}
              className={cn(
                'flex min-w-[150px] flex-col items-start gap-0.5 rounded-md border px-3.5 py-2.5 text-left',
                'transition-[border-color,background-color] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
                'focus-visible:outline-none focus-visible:shadow-[0_0_0_3px_rgba(23,92,211,0.2)] disabled:cursor-not-allowed',
                on ? 'border-text bg-surface-3 text-text' : 'border-line-strong bg-surface text-text-2 hover:border-text-3',
              )}
            >
              <span className={cn('text-sm leading-5', on ? 'font-semibold' : 'font-medium')}>{o.label}</span>
              <span className="text-xs leading-4 text-text-3">{o.times}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

const OUTCOME_LABEL: Record<SiteVisitProposal['outcome'], string> = {
  pending: 'Waiting',
  accepted: 'Accepted',
  kept: 'Kept',
  declined: 'Declined',
  superseded: 'Replaced',
}

const OUTCOME_TONE: Record<SiteVisitProposal['outcome'], string> = {
  pending: 'bg-warning',
  accepted: 'bg-success',
  kept: 'bg-success',
  declined: 'bg-line-strong',
  superseded: 'bg-line-strong',
}

/** "You proposed ..." from the reader's side; the other side by role or name. */
export function roundTitle(p: SiteVisitProposal, reader: 'officer' | 'operator'): string {
  const who = p.author_role === reader ? 'You' : reader === 'operator' ? 'The officer' : p.author_name
  const verb = p.round === 1 ? 'proposed' : 'proposed instead'
  return `${who} ${verb} ${p.when}`
}

export interface VisitRoundsProps {
  rounds: SiteVisitProposal[]
  reader: 'officer' | 'operator'
  className?: string
}

/** Every proposal in order, with its reason and what became of it. The list never changes once written. */
export function VisitRounds({ rounds, reader, className }: VisitRoundsProps) {
  if (rounds.length === 0) return null
  return (
    <ol className={cn('flex flex-col', className)} aria-label="Site visit rounds">
      {rounds.map((p, i) => {
        const last = i === rounds.length - 1
        return (
          <li key={p.round} className="flex gap-3">
            <span className="flex w-4 shrink-0 flex-col items-center" aria-hidden="true">
              <span className={cn('mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full', OUTCOME_TONE[p.outcome])} />
              {last ? null : <span className="mt-1 w-0.5 flex-1 bg-line" />}
            </span>
            <div className={cn('flex min-w-0 flex-1 flex-col gap-1', last ? 'pb-0' : 'pb-4')}>
              <span className="text-sm font-semibold leading-5">{roundTitle(p, reader)}</span>
              {p.reason ? <span className="text-sm leading-5 text-text-2">{p.reason}</span> : null}
              <span className="text-xs leading-4 text-text-3">
                Round {p.round} · {formatDateTime(p.created_at)} · {OUTCOME_LABEL[p.outcome]}
              </span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
