import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { Role } from '@/api/auth'
import type { NotificationItem } from '@/api/notifications'
import { getNotifications, markAllNotificationsRead, markNotificationRead } from '@/api/notifications'
import { cn } from '@/lib/cn'
import { formatRelative } from '@/lib/format'

const KEY = ['notifications'] as const

function targetFor(role: Role, item: NotificationItem): string {
  return role === 'operator' ? `/app/applications/${item.application_id}` : `/officer/applications/${item.application_id}`
}

/** Bell with unread count and a popover list (S-17). Polls every 30 s; a new unread item pulses the dot once. */
export function NotificationsBell({ role }: { role: Role }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const query = useQuery({ queryKey: KEY, queryFn: getNotifications, refetchInterval: 30_000, refetchOnWindowFocus: true })
  const readOne = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => void qc.invalidateQueries({ queryKey: KEY }),
  })
  const readAll = useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: (data) => qc.setQueryData(KEY, data),
  })

  useEffect(() => {
    if (!open) return
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const unread = query.data?.unread_count ?? 0
  const items = query.data?.items ?? []

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className={cn(
          'relative flex h-10 w-10 items-center justify-center rounded-md text-text-2 transition-colors hover:bg-neutral-soft hover:text-text',
          open && 'bg-neutral-soft text-text',
        )}
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : 'Notifications'}
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((v) => !v)}
      >
        <svg
          width="19"
          height="19"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.94 1.94 0 0 0 3.4 0" />
        </svg>
        {unread > 0 ? (
          <span
            className="absolute right-1.5 top-1.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-primary px-1 font-mono text-[10px] font-semibold leading-none text-white"
            aria-hidden="true"
          >
            {unread > 9 ? '9+' : unread}
          </span>
        ) : null}
      </button>
      {open ? (
        <div
          role="dialog"
          aria-label="Notifications"
          className="pf-enter-fast absolute right-0 top-12 z-40 w-[min(380px,calc(100vw-24px))] overflow-hidden rounded-lg border border-line bg-surface shadow-[var(--shadow-2)]"
        >
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <span className="text-sm font-semibold">Notifications</span>
            {unread > 0 ? (
              <button
                type="button"
                className="text-xs font-semibold text-text-2 hover:text-text"
                onClick={() => readAll.mutate()}
                disabled={readAll.isPending}
              >
                Mark all as read
              </button>
            ) : (
              <span className="text-xs text-text-3">All read</span>
            )}
          </div>
          {items.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-text-3">Nothing yet. Status changes on your applications appear here.</p>
          ) : (
            <ul className="max-h-[60vh] divide-y divide-line overflow-y-auto">
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    className={cn(
                      'flex w-full gap-3 px-4 py-3 text-left transition-colors hover:bg-surface-2',
                      !item.read_at && 'bg-primary-soft/40',
                    )}
                    onClick={() => {
                      if (!item.read_at) readOne.mutate(item.id)
                      setOpen(false)
                      navigate(targetFor(role, item))
                    }}
                  >
                    <span
                      className={cn('mt-2 h-[7px] w-[7px] shrink-0 rounded-full', item.read_at ? 'bg-transparent' : 'bg-primary')}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[13px] font-semibold leading-[18px]">{item.title}</span>
                      <span className="block text-[13px] leading-[18px] text-text-2">{item.body}</span>
                      <span className="mt-1 block text-[11px] text-text-3">{formatRelative(item.created_at)}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}
