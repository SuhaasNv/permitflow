import { QueryClient, useQuery, useQueryClient } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '@/api/auth'
import type { TokenResponse } from '@/api/auth'
import { AppError, notifyUnauthorized } from '@/api/client'
import { AppProviders } from '@/app/providers'
import { AuthProvider, useAuth } from './AuthContext'

const STORAGE_KEY = 'permitflow.session'
const user = { id: 'u1', email: 'operator@permitflow.example.sg', full_name: 'Tan Wei Ling', role: 'operator' as const }
const inAnHour = () => new Date(Date.now() + 60 * 60 * 1000).toISOString()
const token = (expires_at = inAnHour()): TokenResponse => ({ access_token: 'tok', token_type: 'bearer', expires_at, user })

/** A consumer that shows the auth state and holds one cached query so cache clearing is observable. */
function Probe() {
  const { user, ready, endedReason, signIn, signOut } = useAuth()
  const client = useQueryClient()
  const q = useQuery({ queryKey: ['probe'], queryFn: async () => 'cached', staleTime: Infinity })
  return (
    <div>
      <div data-testid="ready">{String(ready)}</div>
      <div data-testid="user">{user?.email ?? 'none'}</div>
      <div data-testid="ended">{endedReason ?? 'none'}</div>
      <div data-testid="cache">{String(client.getQueryData(['probe']) ?? q.data ?? 'empty')}</div>
      <button onClick={() => signIn(token())}>sign in</button>
      <button onClick={() => signOut()}>sign out</button>
    </div>
  )
}

function renderAuth() {
  return render(
    <AppProviders>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </AppProviders>,
  )
}

describe('AuthProvider (UC0-A session handling)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
    sessionStorage.clear()
  })

  it('signs in, mirrors the session to sessionStorage, and clears the cache on sign out', async () => {
    const clear = vi.spyOn(QueryClient.prototype, 'clear')
    renderAuth()
    expect(await screen.findByTestId('ready')).toHaveTextContent('true')
    await userEvent.click(screen.getByText('sign in'))
    expect(screen.getByTestId('user')).toHaveTextContent(user.email)
    expect(JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? '{}')).toMatchObject({ token: 'tok', user: { email: user.email } })
    await waitFor(() => expect(screen.getByTestId('cache')).toHaveTextContent('cached'))

    await userEvent.click(screen.getByText('sign out'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
    // The previous account's cached data must not survive for the next person on this browser.
    expect(clear).toHaveBeenCalled()
  })

  it('restores a stored session and re-validates it against the server', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: 'tok', user, expiresAt: inAnHour() }))
    const me = vi.spyOn(authApi, 'me').mockResolvedValue({ ...user, full_name: 'Renamed' })
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    expect(me).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('user')).toHaveTextContent(user.email)
  })

  it('drops a stored session the server rejects, but keeps it through a network blip', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: 'tok', user, expiresAt: inAnHour() }))
    vi.spyOn(authApi, 'me').mockRejectedValueOnce(new AppError(0, { code: 'network_error', message: 'offline' }))
    const first = renderAuth()
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    expect(screen.getByTestId('user')).toHaveTextContent(user.email)
    first.unmount()

    vi.spyOn(authApi, 'me').mockRejectedValueOnce(new AppError(401, { code: 'unauthorized', message: 'Deactivated.' }))
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('none'))
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull()
  })

  it('ignores an expired stored session', async () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: 'tok', user, expiresAt: new Date(Date.now() - 1000).toISOString() }))
    const me = vi.spyOn(authApi, 'me')
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
    expect(me).not.toHaveBeenCalled()
  })

  it('ends the session with a reason on a 401 from any request', async () => {
    renderAuth()
    await screen.findByTestId('ready')
    await userEvent.click(screen.getByText('sign in'))
    act(() => notifyUnauthorized())
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('none'))
    expect(screen.getByTestId('ended')).toHaveTextContent('unauthorized')
  })

  it('signs out by itself when the token expires', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.spyOn(authApi, 'me').mockResolvedValue(user)
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ token: 'tok', user, expiresAt: new Date(Date.now() + 1500).toISOString() }))
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent(user.email))
    await act(async () => {
      vi.advanceTimersByTime(2000)
    })
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('none'))
    expect(screen.getByTestId('ended')).toHaveTextContent('expired')
    vi.useRealTimers()
  })
})
