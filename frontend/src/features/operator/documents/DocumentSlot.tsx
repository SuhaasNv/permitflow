import { useState } from 'react'

import type { DocumentSlotView } from '@/api/applications'
import { AppError } from '@/api/client'
import { deleteDocument, downloadDocument, rerunVerification, uploadDocument, validateFile } from '@/api/documents'
import type { UploadResult } from '@/api/documents'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { Dialog } from '@/features/shared/Dialog'
import { StatusBadge } from '@/features/shared/StatusBadge'
import { useToast } from '@/features/shared/Toast'
import { cn } from '@/lib/cn'
import { formatBytes, formatDateTime } from '@/lib/format'
import { DropZone } from './DropZone'
import { VerificationBlock } from './VerificationBlock'

interface DocumentSlotProps {
  applicationId: string
  slot: DocumentSlotView
  index: number
  canDelete: boolean
  onUploaded: (result: UploadResult) => void
  onDeleted: (view: UploadResult['application']) => void
}

type UploadState = { phase: 'idle' } | { phase: 'uploading'; name: string; fraction: number } | { phase: 'error'; message: string }

const FileIcon = ({ image }: { image: boolean }) => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {image ? (
      <>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <path d="m21 15-5-5L5 21" />
      </>
    ) : (
      <>
        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z" />
        <path d="M14 2v6h6" />
      </>
    )}
  </svg>
)

const RERUNNABLE = new Set(['verified', 'issues_found', 'needs_review', 'unreadable', 'failed', 'unavailable'])

