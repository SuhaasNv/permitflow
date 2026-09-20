import { useIsMutating } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import type { StorageView } from '@/api/applications'
import type { ClarificationItem } from '@/api/clarification'
import { downloadAttachment } from '@/api/clarification'
import { AppError } from '@/api/client'
import { validateFile } from '@/api/documents'
import { Alert } from '@/features/shared/Alert'
import { Button, buttonClasses } from '@/features/shared/Button'
import { TextAreaField } from '@/features/shared/Controls'
import { Dialog } from '@/features/shared/Dialog'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { StorageRoom } from '@/features/shared/StorageRoom'
import type { Tone } from '@/features/shared/StatusBadge'
import { ErrorPanel, NotFoundPanel, PageSkeleton, Skeleton } from '@/features/shared/states'
import { useToast } from '@/features/shared/Toast'
import { formatBytes, formatDateTime } from '@/lib/format'
import { ApplicationHeader } from './ApplicationHeader'
import { useApplication, useAttach, useClarifications, useRemoveAttachment, useRespond, useSendClarifications } from './queries'

const TONE: Record<string, Tone> = {
  'Waiting for your response': 'warning',
  Sent: 'info',
  Clarified: 'success',
  'No longer needed': 'neutral',
}

const ATTACHMENT_CAP = 3

