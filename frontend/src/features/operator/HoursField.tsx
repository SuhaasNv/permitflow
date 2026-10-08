import { useId } from 'react'

import { Alert } from '@/features/shared/Alert'
import { selectChevron } from '@/features/shared/Controls'
import { FieldMessage, inputClasses } from '@/features/shared/Field'
import { cn } from '@/lib/cn'
import type { DayKey, HoursValue } from '@/lib/hours'
import { closesAfterMidnight, DAYS, NO_DAYS_MESSAGE, STEP_MINUTES, summariseHours, timeOptions } from '@/lib/hours'

/** The empty picker: nothing chosen yet. */
export const EMPTY_HOURS: HoursValue = { days: [], opens: null, closes: null, open_24h: false }

const WEEKDAYS: DayKey[] = ['mon', 'tue', 'wed', 'thu', 'fri']
const ALL_DAYS: DayKey[] = DAYS.map((d) => d.value)

export interface HoursFieldProps {
  label: string
  help?: string
  required?: boolean
  value: HoursValue | undefined
  onChange: (value: HoursValue) => void
  onBlur?: () => void
  error?: string
  disabled?: boolean
  stepMinutes?: number | null
  /** An older free-text entry that cannot be shown in the picker: named once so the operator can re-pick. */
  legacy?: string
}

