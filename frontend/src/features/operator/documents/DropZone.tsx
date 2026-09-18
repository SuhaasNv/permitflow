import type { DragEvent } from 'react'
import { useId, useRef, useState } from 'react'

import { cn } from '@/lib/cn'

interface DropZoneProps {
  label: string
  hint?: string
  disabled?: boolean
  compact?: boolean
  onFile: (file: File) => void
  /** Called when more than one file is dropped; the first is still used. */
  onExtraFiles?: (count: number) => void
}

/** Drag-and-drop area with a keyboard-reachable file picker (FR-004). The whole zone is the click target. */
export function DropZone({ label, hint = 'PDF, PNG, JPG or TXT · up to 10 MB', disabled, compact, onFile, onExtraFiles }: DropZoneProps) {
  const [over, setOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setOver(false)
    if (disabled) return
    const file = e.dataTransfer.files[0]
    if (e.dataTransfer.files.length > 1) onExtraFiles?.(e.dataTransfer.files.length - 1)
    if (file) onFile(file)
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = disabled ? 'none' : 'copy'
        if (!disabled) setOver(true)
      }}
      onDragLeave={(e) => {
        // Moving over a child fires dragleave on the parent; only clear when the cursor really left.
        if (e.currentTarget.contains(e.relatedTarget as Node | null)) return
        setOver(false)
      }}
      onDrop={onDrop}
      className={cn(
        'relative rounded-lg border-[1.5px] border-dashed text-center',
        'transition-[border-color,background-color,transform] duration-[var(--dur-base)] ease-[var(--ease-out)]',
        compact ? 'px-4 py-4' : 'px-6 py-8',
        over ? 'scale-[1.005] border-text bg-surface-3' : 'border-line-strong bg-surface-2/60 hover:border-text-3 hover:bg-surface-2',
        disabled && 'opacity-60',
      )}
    >
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain"
        className="peer sr-only"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
          e.target.value = ''
        }}
      />
      <label
        htmlFor={inputId}
        className="absolute inset-0 cursor-pointer rounded-lg peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus"
      >
        <span className="sr-only">{label}</span>
      </label>
      {!compact ? (
        <div
          className={cn(
            'mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-surface text-text-2 shadow-[var(--shadow-1)]',
            'transition-transform duration-[var(--dur-base)] ease-[var(--ease-out)]',
            over && '-translate-y-0.5',
          )}
        >
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
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <path d="m17 8-5-5-5 5M12 3v12" />
          </svg>
        </div>
      ) : null}
      <div className="text-[15px] font-semibold">
        {over ? 'Drop to upload' : label}{' '}
        {!over ? (
          <span className="font-semibold text-primary underline decoration-primary-line underline-offset-[3px]">browse files</span>
        ) : null}
      </div>
      <div className="mt-1 text-[13px] text-text-3">{hint}</div>
    </div>
  )
}