/** One item's answer: text saved on blur, files added through the camera or a picker, removable until sent. */
function ItemAnswer({ appId, item, storage }: { appId: string; item: ClarificationItem; storage: StorageView | null }) {
  const respond = useRespond(appId)
  const attach = useAttach(appId)
  const remove = useRemoveAttachment(appId)
  const toast = useToast()
  // The answer of the current round only; earlier rounds are shown read-only under their question.
  const latest = item.responses.find((r) => r.round_no === item.round_no) ?? null
  const [text, setText] = useState(latest?.message ?? '')
  const [fileError, setFileError] = useState<string | null>(null)
  const saved = useRef(latest?.message ?? '')
  const fileInput = useRef<HTMLInputElement>(null)
  const cameraInput = useRef<HTMLInputElement>(null)
  useEffect(() => {
    // Another tab or a refetch changed the saved answer: follow it unless the operator is mid-edit here.
    const next = latest?.message ?? ''
    if (next !== saved.current && text === saved.current) setText(next)
    saved.current = next
    // eslint-disable-next-line react-hooks/exhaustive-deps -- follows the server copy only
  }, [latest?.message])

  const saveText = () => {
    const value = text.trim()
    if (!value || value === saved.current) return
    respond.mutate(
      { itemId: item.item_id, message: value },
      {
        onError: (e) => {
          const fields = e instanceof AppError && e.status === 422 ? e.details?.fields : null
          const msg =
            fields && typeof fields === 'object' && 'message' in fields ? String((fields as Record<string, unknown>).message) : e.message
          toast.push({ title: 'Could not save your answer', body: msg, tone: 'error' })
        },
      },
    )
  }
  const addFiles = (files: FileList | null) => {
    if (!files || !latest) return
    setFileError(null)
    const count = latest.attachments.length
    for (const [n, file] of Array.from(files).entries()) {
      if (count + n >= ATTACHMENT_CAP) {
        setFileError(`Up to ${ATTACHMENT_CAP} files per answer.`)
        break
      }
      const problem = validateFile(file)
      if (problem) {
        setFileError(problem)
        continue
      }
      attach.mutate(
        { responseId: latest.id, file },
        {
          onSuccess: (r) => {
            if (r.unchanged) toast.push({ title: 'No change', body: `${file.name} is already attached.`, tone: 'info' })
          },
          onError: (e) => setFileError(e.message),
        },
      )
    }
  }
  const attachments = latest?.attachments ?? []
  const sent = latest?.sent_at != null
  const canEdit = item.can_respond && !sent

  return (
    <div className="flex flex-col gap-3">
      {canEdit ? (
        <TextAreaField
          label="Your answer"
          required
          value={text}
          maxLength={2000}
          placeholder="What was done, when, and anything the officer should know."
          onChange={(e) => setText(e.target.value)}
          onBlur={saveText}
          help={
            respond.isPending ? 'Saving your answer…' : latest ? 'Saved. Sent with the round when you press Send responses.' : undefined
          }
        />
      ) : latest ? (
        <div className="rounded-md border border-line px-4 py-3">
          <div className="text-xs font-semibold uppercase tracking-[0.04em] text-text-3">
            Your answer{latest.sent_at ? `, sent ${formatDateTime(latest.sent_at)}` : ''}
          </div>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-5">{latest.message}</p>
        </div>
      ) : null}
      {latest ? (
        <div className="flex flex-col gap-2">
          {attachments.length > 0 ? (
            <ul className="flex flex-col gap-1.5">
              {attachments.map((a) => (
                <li
                  key={a.id}
                  className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border border-line bg-surface-2 px-3 py-2 text-sm"
                >
                  <button
                    type="button"
                    className="min-w-0 flex-1 truncate text-left font-medium hover:underline"
                    onClick={() =>
                      void downloadAttachment(appId, a.id, a.original_filename).catch((e: unknown) =>
                        toast.push({ title: 'Download failed', body: e instanceof Error ? e.message : 'Try again.', tone: 'error' }),
                      )
                    }
                  >
                    {a.original_filename}
                  </button>
                  <span className="text-xs text-text-3">{formatBytes(a.size_bytes)}</span>
                  {canEdit ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      loading={remove.isPending && remove.variables?.attachmentId === a.id}
                      onClick={() =>
                        remove.mutate(
                          { responseId: latest.id, attachmentId: a.id },
                          { onError: (e) => toast.push({ title: 'Could not remove the file', body: e.message, tone: 'error' }) },
                        )
                      }
                    >
                      Remove
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
          {canEdit ? (
            <div className="flex flex-wrap items-center gap-2">
              <input
                ref={cameraInput}
                type="file"
                accept="image/jpeg,image/png"
                capture="environment"
                className="sr-only"
                onChange={(e) => {
                  addFiles(e.target.files)
                  e.target.value = ''
                }}
              />
              <input
                ref={fileInput}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain"
                multiple
                className="sr-only"
                onChange={(e) => {
                  addFiles(e.target.files)
                  e.target.value = ''
                }}
              />
              <Button
                variant="secondary"
                size="sm"
                className="sm:hidden"
                disabled={attach.isPending || attachments.length >= ATTACHMENT_CAP}
                onClick={() => cameraInput.current?.click()}
              >
                Take a photo
              </Button>
              <Button
                variant="secondary"
                size="sm"
                loading={attach.isPending}
                disabled={attachments.length >= ATTACHMENT_CAP}
                onClick={() => fileInput.current?.click()}
              >
                Choose a file
              </Button>
              <span className="text-xs text-text-3">
                {attachments.length} of {ATTACHMENT_CAP} files attached. PDF, PNG, JPG or TXT, up to 10 MB each; photos are stored without their
                camera data. <StorageRoom storage={storage} />
              </span>
            </div>
          ) : null}
          {fileError ? (
            <p role="alert" className="text-[13px] font-medium text-error">
              {fileError}
            </p>
          ) : null}
        </div>
      ) : canEdit ? (
        <p className="text-xs text-text-3">Write your answer first; files can be attached once it is saved.</p>
      ) : null}
    </div>
  )
}

/** S-18: only the flagged items, the officer's question first on each, an answer and evidence per item, one Send (US-064, US-065). */
export function ClarificationPage() {
  const { id = '' } = useParams()
  const app = useApplication(id)
  const clar = useClarifications(id)
  const send = useSendClarifications(id)
  const toast = useToast()
  const [confirming, setConfirming] = useState(false)
  // An answer or a file still on its way to the server: the send waits so nothing typed is left behind.
  const saving = useIsMutating({ mutationKey: ['clarification', id] }) > 0

  if (app.isError && app.data === undefined) {
    if (app.error instanceof AppError && app.error.status === 404)
      return <NotFoundPanel backTo="/app/applications" backLabel="Back to my applications" />
    return <ErrorPanel error={app.error} onRetry={() => void app.refetch()} />
  }
  if (clar.isError && clar.data === undefined) return <ErrorPanel error={clar.error} onRetry={() => void clar.refetch()} />
  if (!app.data || !clar.data) {
    return (
      <PageSkeleton label="Loading clarification">
        <Skeleton className="h-10 w-1/2" />
        <Skeleton className="mt-6 h-64" />
      </PageSkeleton>
    )
  }
  const view = app.data
  const c = clar.data
  const open = c.items.filter((i) => i.status === 'Waiting for your response')
  const unanswered = open.filter((i) => !(i.responses.at(-1)?.message ?? '').trim())
  const base = `/app/applications/${id}`
  const doSend = () =>
    send.mutate(undefined, {
      onSuccess: (next) => {
        setConfirming(false)
        toast.push({
          title: 'Answers sent',
          body: `${next.answered_count} ${next.answered_count === 1 ? 'answer was' : 'answers were'} sent to the licensing office.`,
          tone: 'success',
        })
      },
      onError: (e) => {
        setConfirming(false)
        if (e instanceof AppError && e.status === 409) {
          toast.push({ title: 'Could not send', body: 'This application changed since you opened it. Showing the latest.', tone: 'error' })
          void clar.refetch()
          return
        }
        toast.push({ title: 'Could not send', body: e.message, tone: 'error' })
      },
    })

  return (
    <>
      <ApplicationHeader
        view={view}
        crumb="Clarification"
        actions={
          <Link to={base} className={buttonClasses('secondary', 'sm')}>
            Back to the application
          </Link>
        }
      />
      {c.items.length === 0 ? (
        <section className="pf-surface px-5 py-8 text-center" aria-labelledby="clar-empty">
          <h2 id="clar-empty" className="text-[17px] font-semibold">
            Nothing needs your response yet
          </h2>
          <p className="mx-auto mt-1 max-w-[46ch] text-sm leading-[21px] text-text-2">
            When the licensing officer needs more information after the site visit, the items in question appear here with the officer's
            note on each.
          </p>
        </section>
      ) : (
        <>
          <div className="mb-5">
            <Alert
              tone={open.length > 0 ? 'warning' : 'info'}
              title={
                open.length > 0
                  ? `Round ${c.round}: ${open.length} of ${c.items.length} ${c.items.length === 1 ? 'item needs' : 'items need'} your response`
                  : `Round ${c.round}: every item is answered`
              }
            >
              {open.length > 0
                ? 'Answer each item below, attach a photo or a file where it helps, then press Send responses. Nothing reaches the officer until you send.'
                : 'The officer is reading your answers. You will be told here and by notification if anything else is needed.'}
            </Alert>
          </div>
          <ol className="flex flex-col gap-4 pb-24">
            {c.items.map((item, n) => (
              <li key={item.item_id} className="pf-surface px-5 py-5" id={`item-${item.key}`}>
                <div className="flex flex-wrap items-start gap-3">
                  <span className="font-mono text-[13px] leading-6 text-text-3">{String(n + 1).padStart(2, '0')}</span>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-base font-semibold leading-6">{item.title}</h2>
                    {item.guidance ? <p className="text-[13px] leading-5 text-text-3">{item.guidance}</p> : null}
                  </div>
                  <StatusBadge label={item.status} tone={TONE[item.status] ?? 'neutral'} />
                </div>
                <div className="mt-4 flex flex-col gap-3 sm:pl-[34px]">
                  {item.requests.map((q) => {
                    const earlier = q.round_no < item.round_no ? item.responses.find((r) => r.round_no === q.round_no) : null
                    return (
                      <div key={q.id} className="flex flex-col gap-2">
                        <div className="rounded-md border border-line bg-surface-2 px-4 py-3">
                          <div className="text-xs font-semibold uppercase tracking-[0.04em] text-text-3">
                            The officer asked{item.requests.length > 1 ? ` (round ${q.round_no})` : ''}
                          </div>
                          <p className="mt-1 text-sm leading-5 text-text">{q.message}</p>
                          <div className="mt-1 text-xs text-text-3">{formatDateTime(q.released_at)}</div>
                        </div>
                        {earlier ? (
                          <div className="rounded-md border border-line px-4 py-3">
                            <div className="text-xs font-semibold uppercase tracking-[0.04em] text-text-3">
                              You answered{earlier.sent_at ? `, sent ${formatDateTime(earlier.sent_at)}` : ''}
                            </div>
                            <p className="mt-1 whitespace-pre-wrap text-sm leading-5">{earlier.message}</p>
                            {earlier.attachments.length ? (
                              <p className="mt-1 text-xs text-text-3">{earlier.attachments.map((a) => a.original_filename).join(', ')}</p>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                  <ItemAnswer
                    key={`${item.round_no}-${item.responses.find((r) => r.round_no === item.round_no)?.id ?? 'none'}`}
                    appId={id}
                    item={item}
                    storage={view.storage}
                  />
                </div>
              </li>
            ))}
          </ol>
          {c.can_respond ? (
            <div className="sticky bottom-0 mt-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface px-5 py-3.5 shadow-[0_-8px_24px_rgba(27,36,48,0.06)] max-lg:bottom-[64px]">
              <span className="text-sm text-text-2">
                {unanswered.length === 0
                  ? `Every item is answered. Send ${open.length === 1 ? 'your answer' : `your ${open.length} answers`} to the licensing office.`
                  : `${unanswered.length} of ${open.length} ${open.length === 1 ? 'item' : 'items'} still ${unanswered.length === 1 ? 'needs' : 'need'} an answer.`}
              </span>
              <Button
                size="lg"
                disabled={!c.can_send || saving}
                title={saving ? 'Wait for your answer to save.' : c.can_send ? undefined : 'Answer every item first.'}
                onClick={() => setConfirming(true)}
              >
                Send responses
              </Button>
            </div>
          ) : null}
        </>
      )}
      <Dialog
        open={confirming}
        title="Send your answers?"
        confirmLabel="Send responses"
        busy={send.isPending}
        onConfirm={doSend}
        onCancel={() => setConfirming(false)}
      >
        <p>
          {open.length === 1 ? 'Your answer and its files are' : `Your ${open.length} answers and their files are`} sent to the licensing
          office as one round. Once sent they cannot change; the officer may ask again on any item.
        </p>
      </Dialog>
    </>
  )
}
