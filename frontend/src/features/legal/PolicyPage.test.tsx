import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '@/api/auth'

import { AuthProvider } from '@/features/auth/AuthContext'
import { PolicyPage } from './PolicyPage'
import { OPERATOR_NAME, POLICIES } from './content'

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: '/privacy', element: <PolicyPage /> },
      { path: '/terms', element: <PolicyPage /> },
      { path: '/cookies', element: <PolicyPage /> },
      { path: '/other', element: <PolicyPage /> },
    ],
    { initialEntries: [path] },
  )
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  )
  return router
}

function storeSession(role: 'operator' | 'officer') {
  sessionStorage.setItem(
    'permitflow.session',
    JSON.stringify({
      token: 'tok',
      expiresAt: new Date(Date.now() + 60_000).toISOString(),
      user: { id: '1', email: `${role}@permitflow.example.sg`, full_name: 'Demo', role },
    }),
  )
}

describe('PolicyPage (US-057)', () => {
  afterEach(() => {
    sessionStorage.clear()
    vi.restoreAllMocks()
  })

  it.each(['privacy', 'terms', 'cookies'] as const)('renders the %s policy with every section', (slug) => {
    renderAt(`/${slug}`)
    const policy = POLICIES[slug]
    expect(screen.getByRole('heading', { level: 1, name: policy.title })).toBeInTheDocument()
    expect(screen.getByText(`Last reviewed ${policy.reviewed}`)).toBeInTheDocument()
    for (const section of policy.sections) {
      expect(screen.getByRole('heading', { level: 2, name: section.heading })).toBeInTheDocument()
    }
    expect(screen.getByRole('link', { name: policy.title })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login')
  })

  it.each([
    ['operator', 'Dashboard', '/app/dashboard'],
    ['officer', 'Queue', '/officer/queue'],
  ] as const)('signed in as %s, the policy opens inside the app shell with the rail, not the public frame', async (role, label, href) => {
    storeSession(role)
    vi.spyOn(authApi, 'me').mockResolvedValue({ id: '1', email: `${role}@permitflow.example.sg`, full_name: 'Demo', role })
    renderAt('/privacy')
    // the shell, once the restored session is re-validated: the role's rail links and Sign out are there,
    // the public Sign in button is not
    expect((await screen.findAllByRole('link', { name: label }))[0]).toHaveAttribute('href', href)
    expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Sign in' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: POLICIES.privacy.title })).toBeInTheDocument()
    // the section list on the left links to every section
    for (const section of POLICIES.privacy.sections) {
      expect(screen.getByRole('link', { name: section.heading })).toHaveAttribute('href', expect.stringMatching(/^#/))
    }
  })

  it('names the operator, links the repository, and says it is not a government service', () => {
    renderAt('/privacy')
    expect(screen.getByText(new RegExp(`operated by ${OPERATOR_NAME}`))).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /github.com\/SuhaasNv\/permitflow/ })).toHaveAttribute('rel', 'noreferrer')
    expect(screen.getAllByText(/Not a government service/).length).toBeGreaterThan(0)
  })

  it('states the facts the code guarantees: no cookies, OpenAI and LangSmith transfers, 10 MB uploads', () => {
    renderAt('/privacy')
    expect(screen.getByText(/sets no cookies/)).toBeInTheDocument()
    expect(screen.getByText(/sent to OpenAI \(United States\)/)).toBeInTheDocument()
    expect(screen.getByText(/LangSmith/)).toBeInTheDocument()
    expect(screen.getByText(/at most 10 MB each/)).toBeInTheDocument()
  })

  it('redirects an unknown slug to the privacy policy', () => {
    const router = renderAt('/other')
    expect(router.state.location.pathname).toBe('/privacy')
  })
})
