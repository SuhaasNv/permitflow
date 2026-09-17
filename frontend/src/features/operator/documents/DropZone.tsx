import type { DragEvent } from 'react'
import { useId, useRef, useState } from 'react'

import { cn } from '@/lib/cn'

interface DropZoneProps {
  label: string
  hint?: string
  disabled?: boolean
  compact?: boolean
  onFile: (file: File) => void
}

/** Drag-and-drop area with a keyboard-reachable file picker (FR-004). */
export function DropZone({ label, hint = 'PDF, PNG, JPG or TXT · up to 10 MB', disabled, compact, onFile }: DropZoneProps) {
  const [over, setOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setOver(false)
    if (disabled) return
    const file = e.dataTransfer.files[0]
    if (file) onFile(file)
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      className={cn(
        'rounded-lg border-[1.5px] border-dashed text-center transition-colors',
        compact ? 'px-4 py-4' : 'px-6 py-7',
        over ? 'border-primary bg-primary-soft' : 'border-line-strong bg-surface hover:border-text-3',
        disabled && 'opacity-60',
      )}
    >
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.txt,application/pdf,image/png,image/jpeg,text/plain"
        className="sr-only"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
          e.target.value = ''
        }}
      />
      {!compact ? (
        <div className="mx-auto mb-2.5 flex h-11 w-11 items-center justify-center rounded-full bg-neutral-soft text-text-2">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <path d="m17 8-5-5-5 5M12 3v12" />
          </svg>
        </div>
      ) : null}
      <div className={cn('font-semibold', over && 'text-primary')}>
        {over ? 'Drop to upload' : label}{' '}
        {!over ? (
          <label htmlFor={inputId} className="cursor-pointer text-primary underline-offset-2 hover:underline">
            browse
          </label>
        ) : null}
      </div>
      <div className="mt-0.5 text-[13px] text-text-2">{hint}</div>
    </div>
  )
}