/** One required document type: empty drop zone, or the current file with its verification result. */
export function DocumentSlot({ applicationId, slot, index, canDelete, onUploaded, onDeleted }: DocumentSlotProps) {
  const [state, setState] = useState<UploadState>({ phase: 'idle' })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState(false)
  const toast = useToast()
  const doc = slot.document

  const start = async (file: File) => {
    const clientError = validateFile(file)
    if (clientError) {
      setState({ phase: 'error', message: clientError })
      return
    }
    setState({ phase: 'uploading', name: file.name, fraction: 0 })
    try {
      const result = await uploadDocument(applicationId, slot.type, file, (fraction) =>
        setState({ phase: 'uploading', name: file.name, fraction }),
      )
      setState({ phase: 'idle' })
      onUploaded(result)
      if (result.unchanged) {
        toast.push({ title: 'No change', body: `${file.name} is identical to the file already attached.`, tone: 'info' })
      } else {
        toast.push({ title: 'Document uploaded', body: `${file.name} is attached and being checked.`, tone: 'success' })
      }
    } catch (error) {
      setState({ phase: 'error', message: error instanceof Error ? error.message : 'Upload failed. Try again.' })
    }
  }

  const rerun = async () => {
    if (!doc) return
    setBusy(true)
    try {
      onUploaded(await rerunVerification(applicationId, doc.id))
      setState({ phase: 'idle' })
    } catch (error) {
      setState({ phase: 'error', message: error instanceof AppError ? error.message : 'Could not re-run the check.' })
    } finally {
      setBusy(false)
    }
  }

  const remove = async () => {
    if (!doc) return
    setBusy(true)
    try {
      onDeleted(await deleteDocument(applicationId, doc.id))
      setConfirmDelete(false)
      toast.push({ title: 'Document removed', body: `${slot.label} is no longer attached.` })
    } catch (error) {
      setState({ phase: 'error', message: error instanceof AppError ? error.message : 'Could not remove this file.' })
    } finally {
      setBusy(false)
    }
  }

  const live = doc?.verification?.status === 'running' || doc?.verification?.status === 'pending'

  return (
    <section className="pf-surface overflow-hidden" aria-labelledby={`slot-${slot.type}`}>
      <div className="flex items-center gap-3.5 px-4 py-4 sm:px-5">
        <span
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-md transition-colors duration-[var(--dur-base)]',
            doc ? 'bg-ink text-white' : 'bg-surface-3 text-text-2',
          )}
        >
          <FileIcon image={Boolean(doc?.content_type.startsWith('image/'))} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-xs text-text-3">0{index + 1}</span>
            <h3 id={`slot-${slot.type}`} className="text-[15px] font-semibold leading-[22px]">
              {slot.label}
            </h3>
          </div>
          <div className={cn('text-[13px] text-text-3', doc && 'truncate')}>
            {doc ? (
              <>
                <span className="text-text-2">{doc.original_filename}</span> · {formatBytes(doc.size_bytes)} · uploaded{' '}
                {formatDateTime(doc.uploaded_at)}
                {doc.replaces_filename ? ` · replaces ${doc.replaces_filename}` : ''}
              </>
            ) : (
              'Required · not uploaded yet'
            )}
          </div>
        </div>
        {doc ? (
          live ? (
            <StatusBadge label="Checking" tone="info" live />
          ) : (
            <StatusBadge label="Uploaded" tone="success" />
          )
        ) : (
          <StatusBadge label="Missing" tone="neutral" />
        )}
      </div>

      {state.phase === 'error' ? (
        <div className="px-4 pb-4 sm:px-5">
          <Alert tone="error" title="Upload not accepted">
            {state.message}
          </Alert>
        </div>
      ) : null}

      {state.phase === 'uploading' ? (
        <div className="flex flex-col gap-2 border-t border-line px-4 py-4 sm:px-5" aria-live="polite">
          <div className="flex justify-between text-[13px]">
            <span className="truncate font-medium">Uploading {state.name}</span>
            <span className="font-mono tabular-nums text-text-3">{Math.round(state.fraction * 100)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-3">
            <div
              className="h-full rounded-full bg-text transition-[width] duration-[var(--dur-base)] ease-[var(--ease-out)]"
              style={{ width: `${Math.max(4, state.fraction * 100)}%` }}
            />
          </div>
        </div>
      ) : null}

      {doc?.verification ? <VerificationBlock verification={doc.verification} /> : null}

      {!doc && state.phase !== 'uploading' && slot.editable ? (
        <div className="px-4 pb-4 sm:px-5">
          <DropZone label={`Drop your ${slot.label.toLowerCase()} here, or`} onFile={start} />
        </div>
      ) : null}

      {doc ? (
        <div className="flex flex-wrap items-center gap-1 border-t border-line bg-surface-2 px-3 py-2 sm:px-4">
          <Button variant="ghost" size="sm" onClick={() => void downloadDocument(applicationId, doc.id, doc.original_filename)}>
            Download
          </Button>
          {doc.verification && RERUNNABLE.has(doc.verification.status) ? (
            <Button variant="ghost" size="sm" loading={busy} onClick={() => void rerun()}>
              Re-run check
            </Button>
          ) : null}
          {slot.editable ? (
            <label className="inline-flex h-8 cursor-pointer items-center rounded-md px-3 text-[13px] font-semibold text-text-2 transition-colors hover:bg-neutral-soft hover:text-text">
              Replace file
              <input
                type="file"
                className="sr-only"
                accept=".pdf,.png,.jpg,.jpeg,.txt"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) void start(file)
                  e.target.value = ''
                }}
              />
            </label>
          ) : null}
          {slot.editable && canDelete ? (
            <Button variant="ghost" size="sm" className="ml-auto text-text-3" onClick={() => setConfirmDelete(true)}>
              Remove
            </Button>
          ) : null}
        </div>
      ) : null}

      <Dialog
        open={confirmDelete}
        title="Remove this document?"
        confirmLabel="Remove"
        danger
        busy={busy}
        onConfirm={() => void remove()}
        onCancel={() => setConfirmDelete(false)}
      >
        <p>
          {doc?.original_filename} will be removed from this application. You can upload another {slot.label.toLowerCase()} afterwards.
        </p>
      </Dialog>
    </section>
  )
}
