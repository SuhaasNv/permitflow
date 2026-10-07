import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import type { ApplicationView } from '@/api/applications'
import { AppError } from '@/api/client'
import type { SiteVisitSlot } from '@/api/siteVisit'
import { Button } from '@/features/shared/Button'
import { TextAreaField } from '@/features/shared/Controls'
import { Dialog } from '@/features/shared/Dialog'
import { Field } from '@/features/shared/Field'
import { SlotControl, VisitRounds, dateBounds, fieldErrorsOf } from '@/features/shared/SiteVisit'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { useToast } from '@/features/shared/Toast'
import { formatDate } from '@/lib/format'
import { applicationKeys, useAcceptSiteVisit, useCounterSiteVisit, useRescheduleSiteVisit } from './queries'

const TONE: Record<string, Tone> = { proposed: 'warning', counter_proposed: 'neutral', confirmed: 'success', done: 'success' }

interface DateFormProps {
  earliest: string
  submitLabel: string
  busy: boolean
  errors: Record<string, string>
  onSubmit: (date: string, slot: SiteVisitSlot, reason: string) => void
  onCancel?: () => void
}

/** Date, slot and a required reason: the counter-proposal and the reschedule request share it. */
function DateForm({ earliest, submitLabel, busy, errors, onSubmit, onCancel }: DateFormProps) {
  const [date, setDate] = useState('')
  const [slot, setSlot] = useState<SiteVisitSlot>('morning')
  const [reason, setReason] = useState('')
  const [local, setLocal] = useState<Record<string, string>>({})
  const bounds = dateBounds(earliest)
  // A key edited since the last submit hides the server message for it until the next submit.
  const show = (key: string) => (local[key] === undefined ? errors[key] : local[key] || undefined)
  return (
    <form
      className="flex flex-col gap-4"
      aria-label={submitLabel}
      // min and max shape the picker; the messages come from this form and the server, not the browser bubble.
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        // Every problem at once, in the server's words (UAT run 5, F5); the server still has the last word.
        const next: Record<string, string> = {}
        const weekday = date ? new Date(`${date}T00:00:00Z`).getUTCDay() : null
        if (!date) next.date = 'Choose a date.'
        else if (weekday === 0 || weekday === 6) next.date = 'Choose a working day, Monday to Friday.'
        else if (date < earliest) next.date = 'Choose a date at least 2 working days ahead.'
        else if (date > bounds.max) next.date = 'Choose a date within the next 60 days.'
        if (reason.trim().length < 3) next.reason = 'Say why, in a sentence the officer will read.'
        setLocal(next)
        if (Object.keys(next).length) return
        onSubmit(date, slot, reason.trim())
      }}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
        <Field
          label="Date"
          type="date"
          required
          min={bounds.min}
          max={bounds.max}
          value={date}
          error={show('date')}
          help={show('date') ? undefined : `Monday to Friday, ${formatDate(earliest)} or later (two working days' notice).`}
          className="sm:w-[200px]"
          onChange={(e) => {
            setDate(e.target.value)
            setLocal((l) => ({ ...l, date: '' }))
          }}
        />
        <SlotControl value={slot} onChange={setSlot} disabled={busy} />
      </div>
      <TextAreaField
        label="Reason"
        required
        value={reason}
        error={show('reason')}
        maxLength={500}
        placeholder="Shared with the licensing officer."
        onChange={(e) => {
          setReason(e.target.value)
          setLocal((l) => ({ ...l, reason: '' }))
        }}
      />
      <div className="flex flex-col gap-2 sm:flex-row">
        <Button type="submit" variant="secondary" loading={busy} className="sm:w-auto">
          {submitLabel}
        </Button>
        {onCancel ? (
          <Button type="button" variant="ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  )
}

/** S-33: the operator's appointment. Accept the officer's date, propose another with a reason, or ask to move a confirmed visit. */
export function SiteVisitCard({ view }: { view: ApplicationView }) {
  const visit = view.site_visit
  const accept = useAcceptSiteVisit(view.id)
  const counter = useCounterSiteVisit(view.id)
  const reschedule = useRescheduleSiteVisit(view.id)
  const toast = useToast()
  const queryClient = useQueryClient()
  const [acceptOpen, setAcceptOpen] = useState(false)
  const [rescheduleOpen, setRescheduleOpen] = useState(false)
  if (!visit) return null
  const busy = accept.isPending || counter.isPending || reschedule.isPending
  const fail = (title: string) => (e: Error) => {
    if (Object.keys(fieldErrorsOf(e)).length) return
    if (e instanceof AppError && e.status === 409) {
      toast.push({ title, body: 'This application changed since you opened it. Showing the latest.', tone: 'error' })
      void queryClient.invalidateQueries({ queryKey: applicationKeys.detail(view.id) })
      return
    }
    toast.push({ title, body: e.message, tone: 'error' })
  }
  const lastMine = [...visit.rounds].reverse().find((r) => r.author_role === 'operator')
  const officerRound = [...visit.rounds].reverse().find((r) => r.author_role === 'officer')

  return (
    <section className="pf-surface" aria-labelledby="visit-title">
      <div className="flex flex-wrap items-baseline justify-between gap-3 px-5 pt-5">
        <h2 id="visit-title" className="text-[17px] font-semibold leading-6">
          Site visit
        </h2>
        <StatusBadge label={visit.status_label} tone={TONE[visit.status] ?? 'neutral'} />
      </div>
      <div className="flex flex-col gap-3.5 px-5 pb-5 pt-3">
        {visit.status === 'counter_proposed' && lastMine ? (
          <>
            <p className="text-base font-semibold leading-6">You proposed {lastMine.when}</p>
            <p className="text-sm leading-5 text-text-2">
              The licensing officer decides between your date and {visit.when}
              {visit.rounds_left > 0 ? ', or proposes a third one' : ''}. You will be told here and by notification.
            </p>
          </>
        ) : (
          <>
            <p className="text-base font-semibold leading-6">{visit.when}</p>
            <p className="text-sm leading-5 text-text-2">
              {visit.status === 'proposed'
                ? `Proposed by the licensing officer${officerRound ? ` on ${formatDate(officerRound.created_at)}` : ''}.`
                : visit.status === 'confirmed'
                  ? 'Confirmed. An officer will visit the premises in this slot.'
                  : 'The visit has taken place.'}
              {visit.status === 'proposed' && officerRound?.reason ? ` Reason: ${officerRound.reason}` : ''}
              {visit.note ? ` Note: ${visit.note}` : ''}
            </p>
          </>
        )}
        {visit.status === 'proposed' && visit.reply_by ? (
          <p className="text-[13px] leading-[18px] text-text-3">
            Reply by {formatDate(visit.reply_by)}. After that the officer can confirm this date without your reply.
          </p>
        ) : null}

        {visit.status === 'proposed' && !visit.can_accept ? (
          <p className="text-[13px] leading-[18px] text-text-2">
            This date has passed and can no longer be accepted; propose another one below.
          </p>
        ) : null}
        {visit.can_accept ? (
          <div className="flex">
            <Button size="lg" className="w-full sm:w-auto" disabled={busy} onClick={() => setAcceptOpen(true)}>
              Accept this date
            </Button>
          </div>
        ) : null}
        {visit.status === 'proposed' ? (
          <div className="flex flex-col gap-3 border-t border-line pt-3.5">
            <h3 className="text-sm font-semibold">Or propose another date</h3>
            {visit.can_counter ? (
              <DateForm
                earliest={visit.earliest_date}
                submitLabel="Propose this date"
                busy={counter.isPending}
                errors={fieldErrorsOf(counter.error)}
                onSubmit={(date, slot, reason) =>
                  counter.mutate(
                    { date, slot, reason },
                    {
                      onSuccess: () =>
                        toast.push({ title: 'Date proposed', body: 'The licensing officer has been asked to decide.', tone: 'success' }),
                      onError: fail('Could not propose the date'),
                    },
                  )
                }
              />
            ) : (
              <p className="text-sm leading-5 text-text-2">{visit.round_limit_reason ?? 'Not available for this visit.'}</p>
            )}
          </div>
        ) : null}
        {visit.status === 'confirmed' ? (
          rescheduleOpen ? (
            <div className="flex flex-col gap-3 border-t border-line pt-3.5">
              <h3 className="text-sm font-semibold">Request a different date</h3>
              <DateForm
                earliest={visit.earliest_date}
                submitLabel="Send the request"
                busy={reschedule.isPending}
                errors={fieldErrorsOf(reschedule.error)}
                onCancel={() => {
                  reschedule.reset()
                  setRescheduleOpen(false)
                }}
                onSubmit={(date, slot, reason) =>
                  reschedule.mutate(
                    { date, slot, reason },
                    {
                      onSuccess: () => {
                        setRescheduleOpen(false)
                        toast.push({ title: 'Request sent', body: 'The licensing officer decides on the new date.', tone: 'success' })
                      },
                      onError: fail('Could not send the request'),
                    },
                  )
                }
              />
            </div>
          ) : (
            <div className="flex flex-col gap-1">
              <div className="flex">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!visit.can_reschedule || busy}
                  title={visit.round_limit_reason ?? undefined}
                  onClick={() => setRescheduleOpen(true)}
                >
                  Request a different date
                </Button>
              </div>
              {!visit.can_reschedule && visit.round_limit_reason ? (
                <p className="text-xs leading-[17px] text-text-3">{visit.round_limit_reason}</p>
              ) : null}
            </div>
          )
        ) : null}

        <div className="border-t border-line pt-3.5">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-text-3">
            Visit history · {visit.rounds.length} {visit.rounds.length === 1 ? 'round' : 'rounds'}
          </h3>
          <VisitRounds rounds={visit.rounds} reader="operator" />
        </div>
      </div>
      <Dialog
        open={acceptOpen}
        title="Accept this visit date?"
        confirmLabel="Accept the date"
        busy={accept.isPending}
        onConfirm={() =>
          accept.mutate(undefined, {
            onSuccess: () => {
              setAcceptOpen(false)
              toast.push({ title: 'Site visit confirmed', body: 'The licensing officer has been told.', tone: 'success' })
            },
            onError: (e) => {
              setAcceptOpen(false)
              fail('Could not accept the date')(e)
            },
          })
        }
        onCancel={() => setAcceptOpen(false)}
      >
        <p>
          <b>{visit.when}</b> becomes the confirmed appointment. Have the premises and the people the officer asked for ready in that slot.
          You can still request a different date before then, with a reason.
        </p>
      </Dialog>
    </section>
  )
}
