import { useState } from 'react'

import { AppError } from '@/api/client'
import type { OfficerApplication } from '@/api/officer'
import type { SiteVisitSlot } from '@/api/siteVisit'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { TextAreaField } from '@/features/shared/Controls'
import { Dialog } from '@/features/shared/Dialog'
import { Field } from '@/features/shared/Field'
import { SlotControl, VisitRounds, dateBounds, fieldErrorsOf } from '@/features/shared/SiteVisit'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { useToast } from '@/features/shared/Toast'
import { formatDate, formatDateTime } from '@/lib/format'
import { useConfirmSiteVisitWithoutReply, useDecideSiteVisit, useProposeSiteVisit, useRescheduleSiteVisitAsOfficer } from './queries'

const TONE: Record<string, Tone> = { proposed: 'neutral', counter_proposed: 'warning', confirmed: 'success', done: 'success' }

/** Short form of a server `when`: "Tuesday 22 September 2026, morning (09:00 to 12:00)" to "Tue 22 Sep, morning". */
export function shortWhen(when: string): string {
  const m = /^(\w{3})\w*\s+(\d+)\s+(\w{3})\w*\s+\d{4},\s+(\w+)/.exec(when)
  return m ? `${m[1]} ${m[2]} ${m[3]}, ${m[4]}` : when
}

interface DateFormProps {
  title: string
  submitLabel: string
  reasonLabel: string
  reasonRequired: boolean
  busy: boolean
  errors: Record<string, string>
  onSubmit: (date: string, slot: SiteVisitSlot, text: string) => void
  onCancel: () => void
}

/** Date, slot and a note or reason: the same form for a third date and for a reschedule. */
function DateForm({ title, submitLabel, reasonLabel, reasonRequired, busy, errors, onSubmit, onCancel }: DateFormProps) {
  const [date, setDate] = useState('')
  const [slot, setSlot] = useState<SiteVisitSlot>('morning')
  const [text, setText] = useState('')
  const [local, setLocal] = useState<Record<string, string>>({})
  const bounds = dateBounds()
  const submit = () => {
    const next: Record<string, string> = {}
    if (!date) next.date = 'Choose a date.'
    if (reasonRequired && text.trim().length < 3) next.reason = 'Say why, in a sentence the operator will read.'
    setLocal(next)
    if (Object.keys(next).length) return
    onSubmit(date, slot, text.trim())
  }
  // A key edited since the last submit hides the server message for it until the next submit.
  const show = (key: string) => (local[key] === undefined ? errors[key] : local[key] || undefined)
  return (
    <form
      className="flex flex-col gap-4 border-t border-line pt-4"
      // min and max shape the picker; the messages come from this form and the server, not the browser bubble.
      noValidate
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
      aria-label={title}
    >
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="flex flex-wrap gap-4">
        <Field
          label="Date"
          type="date"
          required
          min={bounds.min}
          max={bounds.max}
          value={date}
          error={show('date')}
          help={show('date') ? undefined : 'A working day, from tomorrow.'}
          className="w-[200px]"
          onChange={(e) => {
            setDate(e.target.value)
            setLocal((l) => ({ ...l, date: '' }))
          }}
        />
        <SlotControl value={slot} onChange={setSlot} disabled={busy} />
      </div>
      <TextAreaField
        label={reasonLabel}
        required={reasonRequired}
        value={text}
        error={show('reason') ?? show('note')}
        maxLength={500}
        onChange={(e) => {
          setText(e.target.value)
          setLocal((l) => ({ ...l, reason: '' }))
        }}
        placeholder="Shown to the operator."
      />
      <div className="flex gap-2">
        <Button type="submit" loading={busy}>
          {submitLabel}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
      </div>
    </form>
  )
}

export interface ProposeVisitDialogProps {
  open: boolean
  view: OfficerApplication
  onClose: () => void
}

