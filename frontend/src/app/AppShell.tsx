import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'

import type { Role } from '@/api/auth'
import { useAuth } from '@/features/auth/AuthContext'
import { Logo } from '@/features/shared/Logo'
import { cn } from '@/lib/cn'

interface NavItem {
  label: string
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
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d={d} />
  </svg>
)

const NAV: Record<Role, NavItem[]> = {
  operator: [
    {
      label: 'Dashboard',
      to: '/app/dashboard',
      icon: icon('m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10'),
    },
    {
      label: 'My applications',
      to: '/app/applications',
      icon: icon('M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z'),
    },
  ],
  officer: [
    {
      label: 'Review queue',
      to: '/officer/queue',
      icon: icon(
        'M22 12h-6l-2 3h-4l-2-3H2M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z',
      ),
    },
  ],
  admin: [
    {
      label: 'Overview',
      to: '/admin/overview',
      icon: icon('M22 12h-4l-3 9L9 3l-3 9H2'),
    },
  ],
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

/** Masthead, top bar with hamburger, collapsible side rail (64 px) and content. */
export function AppShell() {
  const { user, expiresAt, signOut } = useAuth()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(NAV_KEY) === '1'
    } catch {
      return false
    }
  })
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    try {
      localStorage.setItem(NAV_KEY, collapsed ? '1' : '0')
    } catch {
      // ignore
    }
  }, [collapsed])

  if (!user) return null
  const items = NAV[user.role]

  const nav = (
    <nav
      aria-label="Main"
      className={cn('flex flex-col gap-0.5 border-r border-line bg-surface p-3', collapsed ? 'w-16 items-center px-2' : 'w-[232px]')}
    >
      {!collapsed ? (
        <div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-text-3">{ROLE_LABEL[user.role]}</div>
      ) : null}
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          title={item.label}
          onClick={() => setMobileOpen(false)}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2.5 rounded-md text-sm font-medium text-text-2 no-underline transition-colors hover:bg-neutral-soft hover:text-text',
              collapsed ? 'h-11 w-11 justify-center' : 'px-3 py-[9px]',
              isActive && 'bg-neutral-soft font-semibold text-text shadow-[inset_3px_0_0_var(--color-primary)]',
            )
          }
        >
          {item.icon}
          {!collapsed ? <span>{item.label}</span> : null}
        </NavLink>
      ))}
      {!collapsed ? <div className="mt-auto border-t border-line p-3 text-xs leading-[18px] text-text-3">© 2026 PermitFlow</div> : null}
    </nav>
  )

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <div className="flex h-7 items-center gap-2 bg-text px-4 text-xs text-[#c5cbd3] sm:px-6">
        <span className="font-semibold text-white">Secure licensing portal</span>
        <span className="hidden sm:inline">· Food Establishments Unit</span>
        {expiresAt ? (
          <span className="ml-auto hidden sm:inline" title={new Date(expiresAt).toLocaleString()}>
            Session expires {formatExpiry(expiresAt)}
          </span>
        ) : null}
      </div>
      <header className="flex h-14 items-center gap-3 border-b border-line bg-surface px-3 sm:gap-4 sm:px-6">
        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-md text-text-2 hover:bg-neutral-soft"
          aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
          aria-expanded={!collapsed}
          onClick={() => {
            if (window.matchMedia('(max-width: 767px)').matches) setMobileOpen((v) => !v)
            else setCollapsed((v) => !v)
          }}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        <Logo />
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-2.5 rounded-md px-1 py-1">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#e4e7ec] text-xs font-semibold text-text-2">
              {initials(user.full_name)}
            </span>
            <div className="hidden sm:block">
              <div className="text-[13px] font-semibold leading-4">{user.full_name}</div>
              <div className="text-xs text-text-3">{ROLE_LABEL[user.role]}</div>
            </div>
          </div>
          <button
            type="button"
            className="h-8 rounded-md px-3 text-[13px] font-semibold text-text-2 hover:bg-neutral-soft hover:text-text"
            onClick={() => {
              signOut()
              navigate('/login', { replace: true })
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="flex flex-1">
        <div className="hidden md:flex">{nav}</div>
        {mobileOpen ? (
          <div className="fixed inset-0 z-20 flex md:hidden" role="dialog" aria-label="Navigation">
            <div className="flex w-[260px] bg-surface">{nav}</div>
            <button type="button" className="flex-1 bg-black/40" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />
          </div>
        ) : null}
        <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 sm:pb-10">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
