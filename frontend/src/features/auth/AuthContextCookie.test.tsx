import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { login } from '@/api/auth'
import { API_URL, request, setCsrfToken, setTokenProvider } from '@/api/client'
import { AppProviders } from '@/app/providers'
import { AuthProvider, useAuth } from './AuthContext'

// Cookie mode (US-104): the provider holds no credential. The session lives in an HttpOnly cookie, the page keeps
// only a CSRF value in memory, and a reload restores through GET /auth/me.

const user = { id: 'u1', email: 'operator@permitflow.example.sg', full_name: 'Tan Wei Ling', role: 'operator' as const }
const json = (status: number, body?: unknown) => new Response(body === undefined ? null : JSON.stringify(body), { status })

function Probe() {
  const { user, token, ready, endedReason, signIn, signOut } = useAuth()
  return (
    <div>
      <div data-testid="ready">{String(ready)}</div>
      <div data-testid="user">{user?.email ?? 'none'}</div>
      <div data-testid="token">{token ?? 'none'}</div>
      <div data-testid="ended">{endedReason ?? 'none'}</div>
      <button onClick={() => void login('a@b.sg', 'pw').then(signIn)}>sign in</button>
      <button onClick={() => void signOut()}>sign out</button>
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

describe('AuthProvider in cookie mode', () => {
  const fetchMock = vi.fn<typeof fetch>()
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    sessionStorage.clear()
    localStorage.clear()
    setCsrfToken(null)
    setTokenProvider(() => null)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    fetchMock.mockReset()
  })
  const call = (n: number) => ({ url: fetchMock.mock.calls[n][0], init: fetchMock.mock.calls[n][1]! })

  it('restores a cookie session on load through /auth/me, with nothing stored', async () => {
    fetchMock.mockImplementation(async () => json(200, { ...user, csrf_token: 'csrf-1' }))
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent(user.email))
    expect(screen.getByTestId('ready')).toHaveTextContent('true')
    expect(screen.getByTestId('token')).toHaveTextContent('none')
    expect(call(0).url).toBe(`${API_URL}/auth/me`)
    expect(call(0).init.credentials).toBe('include')
    expect(sessionStorage.length).toBe(0)
    expect(localStorage.length).toBe(0)

    // The restored CSRF value is used on the next write.
    await request('/applications', { method: 'POST', body: {} })
    const last = fetchMock.mock.calls[fetchMock.mock.calls.length - 1][1]!
    expect((last.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf-1')
  })

  it('ends on the sign-in page state when /auth/me answers 401', async () => {
    fetchMock.mockImplementation(async () => json(401, { error: { code: 'unauthorized', message: 'Sign in.' } }))
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('signs in without a token, stores nothing, and signs out with the CSRF header', async () => {
    fetchMock.mockImplementationOnce(async () => json(401, { error: { code: 'unauthorized', message: 'Sign in.' } }))
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))

    fetchMock.mockImplementationOnce(async () =>
      json(200, { expires_at: new Date(Date.now() + 3_600_000).toISOString(), user, csrf_token: 'csrf-1' }),
    )
    await userEvent.click(screen.getByText('sign in'))
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent(user.email))
    expect(screen.getByTestId('token')).toHaveTextContent('none')
    expect(sessionStorage.length).toBe(0)
    expect(localStorage.length).toBe(0)

    fetchMock.mockImplementation(async () => json(204))
    await userEvent.click(screen.getByText('sign out'))
    const logoutCall = fetchMock.mock.calls.find(([url]) => url === `${API_URL}/auth/logout`)!
    expect(logoutCall[1]!.method).toBe('POST')
    expect((logoutCall[1]!.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf-1')
    expect(logoutCall[1]!.credentials).toBe('include')
    expect(screen.getByTestId('user')).toHaveTextContent('none')

    // In-memory state is gone: the next write carries no CSRF header.
    await request('/x', { method: 'POST' })
    const last = fetchMock.mock.calls[fetchMock.mock.calls.length - 1][1]!
    expect((last.headers as Record<string, string>)['X-CSRF-Token']).toBeUndefined()
  })

  const signedInBody = () =>
    json(200, { expires_at: new Date(Date.now() + 3_600_000).toISOString(), user, csrf_token: 'csrf-1' })
  const unauthorized = () => json(401, { error: { code: 'unauthorized', message: 'Sign in.' } })

  async function signInThroughTheForm() {
    fetchMock.mockImplementationOnce(async () => unauthorized())
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    fetchMock.mockImplementationOnce(async () => signedInBody())
    await userEvent.click(screen.getByText('sign in'))
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent(user.email))
  }

  it('stays signed in with an error when the sign-out does not reach the server (offline)', async () => {
    await signInThroughTheForm()
    fetchMock.mockImplementation(async () => {
      throw new TypeError('Failed to fetch')
    })
    await userEvent.click(screen.getByText('sign out'))
    expect(await screen.findByText('Sign-out did not reach the server. Try again.')).toBeInTheDocument()
    expect(screen.getByTestId('user')).toHaveTextContent(user.email)

    // Still a live cookie session: the CSRF value was kept, and the next try goes through.
    fetchMock.mockImplementation(async () => json(204))
    await userEvent.click(screen.getByText('sign out'))
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('none'))
    const lastLogout = [...fetchMock.mock.calls].reverse().find(([url]) => url === `${API_URL}/auth/logout`)!
    expect((lastLogout[1]!.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf-1')
  })

  it('stays signed in with an error when the sign-out is refused (403 csrf_failed twice)', async () => {
    await signInThroughTheForm()
    fetchMock.mockImplementation(async (url) =>
      url === `${API_URL}/auth/me`
        ? json(200, { ...user, csrf_token: 'csrf-2' })
        : json(403, { error: { code: 'csrf_failed', message: 'Reload.' } }),
    )
    await userEvent.click(screen.getByText('sign out'))
    expect(await screen.findByText('Sign-out did not reach the server. Try again.')).toBeInTheDocument()
    expect(screen.getByTestId('user')).toHaveTextContent(user.email)
  })

  it('a slow cold /auth/me that answers 401 does not undo a sign-in made meanwhile', async () => {
    let answerMe: (r: Response) => void = () => undefined
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => (answerMe = resolve)))
    renderAuth()
    fetchMock.mockImplementationOnce(async () => signedInBody())
    await userEvent.click(screen.getByText('sign in'))
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent(user.email))
    answerMe(unauthorized())
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    expect(screen.getByTestId('user')).toHaveTextContent(user.email)
    expect(screen.getByTestId('ended')).toHaveTextContent('none')
    // The write still carries the CSRF value of the sign-in.
    fetchMock.mockImplementation(async () => json(200, {}))
    await request('/x', { method: 'POST' })
    const last = fetchMock.mock.calls[fetchMock.mock.calls.length - 1][1]!
    expect((last.headers as Record<string, string>)['X-CSRF-Token']).toBe('csrf-1')
  })

  it('a slow cold /auth/me that answers 200 does not replace the sign-in made meanwhile', async () => {
    let answerMe: (r: Response) => void = () => undefined
    fetchMock.mockImplementationOnce(() => new Promise<Response>((resolve) => (answerMe = resolve)))
    renderAuth()
    fetchMock.mockImplementationOnce(async () => signedInBody())
    await userEvent.click(screen.getByText('sign in'))
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent(user.email))
    answerMe(json(200, { ...user, id: 'u9', email: 'someone.else@permitflow.example.sg', csrf_token: 'csrf-9' }))
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    expect(screen.getByTestId('user')).toHaveTextContent(user.email)
  })

  it('restores the expiry timer from /auth/me: an already-ended cookie session shows "expired"', async () => {
    fetchMock.mockImplementation(async () =>
      json(200, { ...user, csrf_token: 'csrf-1', expires_at: new Date(Date.now() - 1000).toISOString() }),
    )
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('ended')).toHaveTextContent('expired'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('token mode cold load: one /auth/me 401, no ended reason, no error, nothing stored', async () => {
    fetchMock.mockImplementation(async () => unauthorized())
    renderAuth()
    await waitFor(() => expect(screen.getByTestId('ready')).toHaveTextContent('true'))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(call(0).url).toBe(`${API_URL}/auth/me`)
    expect(screen.getByTestId('user')).toHaveTextContent('none')
    expect(screen.getByTestId('ended')).toHaveTextContent('none')
    expect(sessionStorage.length).toBe(0)
  })
})
