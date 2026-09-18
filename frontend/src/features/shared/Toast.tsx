import type { ReactNode } from 'react'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

import { cn } from '@/lib/cn'

type ToastTone = 'neutral' | 'success' | 'error' | 'info'

export interface ToastInput {
  title: string
  body?: string
  tone?: ToastTone
  /** Milliseconds before auto-dismiss. Errors stay until dismissed. */
  duration?: number
}

interface Toast extends ToastInput {
  id: number
  leaving: boolean
}

interface ToastApi {
  push: (toast: ToastInput) => void
}

const ToastContext = createContext<ToastApi | null>(null)

const PATHS: Record<ToastTone, string> = {
  neutral: 'M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
  info: 'M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
  success: 'M20 6 9 17l-5-5',
  error: 'M12 8v4.5M12 16h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z',
}
const TINT: Record<ToastTone, string> = {
  neutral: 'bg-surface-3 text-text-2',
  info: 'bg-info-soft text-info',
  success: 'bg-success-soft text-success',
  error: 'bg-error-soft text-error',
}

const LEAVE_MS = 220

/** Bottom-right stack (above the phone tab bar). Polite live region; at most four visible. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())

  const dismiss = useCallback((id: number) => {
    setToasts((list) => list.map((t) => (t.id === id ? { ...t, leaving: true } : t)))
    const timer = setTimeout(() => {
      setToasts((list) => list.filter((t) => t.id !== id))
      timers.current.delete(id)
    }, LEAVE_MS)
    timers.current.set(id, timer)
  }, [])

  const push = useCallback(
    (input: ToastInput) => {
      const id = nextId.current++
      const tone = input.tone ?? 'neutral'
      setToasts((list) => [...list.slice(-3), { ...input, tone, id, leaving: false }])
      const duration = input.duration ?? (tone === 'error' ? 0 : 4500)
      if (duration > 0)
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), duration),
        )
    },
    [dismiss],
  )

  useEffect(() => {
    const active = timers.current
    return () => {
      for (const timer of active.values()) clearTimeout(timer)
      active.clear()
    }
  }, [])

  const api = useMemo(() => ({ push }), [push])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-4 bottom-[76px] z-40 flex flex-col items-end gap-2 sm:inset-x-auto sm:bottom-6 sm:right-6 sm:w-[380px]"
        aria-live="polite"
        aria-relevant="additions"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={cn(
              'pointer-events-auto flex w-full items-start gap-3 rounded-lg border border-line bg-surface px-4 py-3 shadow-[var(--shadow-2)]',
              t.leaving ? 'pf-toast-out' : 'pf-toast-in',
            )}
          >
            <span className={cn('mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full', TINT[t.tone ?? 'neutral'])}>
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d={PATHS[t.tone ?? 'neutral']} />
              </svg>
            </span>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold leading-5 text-text">{t.title}</div>
              {t.body ? <div className="mt-0.5 text-[13px] leading-[18px] text-text-2">{t.body}</div> : null}
            </div>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="-mr-1.5 -mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-text-3 transition-colors hover:bg-neutral-soft hover:text-text"
              aria-label="Dismiss"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                aria-hidden="true"
              >
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

/** No-op outside a provider so components stay testable in isolation. */
export function useToast(): ToastApi {
  const api = useContext(ToastContext)
  return api ?? { push: () => undefined }
}
