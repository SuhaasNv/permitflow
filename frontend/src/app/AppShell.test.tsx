import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as notificationsApi from '@/api/notifications'
import { AppProviders } from '@/app/providers'
import * as auth from '@/features/auth/AuthContext'
import { setUnsaved } from '@/lib/unsaved'
import { AppShell } from './AppShell'

type AuthState = ReturnType<typeof auth.useAuth>

function authState(role: 'operator' | 'officer', expiresInMs: number, signOut = vi.fn()): AuthState {
  return {
    user: {
      id: 'u1',
      email: `${role}@permitflow.example.sg`,
      full_name: role === 'operator' ? 'Tan Wei Ling' : 'Rahim bin Abdullah',
      role,
    },
    token: 'tok',
    expiresAt: new Date(Date.now() + expiresInMs).toISOString(),
    ready: true,
    endedReason: null,
    endedAt: null,
    endedMessage: null,
    signIn: vi.fn(),
    signOut,
  }
}

function renderShell(state: AuthState, path = '/app/dashboard') {
  vi.spyOn(auth, 'useAuth').mockReturnValue(state)
  const router = createMemoryRouter(
    [
      {
        element: <AppShell />,
        children: [
          { path: '/app/dashboard', element: <div>DASHBOARD</div> },
          { path: '/officer/queue', element: <div>QUEUE</div> },
        ],
      },
      { path: '/login', element: <div>LOGIN</div> },
    ],
    { initialEntries: [path] },
  )
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  )
  return router
}

describe('AppShell', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    setUnsaved(false)
    vi.spyOn(notificationsApi, 'getNotifications').mockResolvedValue({ items: [], unread_count: 0 })
  })

  it('shows the rail for the signed-in role only', async () => {
    renderShell(authState('operator', 8 * 60 * 60 * 1000))
    expect(await screen.findByText('DASHBOARD')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /My applications/ }).length).toBeGreaterThan(0)
    expect(screen.queryByRole('link', { name: /Review queue/ })).not.toBeInTheDocument()
    expect(screen.getAllByText('Operator').length).toBeGreaterThan(0)
  })

  it('stays silent about the session until 30 minutes remain, then counts down (US-048)', async () => {
    renderShell(authState('officer', 2 * 60 * 60 * 1000), '/officer/queue')
    expect(await screen.findByText('QUEUE')).toBeInTheDocument()
    expect(screen.queryByText(/Session ends/)).not.toBeInTheDocument()
  })

  it('warns inside the last 30 minutes and marks the last 5 as urgent', async () => {
    renderShell(authState('officer', 12 * 60 * 1000), '/officer/queue')
    expect(await screen.findByText(/Session ends in 12 min/)).toBeInTheDocument()
    expect(screen.getByText(/Session ends in 12 min/)).not.toHaveClass('font-semibold')
  })

  it('urgent copy inside five minutes', async () => {
    renderShell(authState('officer', 3 * 60 * 1000), '/officer/queue')
    const status = await screen.findByText(/Session ends in 3 min/)
    expect(status).toHaveClass('font-semibold')
  })

  it('signs out directly when nothing is unsaved, and asks first when a section is dirty', async () => {
    const signOut = vi.fn()
    const router = renderShell(authState('operator', 60 * 60 * 1000, signOut))
    await screen.findByText('DASHBOARD')
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(signOut).toHaveBeenCalledTimes(1)
    expect(router.state.location.pathname).toBe('/login')
  })

  it('asks before signing out with unsaved changes', async () => {
    const signOut = vi.fn()
    renderShell(authState('operator', 60 * 60 * 1000, signOut))
    await screen.findByText('DASHBOARD')
    setUnsaved(true)
    await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(signOut).not.toHaveBeenCalled()
    expect(await screen.findByRole('dialog', { name: 'Sign out without saving?' })).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: 'Sign out' }).at(-1)!)
    expect(signOut).toHaveBeenCalledTimes(1)
  })
})
