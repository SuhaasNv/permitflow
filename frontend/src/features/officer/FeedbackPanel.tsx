import { useState } from 'react'

import { AppError } from '@/api/client'
import type { FeedbackItem, FeedbackTemplate, OfficerApplication } from '@/api/officer'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { SelectField, TextAreaField } from '@/features/shared/Controls'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { useToast } from '@/features/shared/Toast'
import { cn } from '@/lib/cn'
import { UNDO_MS } from '@/lib/feedback'
import { formatDateTime } from '@/lib/format'
import {
  useCreateFeedback,
  useFeedbackTemplates,
  useReopenFeedback,
  useResolveFeedback,
  useRestoreFeedback,
  useWithdrawFeedback,
} from './queries'
import { useReadOnly } from './readOnly'
import { useCaseRefusal } from './refusal'

const RESOLUTION: Record<FeedbackItem['resolution'], { label: string; tone: Tone }> = {
  open: { label: 'Open', tone: 'warning' },
  addressed: { label: 'Addressed', tone: 'info' },
  resolved: { label: 'Resolved', tone: 'success' },
  withdrawn: { label: 'Withdrawn', tone: 'neutral' },
}

export interface Target {
  value: string
  label: string
  target_type: 'section' | 'document'
  key: string
}

/** Feedback rail: existing items by round, then the composer (template, target, message). */
export function FeedbackPanel({ view, targets }: { view: OfficerApplication; targets: Target[] }) {
  const readOnly = useReadOnly()
  const templates = useFeedbackTemplates(!readOnly)
  const create = useCreateFeedback(view.id)
  const withdraw = useWithdrawFeedback(view.id)
  const resolve = useResolveFeedback(view.id)
  const restore = useRestoreFeedback(view.id)
  const reopen = useReopenFeedback(view.id)
  // An administrator never edits: the composer and the item controls stay off whatever the status.
  const editable = view.feedback_editable && !readOnly
  const toast = useToast()
  // A 409 (the case moved under us: the operator withdrew, another officer decided): reload, shared sentence.
  const refused = useCaseRefusal(view.id)
  const [composingRequested, setComposing] = useState(false)
  const [target, setTarget] = useState('')
  const [templateKey, setTemplateKey] = useState('')
  const [message, setMessage] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  // The case can stop being editable under the officer (status moved, operator withdrew): the composer is derived closed.
  const composing = composingRequested && editable

  /** Undo for 10 s (the server accepts a little longer). */
  const offerUndo = (title: string, body: string, feedbackId: string) => {
    toast.push({
      title,
      body,
      tone: 'success',
      duration: UNDO_MS,
      action: {
        label: 'Undo',
        onClick: () =>
          restore.mutate(feedbackId, {
            onSuccess: () => toast.push({ title: 'Undone', body: 'The item is back where it was.', tone: 'neutral' }),
            onError: refused('Could not undo'),
          }),
      },
    })
  }

  const pickTemplate = (key: string) => {
    const previous = templates.data?.find((x) => x.key === templateKey)
    setTemplateKey(key)
    const t = templates.data?.find((x) => x.key === key)
    if (!t) {
      // Back to "No template": drop the template's text unless the officer already edited it.
      if (previous && message === previous.message) setMessage('')
      return
    }
    setMessage(t.message)
    const suggested = targets.find((x) => (t.section_key ? x.key === t.section_key : t.document_type ? x.key === t.document_type : false))
    if (suggested) setTarget(suggested.value)
  }

  const submit = () => {
    const chosen = targets.find((x) => x.value === target)
    const next: Record<string, string> = {}
    if (!chosen) next.target = 'Choose the section or document this is about.'
    if (message.trim().length < 3) next.message = 'Write the feedback the operator will read.'
    setErrors(next)
    if (!chosen || Object.keys(next).length) return
    create.mutate(
      {
        target_type: chosen.target_type,
        section_key: chosen.target_type === 'section' ? chosen.key : null,
        document_type: chosen.target_type === 'document' ? chosen.key : null,
        message: message.trim(),
        template_key: templateKey || null,
      },
      {
        onSuccess: () => {
          setComposing(false)
          setTarget('')
          setTemplateKey('')
          setMessage('')
          toast.push({
            title: 'Feedback added',
            body: `Tied to ${chosen.label}. It reaches the operator when you request a resubmission.`,
            tone: 'success',
          })
        },
        onError: (e) => {
          if (e instanceof AppError && e.status === 422 && e.details && typeof e.details.fields === 'object') {
            const fields = e.details.fields as Record<string, string>
            setErrors({ target: fields.section_key ?? fields.document_type ?? fields.target_type ?? '', message: fields.message ?? '' })
          }
        },
      },
    )
  }

  const rounds = new Map<number, FeedbackItem[]>()
  for (const f of view.feedback) rounds.set(f.raised_in_revision, [...(rounds.get(f.raised_in_revision) ?? []), f])
  const createError = create.error instanceof AppError && create.error.status !== 422 ? create.error.message : null

  return (
    <section className="pf-surface" aria-labelledby="fb-title">
      <div className="flex items-baseline justify-between px-5 pt-4">
        <h2 id="fb-title" className="text-[15px] font-semibold">
          Feedback
        </h2>
        <span className="font-mono text-xs text-text-3">
          {view.open_feedback_count} open · {view.feedback.length} total
        </span>
      </div>

      {view.feedback.length === 0 ? (
        <p className="px-5 pb-1 pt-2 text-[13px] leading-[19px] text-text-3">
          No feedback yet. Each item is tied to one section or document, so the operator knows exactly what to change.
        </p>
      ) : (
        <div className="mt-2 divide-y divide-line border-t border-line">
          {[...rounds.entries()]
            .sort((a, b) => b[0] - a[0])
            .map(([round, items]) => (
              <div key={round} className="px-5 py-3">
                <div className="pf-eyebrow mb-2">Raised against Revision {round}</div>
                <ul className="pf-stagger flex flex-col gap-2.5">
                  {items.map((f) => (
                    <li
                      key={f.id}
                      className={cn(
                        'rounded-md border px-3 py-2.5',
                        f.resolution === 'open' ? 'border-warning-line bg-warning-soft/40' : 'border-line bg-surface-2',
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                        <a
                          href={`#target-${f.target_type}-${f.section_key ?? f.document_type}`}
                          className="text-[13px] font-semibold text-text no-underline hover:underline"
                        >
                          {f.target_label}
                        </a>
                        <StatusBadge
                          label={
                            f.resolution === 'addressed' && f.addressed_in_revision
                              ? `Addressed in Revision ${f.addressed_in_revision}`
                              : RESOLUTION[f.resolution].label
                          }
                          tone={RESOLUTION[f.resolution].tone}
                        />
                        {f.released_to_operator_at ? (
                          <span className="text-[11px] text-text-3">Sent to the operator</span>
                        ) : f.resolution === 'open' ? (
                          <span
                            className="text-[11px] text-text-3"
                            title="Reaches the operator when you request a resubmission. Until then you can edit or withdraw it."
                          >
                            Draft, not sent yet
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-1.5 text-[13px] leading-[19px] text-text-2">{f.message}</p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-text-3">
                        <span className="min-w-0 flex-1 basis-full sm:basis-auto">
                          {f.author_name} · {formatDateTime(f.created_at)}
                        </span>
                        {/* Resolve only what the operator has seen; an unsent draft can only be withdrawn (US-039). */}
                        {f.can_resolve && !readOnly ? (
                          <button
                            type="button"
                            className="whitespace-nowrap py-1 font-semibold text-success hover:underline"
                            disabled={resolve.isPending}
                            onClick={() =>
                              resolve.mutate(f.id, {
                                onSuccess: () => offerUndo('Marked resolved', `${f.target_label} is resolved.`, f.id),
                                onError: refused('Could not resolve'),
                              })
                            }
                          >
                            Mark resolved
                          </button>
                        ) : null}
                        {/* Not fixed (US-049): the operator's change did not settle it; reopen for the next round. */}
                        {f.resolution === 'addressed' && editable ? (
                          <button
                            type="button"
                            className="whitespace-nowrap py-1 font-semibold text-warning hover:underline"
                            disabled={reopen.isPending}
                            title="Reopens this item with the same text so you can request another resubmission."
                            onClick={() =>
                              reopen.mutate(f.id, {
                                onSuccess: () => offerUndo('Marked not fixed', `${f.target_label} is open again for the next round.`, f.id),
                                onError: refused('Could not reopen'),
                              })
                            }
                          >
                            Not fixed
                          </button>
                        ) : null}
                        {f.resolution === 'open' && editable ? (
                          <button
                            type="button"
                            className="whitespace-nowrap py-1 font-semibold text-text-2 hover:text-text"
                            disabled={withdraw.isPending}
                            onClick={() =>
                              withdraw.mutate(f.id, {
                                onSuccess: () => offerUndo('Feedback withdrawn', `${f.target_label} item removed.`, f.id),
                                onError: refused('Could not withdraw'),
                              })
                            }
                          >
                            Withdraw
                          </button>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
      )}

      <div className="border-t border-line px-5 py-4">
        {readOnly ? (
          <p className="text-[13px] leading-[19px] text-text-3">Feedback is written by the licensing officer.</p>
        ) : !view.feedback_editable ? (
          <p className="text-[13px] leading-[19px] text-text-3">{view.feedback_locked_reason}</p>
        ) : !composing ? (
          <Button variant="secondary" onClick={() => setComposing(true)} className="w-full">
            Add feedback
          </Button>
        ) : (
          <form
            className="flex flex-col gap-3"
            onSubmit={(e) => {
              e.preventDefault()
              submit()
            }}
            noValidate
          >
            {createError ? (
              <Alert tone="error">
                <span>{createError}</span>
              </Alert>
            ) : null}
            <SelectField
              label="Template"
              placeholder="No template, write your own"
              value={templateKey}
              onChange={(e) => pickTemplate(e.target.value)}
              options={(templates.data ?? []).map((t: FeedbackTemplate) => ({ value: t.key, label: t.title }))}
            />
            <SelectField
              label="About"
              required
              placeholder="Choose a section or document"
              value={target}
              error={errors.target || undefined}
              onChange={(e) => setTarget(e.target.value)}
              options={targets.map((t) => ({ value: t.value, label: t.label }))}
            />
            <TextAreaField
              label="Feedback for the operator"
              required
              value={message}
              error={errors.message || undefined}
              onChange={(e) => setMessage(e.target.value)}
              maxLength={2000}
              help="Plain language: what is wrong and what to provide. Sent when you request a resubmission."
            />
            <div className="flex justify-end gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setComposing(false)
                  setErrors({})
                }}
              >
                Cancel
              </Button>
              <Button type="submit" loading={create.isPending}>
                Add feedback
              </Button>
            </div>
          </form>
        )}
      </div>
    </section>
  )
}