function Check({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

const focusRing = 'focus-visible:outline-hidden focus-visible:shadow-[0_0_0_3px_rgba(23,92,211,0.2)]'

/**
 * Operating hours as a picker (S-46, US-108): the days a shop opens as toggles, then one opening and one
 * closing time (30-minute steps) for all of them, or Open 24 hours. A closing time earlier than the opening
 * time means the shop closes after midnight. Built from native controls so keyboards and screen readers work.
 */
export function HoursField({
  label,
  help,
  required = true,
  value,
  onChange,
  onBlur,
  error,
  disabled = false,
  stepMinutes,
  legacy,
}: HoursFieldProps) {
  const id = useId()
  const current = value ?? EMPTY_HOURS
  const times = timeOptions(stepMinutes ?? STEP_MINUTES)
  const daysError = error === NO_DAYS_MESSAGE ? error : undefined
  const timesError = error && !daysError ? error : undefined
  const summary = summariseHours(current)
  const afterMidnight = !current.open_24h && current.opens && current.closes && closesAfterMidnight(current.opens, current.closes)

  const set = (patch: Partial<HoursValue>) => onChange({ ...current, ...patch })
  const toggle = (day: DayKey) =>
    set({ days: ALL_DAYS.filter((d) => (d === day ? !current.days.includes(d) : current.days.includes(d))) })
  const time = (field: 'opens' | 'closes', v: string) => set({ [field]: v === '' ? null : v })

  const quick = (text: string, days: DayKey[]) => (
    <button
      type="button"
      onClick={() => set({ days })}
      disabled={disabled}
      className={cn(
        'rounded-sm py-2 text-[13px] text-text-2 underline underline-offset-[3px] hover:text-text disabled:cursor-not-allowed disabled:no-underline sm:py-0.5',
        focusRing,
      )}
    >
      {text}
    </button>
  )

  return (
    <fieldset
      className="m-0 flex min-w-0 flex-col gap-3.5 border-0 p-0"
      aria-describedby={error ? `${id}-error` : help ? `${id}-help` : undefined}
      onBlur={onBlur}
    >
      <legend className="flex items-baseline gap-1.5 p-0 text-[13px] font-semibold leading-[18px] text-text">
        {label}
        {required ? (
          <span className="text-error" aria-hidden="true">
            *
          </span>
        ) : (
          <span className="text-xs font-normal text-text-3">Optional</span>
        )}
      </legend>
      {help ? (
        <div id={`${id}-help`} className="-mt-1 text-[13px] leading-[18px] text-text-3">
          {help}
        </div>
      ) : null}
      {legacy && disabled ? (
        <div className="text-[13px] leading-[18px] text-text-3">Saved as &ldquo;{legacy}&rdquo;.</div>
      ) : legacy ? (
        <Alert tone="warning">
          <span>
            Your earlier entry was &ldquo;{legacy}&rdquo;. Pick your opening days and hours below; this is a one-time change.
          </span>
        </Alert>
      ) : null}

      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-3">
          <span id={`${id}-days`} className="text-[13px] font-semibold leading-[18px] text-text">
            Open on
          </span>
          <span className="flex gap-4">
            {quick('Every day', ALL_DAYS)}
            {quick('Mon to Fri', WEEKDAYS)}
            {quick('Clear', [])}
          </span>
        </div>
        <div role="group" aria-labelledby={`${id}-days`} className="grid max-w-full grid-cols-7 gap-1 sm:max-w-[520px] sm:gap-1.5">
          {DAYS.map((d) => {
            const on = current.days.includes(d.value)
            return (
              <button
                key={d.value}
                type="button"
                aria-pressed={on}
                disabled={disabled}
                onClick={() => toggle(d.value)}
                className={cn(
                  'inline-flex h-11 min-w-0 items-center justify-center gap-1 rounded-md border px-0 text-sm',
                  'transition-[border-color,background-color] duration-[var(--dur-fast)] ease-[var(--ease-out)]',
                  'disabled:cursor-not-allowed disabled:opacity-60',
                  focusRing,
                  on
                    ? 'border-text bg-surface-3 font-semibold text-text'
                    : daysError
                      ? 'border-error bg-surface font-medium text-text-2'
                      : 'border-line-strong bg-surface font-medium text-text-2 hover:border-text-3',
                )}
              >
                {on ? (
                  <span className="hidden sm:inline-flex">
                    <Check />
                  </span>
                ) : null}
                {d.label}
              </button>
            )
          })}
        </div>
        {daysError ? <FieldMessage id={id} error={daysError} /> : null}
      </div>

      {current.open_24h ? null : (
        <div className="flex items-start gap-3">
          {(['opens', 'closes'] as const).map((field) => {
            const selectId = `${id}-${field}`
            return (
              <div key={field} className="flex min-w-0 flex-1 flex-col gap-1.5 sm:w-[168px] sm:flex-none">
                <label htmlFor={selectId} className="text-[13px] font-semibold leading-[18px] text-text">
                  {field === 'opens' ? 'Opens' : 'Closes'}
                </label>
                <select
                  id={selectId}
                  value={current[field] ?? ''}
                  disabled={disabled}
                  aria-invalid={timesError ? true : undefined}
                  onChange={(e) => time(field, e.target.value)}
                  className={cn(inputClasses(Boolean(timesError)), selectChevron, 'tabular-nums')}
                >
                  <option value="">Choose a time</option>
                  {times.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            )
          })}
        </div>
      )}
      {timesError ? <FieldMessage id={id} error={timesError} /> : null}

      <label className="flex min-h-[44px] cursor-pointer items-center gap-2.5 text-[15px] text-text has-[:disabled]:cursor-not-allowed">
        <input
          type="checkbox"
          checked={current.open_24h}
          disabled={disabled}
          onChange={(e) => set({ open_24h: e.target.checked })}
          className={cn('h-5 w-5 cursor-pointer accent-text', focusRing)}
        />
        Open 24 hours
      </label>

      {afterMidnight ? (
        <Alert tone="info">
          <span>Closes after midnight, at {current.closes} the next day.</span>
        </Alert>
      ) : null}

      {summary ? (
        <div className="flex items-start gap-2 text-[13px] leading-[18px]" aria-live="polite">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" className="mt-0.5 shrink-0 text-text-3">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 2" />
          </svg>
          <span className="flex flex-wrap gap-x-1.5">
            <span className="text-text-3">Shown to the officer as</span>
            <span className="font-semibold text-text">{summary}</span>
          </span>
        </div>
      ) : null}
    </fieldset>
  )
}
