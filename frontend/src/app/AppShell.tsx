import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, ScrollRestoration, useLocation, useNavigate } from 'react-router-dom'

import type { Role } from '@/api/auth'
import { useAuth } from '@/features/auth/AuthContext'
import { Dialog } from '@/features/shared/Dialog'
import { Logo } from '@/features/shared/Logo'
import { NotificationsBell } from '@/features/shared/NotificationsBell'
import { hasUnsaved, setUnsaved } from '@/lib/unsaved'
import { cn } from '@/lib/cn'

interface NavItem {
  label: string
  short: string
  to: string
  icon: ReactNode
}

const icon = (d: string) => (
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
    <path d={d} />
  </svg>
)

const NAV: Record<Role, NavItem[]> = {
  operator: [
    { label: 'Dashboard', short: 'Home', to: '/app/dashboard', icon: icon('m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10') },
    {
      label: 'My applications',
      short: 'Applications',
      to: '/app/applications',
      icon: icon('M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'),
    },
  ],
  officer: [
    {
      label: 'Review queue',
      short: 'Queue',
      to: '/officer/queue',
      icon: icon(
        'M22 12h-6l-2 3h-4l-2-3H2M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z',
      ),
    },
  ],
  admin: [{ label: 'Overview', short: 'Overview', to: '/admin/overview', icon: icon('M22 12h-4l-3 9L9 3l-3 9H2') }],
}

const ROLE_LABEL: Record<Role, string> = {
  operator: 'Operator',
  officer: 'Licensing officer',
  admin: 'Administration',
}

const NAV_KEY = 'permitflow.nav.collapsed'

function formatExpiry(iso: string): string {
  const d = new Date(iso)
  const sameDay = d.toDateString() === new Date().toDateString()
  const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  return sameDay ? `at ${time}` : `tomorrow at ${time}`
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('')
}

/** Masthead, top bar, collapsible side rail (232 → 64 px) on desktop, bottom tab bar on phones, route-keyed content transition. */
export function AppShell() {
  const { user, expiresAt, signOut } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(NAV_KEY) === '1'
    } catch {
      return false
    }
  })

  const [confirmSignOut, setConfirmSignOut] = useState(false)
  const doSignOut = () => {
    setUnsaved(false)
    signOut()
    navigate('/login', { replace: true })
  }

  useEffect(() => {
    try {
      localStorage.setItem(NAV_KEY, collapsed ? '1' : '0')
    } catch {
      // ignore
    }
  }, [collapsed])

  if (!user) return null
  const items = NAV[user.role]
  // Section-level key: form sub-steps keep their own in-page transitions.
  const pageKey = location.pathname.split('/').slice(0, 4).join('/')

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <div className="flex h-7 items-center gap-2 bg-ink px-4 text-xs text-[#aeb6c2] sm:px-6">
        <span className="font-semibold text-white">Secure licensing portal</span>
        <span className="hidden sm:inline">· Food Establishments Unit</span>
        {expiresAt ? (
          <span className="ml-auto tabular-nums" title={new Date(expiresAt).toLocaleString()}>
            Session expires {formatExpiry(expiresAt)}
          </span>
        ) : null}
      </div>
      <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface/95 px-3 backdrop-blur sm:gap-4 sm:px-6">
        <button
          type="button"
          className="hidden h-10 w-10 items-center justify-center rounded-md text-text-2 transition-colors hover:bg-neutral-soft hover:text-text md:flex"
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((v) => !v)}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        <Logo />
        <div className="ml-auto flex items-center gap-1">
          <NotificationsBell role={user.role} />
          <div className="flex items-center gap-2.5 px-1 py-1">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-[11px] font-semibold tracking-wide text-white">
              {initials(user.full_name)}
            </span>
            <div className="hidden sm:block">
              <div className="text-[13px] font-semibold leading-4">{user.full_name}</div>
              <div className="text-xs leading-4 text-text-3">{ROLE_LABEL[user.role]}</div>
            </div>
          </div>
          <button
            type="button"
            className="h-8 rounded-md px-3 text-[13px] font-semibold text-text-2 transition-colors hover:bg-neutral-soft hover:text-text"
            onClick={() => {
              if (hasUnsaved()) setConfirmSignOut(true)
              else doSignOut()
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav
          aria-label="Main"
          className={cn(
            'hidden shrink-0 flex-col border-r border-line bg-surface md:flex',
            'transition-[width] duration-[var(--dur-base)] ease-[var(--ease-out)]',
            collapsed ? 'w-16' : 'w-[232px]',
          )}
        >
          <div className="sticky top-14 flex flex-col gap-0.5 p-3">
            <div
              className={cn(
                'pf-eyebrow overflow-hidden whitespace-nowrap px-[11px] transition-[opacity,height,padding] duration-[var(--dur-fast)]',
                collapsed ? 'h-0 py-0 opacity-0' : 'h-9 pb-3 pt-2 opacity-100',
              )}
              aria-hidden={collapsed}
            >
              {ROLE_LABEL[user.role]}
            </div>
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                title={collapsed ? item.label : undefined}
                className={({ isActive }) =>
                  cn(
                    'flex h-10 items-center gap-3 overflow-hidden rounded-md px-[11px] text-sm font-medium text-text-2 no-underline',
                    'transition-[background-color,color] duration-[var(--dur-fast)] ease-[var(--ease-out)] hover:bg-neutral-soft hover:text-text',
                    isActive && 'bg-surface-3 font-semibold text-text',
                  )
                }
              >
                <span className="flex h-[18px] w-[18px] shrink-0 items-center justify-center">{item.icon}</span>
                <span
                  className={cn('truncate transition-opacity duration-[var(--dur-fast)]', collapsed ? 'opacity-0' : 'opacity-100 delay-75')}
                >
                  {item.label}
                </span>
              </NavLink>
            ))}
          </div>
          <div
            className={cn('sticky bottom-0 mt-auto border-t border-line bg-surface p-4 text-xs leading-[18px] text-text-3', collapsed && 'hidden')}
          >
            <div className="font-medium text-text-2">PermitFlow</div>
            <div>Fictional assessment product</div>
          </div>
        </nav>
        <main className="min-w-0 flex-1 pb-24 md:pb-0">
          <div key={pageKey} className="pf-enter mx-auto w-full max-w-[1360px] px-4 py-6 sm:px-8 sm:py-8 lg:px-10">
            <Outlet />
          </div>
          {/* New pages open at the top; Back and Forward return to the remembered position. */}
          <ScrollRestoration />
        </main>
      </div>
      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 flex border-t border-line bg-surface/95 backdrop-blur md:hidden">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex h-16 flex-1 flex-col items-center justify-center gap-1 text-[11px] font-medium text-text-3 no-underline transition-colors',
                isActive && 'text-text',
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn('flex h-7 w-12 items-center justify-center rounded-full transition-colors', isActive && 'bg-surface-3')}
                >
                  {item.icon}
                </span>
                {item.short}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <Dialog
        open={confirmSignOut}
        title="Sign out without saving?"
        confirmLabel="Sign out"
        cancelLabel="Stay"
        danger
        onConfirm={doSignOut}
        onCancel={() => setConfirmSignOut(false)}
      >
        <p>You have unsaved changes in the section you are editing. Sign out now and they will be lost.</p>
      </Dialog>
    </div>
  )
}
