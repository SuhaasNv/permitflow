import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '@/api/auth'
import * as notificationsApi from '@/api/notifications'
import * as officerApi from '@/api/officer'
import App from '@/App'
import { router } from '@/app/router'

const STORAGE_KEY = 'permitflow.session'
const inAnHour = () => new Date(Date.now() + 60 * 60 * 1000).toISOString()

function signedInAs(role: 'operator' | 'officer' | 'admin') {
  const user = { id: 'u1', email: `${role}@permitflow.example.sg`, full_name: 'Someone', role }
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: 'tok', user, expiresAt: inAnHour() }))
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
}

/** Smoke test of the route table and role guards (ADR-005): each area belongs to one role. */
describe('App routing', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    sessionStorage.clear()
    vi.spyOn(notificationsApi, 'getNotifications').mockResolvedValue({ items: [], unread_count: 0 })
  })

  it('serves the landing page publicly and sends anonymous users of the workspace to sign in', async () => {
    await router.navigate('/')
    render(<App />)
    expect(await screen.findByRole('heading', { level: 1 })).toBeInTheDocument()
    await router.navigate('/app/dashboard')
    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('keeps an operator out of the officer area and an officer out of the operator area', async () => {
    signedInAs('operator')
    await router.navigate('/officer/queue')
    const first = render(<App />)
    expect(await screen.findByText('Not available for your role')).toBeInTheDocument()
    first.unmount()

    sessionStorage.clear()
    signedInAs('officer')
    await router.navigate('/app/dashboard')
    render(<App />)
    expect(await screen.findByText('Not available for your role')).toBeInTheDocument()
  })

  it('answers an unknown path with a Not found page: an h1, its own title and a way home', async () => {
    await router.navigate('/definitely/not/here')
    render(<App />)
    expect(await screen.findByRole('heading', { level: 1, name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to PermitFlow' })).toHaveAttribute('href', '/')
    expect(screen.getByRole('main')).toBeInTheDocument()
    await waitFor(() => expect(document.title).toBe('Page not found | PermitFlow'))
  })

  it('gives every public route its own tab title', async () => {
    const expected: [string, string][] = [
      ['/', 'PermitFlow | Food Establishment Licence'],
      ['/login', 'Sign in | PermitFlow'],
      ['/privacy', 'Privacy policy | PermitFlow'],
      ['/terms', 'Terms | PermitFlow'],
      ['/cookies', 'Cookies | PermitFlow'],
      ['/releases', "What's new | PermitFlow"],
    ]
    render(<App />)
    for (const [path, title] of expected) {
      await router.navigate(path)
      await waitFor(() => expect(document.title).toBe(title))
    }
  })

  it('titles a signed-in screen after the screen', async () => {
    signedInAs('officer')
    vi.spyOn(officerApi, 'getQueue').mockResolvedValue({ items: [], officer_turn_count: 0, waiting_on_operator_count: 0, decided_count: 0 })
    await router.navigate('/officer/queue')
    render(<App />)
    await waitFor(() => expect(document.title).toBe('Review queue | PermitFlow'))
  })
})
