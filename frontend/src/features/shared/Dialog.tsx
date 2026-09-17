import type { ReactNode } from 'react'
import { useEffect, useRef } from 'react'

import { Button } from './Button'

export interface DialogProps {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel: string
  cancelLabel?: string
  danger?: boolean
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
}

/** Confirmation dialog: title as a question, consequence in plain language, one primary action. Enters with a 220 ms rise. */
export function Dialog({ open, title, children, confirmLabel, cancelLabel = 'Cancel', danger, busy, onConfirm, onCancel }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (open && !el.open) el.showModal()
    if (!open && el.open) el.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault()
        onCancel()
      }}
      className="pf-dialog m-auto w-[min(520px,calc(100vw-32px))] rounded-lg border border-line bg-surface p-0 text-text shadow-[var(--shadow-3)] backdrop:bg-[rgba(16,24,40,0.5)]"
      aria-labelledby="dialog-title"
    >
      <div className="px-6 pb-2 pt-6">
        <h2 id="dialog-title" className="text-[20px] font-semibold leading-7 tracking-[-0.01em]">
          {title}
        </h2>
      </div>
      <div className="flex flex-col gap-3 px-6 pb-6 text-sm leading-[21px] text-text-2">{children}</div>
      <div className="flex justify-end gap-2 border-t border-line bg-surface-2 px-6 py-3.5">
        <Button variant="ghost" onClick={onCancel} disabled={busy}>
          {cancelLabel}
        </Button>
        <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} loading={busy} autoFocus>
          {confirmLabel}
        </Button>
      </div>
    </dialog>
  )
}
