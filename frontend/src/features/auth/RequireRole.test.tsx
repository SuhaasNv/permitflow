import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import * as authApi from '@/api/auth'
import { AuthProvider } from './AuthContext'
import { RequireRole } from './RequireRole'

function seedSession(role: authApi.Role) {
  sessionStorage.setItem(
    'permitflow.session',
    JSON.stringify({ token: 't', expiresAt: new Date(Date.now() + 60_000).toISOString(), user: { id: '1', email: 'a@b.sg', full_name: 'A B', role } }),
  )
}

describe('RequireRole', () => {
  beforeEach(() => sessionStorage.clear())

  it('redirects anonymous users to login', async () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/officer/queue']}>
          <Routes>
            <Route path="/login" element={<div>Login</div>} />
            <Route element={<RequireRole roles={['officer']} />}>
              <Route path="/officer/queue" element={<div>Queue</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    )
    expect(await screen.findByText('Login')).toBeInTheDocument()
  })

  it('shows "Not available for your role" for the wrong role', async () => {
    seedSession('operator')
    vi.spyOn(authApi, 'me').mockResolvedValue({ id: '1', email: 'a@b.sg', full_name: 'A B', role: 'operator' })
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/officer/queue']}>
          <Routes>
            <Route element={<RequireRole roles={['officer']} />}>
              <Route path="/officer/queue" element={<div>Queue</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthProvider>,
    )
    expect(await screen.findByText('Not available for your role')).toBeInTheDocument()
  })
})
