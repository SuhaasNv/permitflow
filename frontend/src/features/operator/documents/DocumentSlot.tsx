import { useState } from 'react'

import type { DocumentSlotView } from '@/api/applications'
import { AppError } from '@/api/client'
import { deleteDocument, downloadDocument, uploadDocument, validateFile } from '@/api/documents'
import type { UploadResult } from '@/api/documents'
import { Alert } from '@/features/shared/Alert'
import { Button } from '@/features/shared/Button'
import { Dialog } from '@/features/shared/Dialog'
import { cn } from '@/lib/cn'
import { formatBytes, formatDateTime } from '@/lib/format'
import { DropZone } from './DropZone'
import { VerificationBlock } from './VerificationBlock'

interface DocumentSlotProps {
  applicationId: string
  slot: DocumentSlotView
  canDelete: boolean
  onUploaded: (result: UploadResult) => void
  onDeleted: (view: UploadResult['application']) => void
}

type UploadState =
  { phase: 'idle' } | { phase: 'uploading'; name: string; fraction: number } | { phase: 'error'; message: string } | { phase: 'unchanged' }

const FileIcon = ({ image }: { image: boolean }) => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
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

/** One required document type: empty drop zone, or the current file with its verification result. */
export function DocumentSlot({ applicationId, slot, canDelete, onUploaded, onDeleted }: DocumentSlotProps) {
  const [state, setState] = useState<UploadState>({ phase: 'idle' })
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [busy, setBusy] = useState(false)
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
      setState(result.unchanged ? { phase: 'unchanged' } : { phase: 'idle' })
      onUploaded(result)
    } catch (error) {
      setState({
        phase: 'error',
        message: error instanceof Error ? error.message : 'Upload failed. Try again.',
      })
    }
  }

  const remove = async () => {
    if (!doc) return
    setBusy(true)
    try {
      onDeleted(await deleteDocument(applicationId, doc.id))
      setConfirmDelete(false)
    } catch (error) {
      setState({
        phase: 'error',
        message: error instanceof AppError ? error.message : 'Could not remove this file.',
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section
      className="overflow-hidden rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]"
      aria-labelledby={`slot-${slot.type}`}
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-neutral-soft text-text-2">
          <FileIcon image={Boolean(doc?.content_type.startsWith('image/'))} />
        </span>
        <div className="min-w-0 flex-1">
          <h3 id={`slot-${slot.type}`} className={cn('text-sm font-semibold', doc && 'break-all')}>
            {doc ? doc.original_filename : slot.label}
          </h3>
          <div className="text-xs text-text-3">
            {doc
              ? `${slot.label} · ${formatBytes(doc.size_bytes)} · uploaded ${formatDateTime(doc.uploaded_at)}`
              : 'Required · not uploaded yet'}
            {doc?.replaces_filename ? ` · replaces ${doc.replaces_filename}` : ''}
          </div>
        </div>
        {doc ? (
          <span className="inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-full border border-success-line bg-success-soft px-2 text-xs font-semibold text-success">
            <span className="h-[7px] w-[7px] rounded-full bg-current" aria-hidden="true" />
            Upload complete
          </span>
        ) : (
          <span className="inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-full border border-neutral-line bg-neutral-soft px-2 text-xs font-semibold text-neutral">
            <span className="h-[7px] w-[7px] rounded-full bg-current" aria-hidden="true" />
            Missing
          </span>
        )}
      </div>

      {state.phase === 'error' ? (
        <div className="px-4 pb-3">
          <Alert tone="error">
            <span>{state.message}</span>
          </Alert>
        </div>
      ) : null}
      {state.phase === 'unchanged' ? (
        <div className="px-4 pb-3">
          <Alert tone="info">
            <span>This is the same file as the one already attached, so nothing changed.</span>
          </Alert>
        </div>
      ) : null}

      {state.phase === 'uploading' ? (
        <div className="flex flex-col gap-1.5 border-t border-line px-4 py-3" aria-live="polite">
          <div className="flex justify-between text-[13px]">
            <span className="truncate font-medium">Uploading {state.name}</span>
            <span className="tabular-nums text-text-3">{Math.round(state.fraction * 100)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-sm bg-neutral-soft">
            <div className="h-full rounded-sm bg-primary transition-[width]" style={{ width: `${Math.max(4, state.fraction * 100)}%` }} />
          </div>
        </div>
      ) : null}

      {doc?.verification ? <VerificationBlock verification={doc.verification} /> : null}

      {!doc && state.phase !== 'uploading' && slot.editable ? (
        <div className="px-4 pb-4">
          <DropZone label={`Drop your ${slot.label.toLowerCase()} here, or`} onFile={start} />
        </div>
      ) : null}

      {doc ? (
        <div className="flex flex-wrap items-center gap-2 border-t border-line bg-surface-2 px-4 py-2">
          <Button variant="ghost" size="sm" onClick={() => void downloadDocument(applicationId, doc.id, doc.original_filename)}>
            Download
          </Button>
          {slot.editable ? (
            <label className="inline-flex h-8 cursor-pointer items-center rounded-md border border-line-strong bg-surface px-3 text-[13px] font-semibold text-text shadow-[var(--shadow-1)] hover:bg-surface-2">
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
            <Button variant="ghost" size="sm" className="ml-auto" onClick={() => setConfirmDelete(true)}>
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