/** S-32: the officer's first proposal. From Under Review the case moves to Site Visit Scheduled in the same call. */
export function ProposeVisitDialog({ open, view, onClose }: ProposeVisitDialogProps) {
  const propose = useProposeSiteVisit(view.id)
  const toast = useToast()
  const [date, setDate] = useState('')
  const [slot, setSlot] = useState<SiteVisitSlot>('morning')
  const [note, setNote] = useState('')
  const [dateError, setDateError] = useState<string | null>(null)
  const bounds = dateBounds()
  const serverErrors = fieldErrorsOf(propose.error)
  const conflict = propose.error instanceof AppError && propose.error.status === 409 ? propose.error.message : null
  const reset = () => {
    setDate('')
    setSlot('morning')
    setNote('')
    setDateError(null)
    propose.reset()
  }
  const confirm = () => {
    if (!date) {
      setDateError('Choose a date.')
      return
    }
    propose.mutate(
      { date, slot, note: note.trim() || null, expected_version: view.version },
      {
        onSuccess: () => {
          reset()
          onClose()
          toast.push({ title: 'Site visit proposed', body: 'The operator has been asked to accept the date.', tone: 'success' })
        },
      },
    )
  }
  return (
    <Dialog
      open={open}
      title="Propose a site visit?"
      confirmLabel="Propose visit"
      busy={propose.isPending}
      onConfirm={confirm}
      onCancel={() => {
        reset()
        onClose()
      }}
    >
      <p>
        The operator is told the date and slot and can accept or propose another date. If they do not reply within three working days you
        can confirm the visit yourself.
        {view.status === 'under_review' ? ' The case moves to Site Visit Scheduled now.' : ''}
      </p>
      {conflict ? (
        <Alert tone="warning" title="Could not propose the visit">
          {conflict}
        </Alert>
      ) : propose.error && !serverErrors.date && !serverErrors.note ? (
        <Alert tone="error" title="Could not propose the visit">
          {propose.error.message}
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-4">
        <Field
          label="Date"
          type="date"
          required
          min={bounds.min}
          max={bounds.max}
          value={date}
          error={dateError ?? serverErrors.date}
          help={dateError || serverErrors.date ? undefined : 'A working day, from tomorrow.'}
          className="w-[200px]"
          onChange={(e) => {
            setDate(e.target.value)
            setDateError(null)
          }}
        />
        <SlotControl value={slot} onChange={setSlot} disabled={propose.isPending} />
      </div>
      <TextAreaField
        label="Note for the operator"
        value={note}
        error={serverErrors.note}
        maxLength={500}
        onChange={(e) => setNote(e.target.value)}
        placeholder="What to have ready on the premises, who should be there."
      />
    </Dialog>
  )
}

export interface SiteVisitPanelProps {
  view: OfficerApplication
  onPropose: () => void
}

/** S-34: the appointment in the review rail. Decide a counter-proposal, confirm after silence, reschedule, see every round. */
export function SiteVisitPanel({ view, onPropose }: SiteVisitPanelProps) {
  const visit = view.site_visit
  const decide = useDecideSiteVisit(view.id)
  const confirm = useConfirmSiteVisitWithoutReply(view.id)
  const reschedule = useRescheduleSiteVisitAsOfficer(view.id)
  const toast = useToast()
  const [form, setForm] = useState<'propose' | 'reschedule' | null>(null)
  const busy = decide.isPending || confirm.isPending || reschedule.isPending
  const fail = (title: string) => (e: Error) => {
    if (Object.keys(fieldErrorsOf(e)).length) return
    toast.push({ title, body: e.message, tone: 'error' })
  }
  const settle = (action: 'accept_operator' | 'keep_original') =>
    decide.mutate(
      { action },
      {
        onSuccess: () => toast.push({ title: 'Site visit confirmed', body: 'The operator has been told the date.', tone: 'success' }),
        onError: fail('Could not confirm the visit'),
      },
    )

  return (
    <section className="pf-surface" aria-labelledby="visit-title">
      <div className="flex items-baseline justify-between gap-3 px-5 pt-5">
        <h2 id="visit-title" className="text-[17px] font-semibold leading-6">
          Site visit
        </h2>
        {visit ? <StatusBadge label={visit.status_label} tone={TONE[visit.status] ?? 'neutral'} /> : null}
      </div>
      <div className="flex flex-col gap-3 px-5 pb-5 pt-3">
        {!visit ? (
          <>
            <p className="text-[13px] leading-[19px] text-text-2">
              No date has been proposed yet. The operator is waiting to hear from you.
            </p>
            <Button onClick={onPropose}>Propose a visit date</Button>
          </>
        ) : (
          <>
            {visit.status === 'counter_proposed' && visit.counter ? (
              <div className="flex flex-col gap-1 rounded-md border border-warning-line bg-warning-soft px-3.5 py-3">
                <span className="text-sm font-semibold leading-5">Operator proposes {visit.counter.when}</span>
                {visit.counter.reason ? <span className="text-sm leading-5 text-text-2">"{visit.counter.reason}"</span> : null}
                <span className="text-xs leading-4 text-text-3">
                  {visit.counter.author_name} · {formatDateTime(visit.counter.created_at)}
                </span>
              </div>
            ) : null}
            <p className="text-[15px] font-semibold leading-6">
              {visit.status === 'counter_proposed' ? 'Your proposal: ' : ''}
              {visit.when}
            </p>
            {visit.note ? <p className="text-[13px] leading-[19px] text-text-2">Note to the operator: {visit.note}</p> : null}
            {visit.status === 'proposed' && visit.reply_deadline ? (
              <p className="text-[13px] leading-[19px] text-text-3">
                The operator has until {formatDate(visit.reply_deadline)} to reply. Visit {visit.visit_no}.
              </p>
            ) : (
              <p className="text-[13px] leading-[19px] text-text-3">Visit {visit.visit_no}.</p>
            )}

            {visit.status === 'counter_proposed' && visit.counter && form === null ? (
              <div className="flex flex-col gap-2">
                <Button loading={decide.isPending} disabled={busy} onClick={() => settle('accept_operator')}>
                  Accept {shortWhen(visit.counter.when)}
                </Button>
                <Button variant="secondary" disabled={busy} onClick={() => settle('keep_original')}>
                  Keep {shortWhen(visit.when)}
                </Button>
                <Button
                  variant="secondary"
                  disabled={busy || visit.rounds_left === 0}
                  title={visit.round_limit_reason ?? undefined}
                  onClick={() => setForm('propose')}
                >
                  Propose another date
                </Button>
                {visit.rounds_left === 0 && visit.round_limit_reason ? (
                  <p className="text-xs leading-[17px] text-text-3">{visit.round_limit_reason}</p>
                ) : null}
              </div>
            ) : null}
            {visit.status === 'proposed' ? (
              <div className="flex flex-col gap-1">
                <Button
                  variant={visit.can_confirm_without_reply ? 'primary' : 'ghost'}
                  disabled={!visit.can_confirm_without_reply || busy}
                  loading={confirm.isPending}
                  title={visit.confirm_without_reply_reason ?? undefined}
                  onClick={() =>
                    confirm.mutate(undefined, {
                      onSuccess: () =>
                        toast.push({
                          title: 'Site visit confirmed',
                          body: 'No reply was received; the operator is told.',
                          tone: 'success',
                        }),
                      onError: fail('Could not confirm the visit'),
                    })
                  }
                >
                  Confirm without a reply
                </Button>
                {visit.confirm_without_reply_reason ? (
                  <p className="text-xs leading-[17px] text-text-3">{visit.confirm_without_reply_reason}</p>
                ) : null}
              </div>
            ) : null}
            {visit.status === 'confirmed' && form === null ? (
              <div className="flex flex-col gap-1">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!visit.can_reschedule || busy}
                  title={visit.round_limit_reason ?? undefined}
                  onClick={() => setForm('reschedule')}
                >
                  Request a different date
                </Button>
                {!visit.can_reschedule && visit.round_limit_reason ? (
                  <p className="text-xs leading-[17px] text-text-3">{visit.round_limit_reason}</p>
                ) : null}
              </div>
            ) : null}
            {form === 'propose' ? (
              <DateForm
                title="Propose another date"
                submitLabel="Propose this date"
                reasonLabel="Note for the operator"
                reasonRequired={false}
                busy={decide.isPending}
                errors={fieldErrorsOf(decide.error)}
                onCancel={() => {
                  decide.reset()
                  setForm(null)
                }}
                onSubmit={(date, slot, note) =>
                  decide.mutate(
                    { action: 'propose', date, slot, note: note || null },
                    {
                      onSuccess: () => {
                        setForm(null)
                        toast.push({ title: 'Another date proposed', body: 'The operator has been asked again.', tone: 'success' })
                      },
                      onError: fail('Could not propose the date'),
                    },
                  )
                }
              />
            ) : null}
            {form === 'reschedule' ? (
              <DateForm
                title="Request a different date"
                submitLabel="Send the new date"
                reasonLabel="Reason"
                reasonRequired
                busy={reschedule.isPending}
                errors={fieldErrorsOf(reschedule.error)}
                onCancel={() => {
                  reschedule.reset()
                  setForm(null)
                }}
                onSubmit={(date, slot, reason) =>
                  reschedule.mutate(
                    { date, slot, reason },
                    {
                      onSuccess: () => {
                        setForm(null)
                        toast.push({ title: 'New date proposed', body: 'The operator has been asked to accept it.', tone: 'success' })
                      },
                      onError: fail('Could not reschedule'),
                    },
                  )
                }
              />
            ) : null}
            <div className="border-t border-line pt-3">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.08em] text-text-3">Rounds</h3>
              <VisitRounds rounds={visit.rounds} reader="officer" />
            </div>
          </>
        )}
      </div>
    </section>
  )
}
