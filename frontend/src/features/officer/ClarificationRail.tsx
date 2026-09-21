import { useState } from 'react'

import type { ClarificationThread } from '@/api/clarification'
import { downloadAttachment } from '@/api/clarification'
import type { OfficerApplication } from '@/api/officer'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { TextAreaField } from '@/features/shared/Controls'
import { StatusBadge } from '@/features/shared/StatusBadge'
import type { Tone } from '@/features/shared/StatusBadge'
import { useToast } from '@/features/shared/Toast'
import { cn } from '@/lib/cn'
import { formatBytes, formatDateTime } from '@/lib/format'
import { useReopenClarification, useResolveClarification, useWithdrawClarification } from './queries'
import { useReadOnly } from './readOnly'
import { useCaseRefusal } from './refusal'

const STATUS: Record<string, { label: string; tone: Tone }> = {
  open: { label: 'Open', tone: 'warning' },
  answered: { label: 'Answered', tone: 'info' },
  resolved: { label: 'Clarified', tone: 'success' },
  withdrawn: { label: 'Withdrawn', tone: 'neutral' },
}

const RESULT: Record<string, string> = {
  satisfactory: 'Satisfactory',
  unsatisfactory: 'Unsatisfactory',
  not_applicable: 'Not applicable',
  not_assessed: 'Not assessed',
}

