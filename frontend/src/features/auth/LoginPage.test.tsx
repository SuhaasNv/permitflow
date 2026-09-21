import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import * as authApi from '@/api/auth'
import { AppError } from '@/api/client'
import { AppProviders } from '@/app/providers'
import * as auth from './AuthContext'
import { AuthProvider } from './AuthContext'
import { LoginPage } from './LoginPage'

function renderLogin(from?: string) {
  return render(
    <AppProviders>
      <AuthProvider>
        <MemoryRouter initialEntries={[from ? { pathname: '/login', state: { from } } : '/login']}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/officer/queue" element={<div>Officer home</div>} />
            <Route path="/officer/applications/:id" element={<div>Officer case</div>} />
            <Route path="/app/dashboard" element={<div>Operator home</div>} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </AppProviders>,
  )
}

/** The auth state of a signed-out browser whose last session the server ended (US-093). */
function signedOutState(ended: Pick<auth.AuthState, 'endedReason' | 'endedAt' | 'endedMessage'>): auth.AuthState {
  return { user: null, token: null, expiresAt: null, ready: true, signIn: vi.fn(), signOut: vi.fn(), ...ended }
}

describe('LoginPage', () => {
  beforeEach(() => sessionStorage.clear())
  afterEach(() => vi.restoreAllMocks())

  it('validates inline before calling the API', async () => {
    const spy = vi.spyOn(authApi, 'login')
    renderLogin()
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findAllByRole('alert')).toHaveLength(2)
    expect(spy).not.toHaveBeenCalled()
  })

  it('routes an officer to the review queue after sign-in', async () => {
    vi.spyOn(authApi, 'login').mockResolvedValue({
      access_token: 't',
      token_type: 'bearer',
      expires_at: new Date(Date.now() + 60_000).toISOString(),
      user: {
        id: '1',
        email: 'o@x.sg',
        full_name: 'Rahim bin Abdullah',
        role: 'officer',
      },
    })
    renderLogin()
    await userEvent.type(screen.getByLabelText(/Email address/), 'o@x.sg')
    await userEvent.type(screen.getByLabelText(/Password/), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(screen.getByText('Officer home')).toBeInTheDocument())
  })

  it('returns to the page the session ended on when it is inside the role\'s area, else home', async () => {
    const officer = {
      access_token: 't',
      token_type: 'bearer' as const,
      expires_at: new Date(Date.now() + 60_000).toISOString(),
      user: { id: '1', email: 'o@x.sg', full_name: 'Rahim bin Abdullah', role: 'officer' as const },
    }
    vi.spyOn(authApi, 'login').mockResolvedValue(officer)
    const { unmount } = renderLogin('/officer/applications/x')
    await userEvent.type(screen.getByLabelText(/Email address/), 'o@x.sg')
    await userEvent.type(screen.getByLabelText(/Password/), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(screen.getByText('Officer case')).toBeInTheDocument())
    unmount()
    sessionStorage.clear()
    // a path from another role's area never carries over
    renderLogin('/app/applications/x')
    await userEvent.type(screen.getByLabelText(/Email address/), 'o@x.sg')
    await userEvent.type(screen.getByLabelText(/Password/), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await waitFor(() => expect(screen.getByText('Officer home')).toBeInTheDocument())
  })

  it('a stored session that ran out while the tab was closed is explained on the sign-in page', () => {
    sessionStorage.setItem(
      'permitflow.session',
      JSON.stringify({
        token: 't',
        expiresAt: new Date(Date.now() - 1000).toISOString(),
        user: { id: '1', email: 'o@x.sg', full_name: 'Rahim bin Abdullah', role: 'officer' },
      }),
    )
    renderLogin()
    expect(screen.getByText(/Your session (ended|expired)/)).toBeInTheDocument()
  })

  it('shows the generic message on 401', async () => {
    vi.spyOn(authApi, 'login').mockRejectedValue(
      new AppError(401, {
        code: 'unauthorized',
        message: 'Email or password is incorrect.',
      }),
    )
    renderLogin()
    await userEvent.type(screen.getByLabelText(/Email address/), 'o@x.sg')
    await userEvent.type(screen.getByLabelText(/Password/), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Email or password is incorrect.')).toBeInTheDocument()
  })

  it('offers to sign out the other device on 409 and signs in with take-over (US-093)', async () => {
    const officer = { id: 'u2', email: 'officer@permitflow.example.sg', full_name: 'Rahim bin Abdullah', role: 'officer' as const }
    const login = vi
      .spyOn(authApi, 'login')
      .mockRejectedValueOnce(
        new AppError(409, {
          code: 'session_active',
          message: 'This account is signed in on Safari on iPad.',
          details: { device: 'Safari on iPad', last_seen_at: '2026-09-21T02:05:00+00:00' },
        }),
      )
      .mockResolvedValueOnce({
        access_token: 'tok',
        token_type: 'bearer',
        expires_at: new Date(Date.now() + 3600_000).toISOString(),
        user: officer,
      })
    renderLogin()
    await userEvent.type(screen.getByLabelText(/Email address/), 'officer@permitflow.example.sg')
    await userEvent.type(screen.getByLabelText(/Password/), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    // The other device is named with its last activity in Singapore time; the password stays in the form.
    expect(await screen.findByText(/signed in on Safari on iPad, last active 21 Sep, 10:05/)).toBeInTheDocument()
    expect(screen.getByText(/anything typed in the last second or so may be lost/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Password/)).toHaveValue('pw')
    expect(login).toHaveBeenLastCalledWith('officer@permitflow.example.sg', 'pw', false)

    await userEvent.click(screen.getByRole('button', { name: 'Sign out the other device and continue' }))
    expect(login).toHaveBeenLastCalledWith('officer@permitflow.example.sg', 'pw', true)
    expect(await screen.findByText('Officer home')).toBeInTheDocument()
  })

  it('lets the person cancel a take-over and keeps the form', async () => {
    vi.spyOn(authApi, 'login').mockRejectedValue(
      new AppError(409, { code: 'session_active', message: 'Signed in elsewhere.', details: { device: 'Chrome on Mac' } }),
    )
    renderLogin()
    await userEvent.type(screen.getByLabelText(/Email address/), 'o@x.sg')
    await userEvent.type(screen.getByLabelText(/Password/), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    await screen.findByText(/signed in on Chrome on Mac/)
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.queryByText(/signed in on Chrome on Mac/)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/Email address/)).toHaveValue('o@x.sg')
  })

  it('explains a session that ended on another device, with the time (US-093)', () => {
    vi.spyOn(auth, 'useAuth').mockReturnValue(
      signedOutState({ endedReason: 'taken_over', endedAt: '2026-09-21T02:05:00+00:00', endedMessage: null }),
    )
    renderLogin()
    expect(screen.getByText('Your session ended: this account signed in on another device at 21 Sep, 10:05. Sign in again to continue where you left off.')).toBeInTheDocument()
  })

  it("explains an idle session in the server's words", () => {
    vi.spyOn(auth, 'useAuth').mockReturnValue(
      signedOutState({
        endedReason: 'idle',
        endedAt: '2026-09-21T02:05:00+00:00',
        endedMessage: 'Your session ended after 60 minutes without activity. Sign in again to continue.',
      }),
    )
    renderLogin()
    expect(screen.getByText('Your session ended after 60 minutes without activity. Sign in again to continue.')).toBeInTheDocument()
  })

  it('shows and hides the password without submitting (US-046)', async () => {
    const login = vi.spyOn(authApi, 'login')
    renderLogin()
    const password = screen.getByLabelText(/^Password/)
    expect(password).toHaveAttribute('type', 'password')
    await userEvent.type(password, 'secret')
    await userEvent.click(screen.getByRole('button', { name: 'Show password' }))
    expect(password).toHaveAttribute('type', 'text')
    await userEvent.click(screen.getByRole('button', { name: 'Hide password' }))
    expect(password).toHaveAttribute('type', 'password')
    expect(login).not.toHaveBeenCalled()
  })
})