function Thread({ view, thread, n }: { view: OfficerApplication; thread: ClarificationThread; n: number }) {
  const readOnly = useReadOnly()
  const resolve = useResolveClarification(view.id)
  const reopen = useReopenClarification(view.id)
  const withdraw = useWithdrawClarification(view.id)
  const toast = useToast()
  const [asking, setAsking] = useState(false)
  const [question, setQuestion] = useState('')
  const [questionError, setQuestionError] = useState<string | null>(null)
  const [showEarlier, setShowEarlier] = useState(false)
  const busy = resolve.isPending || reopen.isPending || withdraw.isPending
  const status = STATUS[thread.status] ?? { label: thread.status, tone: 'neutral' as Tone }
  const current = thread.requests.at(-1)
  const earlier = thread.requests.slice(0, -1)
  // A 409 (the item moved under us: another officer decided it, the operator answered): reload, shared sentence.
  const fail = useCaseRefusal(view.id)

  const renderRound = (q: ClarificationThread['requests'][number]) => (
    <li key={q.id} className="flex gap-3">
      <span className="flex w-4 shrink-0 flex-col items-center" aria-hidden="true">
        <span
          className={cn(
            'mt-1.5 h-2.5 w-2.5 rounded-full',
            q.withdrawn_at ? 'bg-line-strong' : q.released_at ? 'bg-warning' : 'bg-line-strong',
          )}
        />
        <span className="mt-1 w-0.5 flex-1 bg-line" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2 pb-4">
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-semibold leading-5">{q.round_no === 1 ? 'You asked' : 'You asked again'}</span>
          <span className="text-sm leading-5 text-text-2">{q.message}</span>
          <span className="text-xs leading-4 text-text-3">
            Round {q.round_no} · {q.released_at ? formatDateTime(q.released_at) : q.withdrawn_at ? 'withdrawn' : 'not sent yet'}
            {q.withdrawn_at ? ` · withdrawn ${formatDateTime(q.withdrawn_at)}` : ''}
          </span>
        </div>
        {q.response ? (
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-semibold leading-5">{view.applicant.full_name} answered</span>
            <span className="whitespace-pre-wrap text-sm leading-5 text-text-2">{q.response.message}</span>
            <span className="text-xs leading-4 text-text-3">
              Round {q.round_no} · {q.response.sent_at ? formatDateTime(q.response.sent_at) : ''}
            </span>
            {q.response.attachments.length > 0 ? (
              <ul className="mt-1 flex flex-col gap-1">
                {q.response.attachments.map((a) => (
                  <li key={a.id}>
                    <button
                      type="button"
                      className="inline-flex max-w-full items-center gap-2 rounded-md border border-line bg-surface-2 px-2.5 py-1.5 text-[13px] font-medium hover:border-text-3"
                      onClick={() =>
                        void downloadAttachment(view.id, a.id, a.original_filename).catch((e: unknown) =>
                          toast.push({ title: 'Download failed', body: e instanceof Error ? e.message : 'Try again.', tone: 'error' }),
                        )
                      }
                    >
                      <span className="truncate">{a.original_filename}</span>
                      <span className="text-xs text-text-3">{formatBytes(a.size_bytes)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  )

  return (
    <li className="flex flex-col gap-3 border-b border-line py-4 last:border-b-0">
      <div className="flex items-start gap-2.5">
        <span
          className={cn(
            'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-xs',
            status.tone === 'warning' && 'border-warning-line bg-warning-soft text-warning',
            status.tone === 'info' && 'border-info-line bg-info-soft text-info',
            status.tone === 'success' && 'border-success-line bg-success-soft text-success',
            status.tone === 'neutral' && 'border-neutral-line bg-neutral-soft text-neutral',
          )}
          aria-hidden="true"
        >
          {n}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold leading-5">{thread.title}</h3>
          <div className="mt-1 flex flex-wrap gap-1.5">
            <span className="inline-flex h-6 items-center rounded-full border border-line bg-surface-2 px-2 text-xs text-text-2">
              Result: {RESULT[thread.result] ?? thread.result}
            </span>
            <StatusBadge label={status.label} tone={status.tone} />
          </div>
        </div>
      </div>
      <div className="rounded-md border border-line bg-surface-2 px-3 py-2.5">
        <div className="text-xs font-semibold uppercase tracking-[0.04em] text-text-3">Your finding on site</div>
        <p className="mt-0.5 text-[13px] leading-5 text-text-2">{thread.comment ?? 'No comment recorded.'}</p>
      </div>
      {earlier.length > 0 ? (
        <button
          type="button"
          className="self-start text-[13px] font-semibold text-text-2 hover:text-text"
          aria-expanded={showEarlier}
          onClick={() => setShowEarlier((v) => !v)}
        >
          {showEarlier ? 'Hide earlier rounds' : `Show earlier rounds (${earlier.length})`}
        </button>
      ) : null}
      <ol className="flex flex-col" aria-label={`Rounds on ${thread.title}`}>
        {showEarlier ? earlier.map(renderRound) : null}
        {current ? renderRound(current) : null}
      </ol>
      {thread.pending_release ? (
        <Alert tone="neutral" title="Not sent yet">
          The operator sees this when {readOnly ? 'the officer requests' : 'you request'} another round.
        </Alert>
      ) : null}
      {readOnly ? null : asking ? (
        <form
          className="flex flex-col gap-3"
          aria-label="Still needs clarification"
          onSubmit={(e) => {
            e.preventDefault()
            if (question.trim().length < 3) {
              setQuestionError('Write what is still unclear; the operator reads it.')
              return
            }
            reopen.mutate(
              { itemId: thread.item_id, message: question.trim() },
              {
                onSuccess: () => {
                  setAsking(false)
                  setQuestion('')
                  toast.push({ title: 'Question drafted', body: 'The operator sees it when you request another round.', tone: 'success' })
                },
                onError: fail('Could not draft the question'),
              },
            )
          }}
        >
          <TextAreaField
            label="What is still unclear"
            required
            value={question}
            error={questionError ?? undefined}
            maxLength={2000}
            placeholder="Shown to the operator with the next round."
            onChange={(e) => {
              setQuestion(e.target.value)
              setQuestionError(null)
            }}
          />
          <div className="flex gap-2">
            <Button type="submit" size="sm" loading={reopen.isPending}>
              Draft the question
            </Button>
            <Button type="button" variant="ghost" size="sm" onClick={() => setAsking(false)} disabled={reopen.isPending}>
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap gap-2">
          {thread.can_resolve ? (
            <Button
              variant="secondary"
              size="sm"
              loading={resolve.isPending}
              disabled={busy}
              onClick={() =>
                resolve.mutate(thread.item_id, {
                  onSuccess: () => toast.push({ title: 'Marked clarified', body: thread.title, tone: 'success' }),
                  onError: fail('Could not mark the item clarified'),
                })
              }
            >
              Mark clarified
            </Button>
          ) : null}
          {thread.can_reopen ? (
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => setAsking(true)}>
              Still needs clarification
            </Button>
          ) : null}
          {thread.can_withdraw ? (
            <Button
              variant="ghost"
              size="sm"
              loading={withdraw.isPending}
              disabled={busy}
              onClick={() =>
                withdraw.mutate(thread.item_id, {
                  onSuccess: () =>
                    toast.push({ title: 'Question withdrawn', body: 'The operator no longer needs to answer it.', tone: 'success' }),
                  onError: fail('Could not withdraw the question'),
                })
              }
            >
              Withdraw
            </Button>
          ) : null}
        </div>
      )}
    </li>
  )
}

/** S-31: the clarification threads on the case rail once the checklist is submitted (US-066). */
export function ClarificationRail({ view }: { view: OfficerApplication }) {
  const c = view.clarification
  if (!c) return null
  return (
    <section className="pf-surface" aria-labelledby="clarification-title">
      <div className="flex flex-col gap-1 border-b border-line px-5 pb-3 pt-5">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
          <h2 id="clarification-title" className="text-[17px] font-semibold leading-6">
            Clarification
          </h2>
          <span className="font-mono text-xs text-text-3">
            {c.open_count} open · {c.answered_count} answered · {c.resolved_count} clarified
            {c.withdrawn_count ? ` · ${c.withdrawn_count} withdrawn` : ''}
          </span>
        </div>
        <p className="text-[13px] leading-[19px] text-text-2">
          {c.turn}
          {c.unreleased_count > 0
            ? `. ${c.unreleased_count} ${c.unreleased_count === 1 ? 'question waits' : 'questions wait'} for Request another round.`
            : '.'}
        </p>
      </div>
      {c.items.length === 0 ? (
        <p className="px-5 py-4 text-sm text-text-2">Nothing to clarify. The officer routes the case to approval when ready.</p>
      ) : (
        <ol className="px-5">
          {c.items.map((t, i) => (
            <Thread key={t.item_id} view={view} thread={t} n={i + 1} />
          ))}
        </ol>
      )}
    </section>
  )
}
