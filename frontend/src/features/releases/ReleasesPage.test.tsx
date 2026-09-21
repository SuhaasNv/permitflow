import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '@/api/auth'
import * as healthApi from '@/api/health'
import * as notificationsApi from '@/api/notifications'
import { AuthProvider } from '@/features/auth/AuthContext'
import { RELEASE_NOTES, ReleasesPage } from './ReleasesPage'
import { hasSeenRelease } from './seen'

type Role = 'operator' | 'officer' | 'admin'

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: '/releases', element: <ReleasesPage /> },
      { path: '/releases/:version', element: <ReleasesPage /> },
    ],
    { initialEntries: [path] },
  )
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>,
  )
  return router
}

function signIn(role: Role) {
  sessionStorage.setItem(
    'permitflow.session',
    JSON.stringify({
      token: 'tok',
      expiresAt: new Date(Date.now() + 60_000).toISOString(),
      user: { id: '1', email: `${role}@permitflow.example.sg`, full_name: 'Demo', role },
    }),
  )
  vi.spyOn(authApi, 'me').mockResolvedValue({ id: '1', email: `${role}@permitflow.example.sg`, full_name: 'Demo', role })
  // The shell's bell fetches on mount; unmocked it would reach a live local API and its 401 would end the session.
  vi.spyOn(notificationsApi, 'getNotifications').mockResolvedValue({ items: [], unread_count: 0 })
}

const latest = RELEASE_NOTES.releases[0]
const headingsOf = (audience: 'operator' | 'officer' | 'admin') =>
  latest.blocks.filter((b) => b.audience === audience).map((b) => b.heading)

describe('ReleasesPage (US-094)', () => {
  afterEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('signed out: the public frame, every block open, the build line and the list with This build', async () => {
    vi.spyOn(healthApi, 'getHealth').mockResolvedValue({ status: 'ok', database: 'ok', version: __APP_VERSION__, commit: 'abc1234', environment: 'development' })
    renderAt('/releases')
    expect(screen.getByRole('heading', { level: 1, name: "What's new" })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument()
    for (const b of latest.blocks) expect(screen.getByRole('heading', { level: 3, name: b.heading })).toBeInTheDocument()
    expect(screen.queryByText('Also in this release')).not.toBeInTheDocument()
    const build = screen.getByTestId('build-line')
    expect(build).toHaveTextContent(`v${__APP_VERSION__}`)
    expect(await within(build).findByText(/abc1234/)).toBeInTheDocument()
    expect(build).toHaveTextContent('development environment')
    // the list: every release, newest first, the running build marked with a label (dot plus text)
    const list = screen.getByRole('navigation', { name: 'Releases' })
    const links = within(list).getAllByRole('link')
    expect(links.map((l) => l.getAttribute('href'))).toEqual(RELEASE_NOTES.releases.map((r) => `/releases/${r.version}`))
    expect(within(list).getByText('This build')).toBeInTheDocument()
    expect(links[0]).toHaveAttribute('aria-current', 'page')
  })

  it.each([
    ['operator', 'officer', 'admin'],
    ['officer', 'operator', 'admin'],
  ] as const)('signed in as %s: own block first under For you, the %s and %s blocks folded', async (role, otherA, otherB) => {
    signIn(role)
    renderAt('/releases')
    expect(await screen.findByRole('button', { name: 'Sign out' })).toBeInTheDocument()
    expect(screen.getByText('For you')).toBeInTheDocument()
    const own = headingsOf(role)
    expect(own.length).toBeGreaterThan(0)
    for (const h of own) expect(screen.getByRole('heading', { level: 3, name: h })).toBeInTheDocument()
    expect(screen.getByText('Also in this release')).toBeInTheDocument()
    for (const h of [...headingsOf(otherA), ...headingsOf(otherB)]) {
      const summary = screen.getByText(h).closest('details')
      expect(summary).not.toBeNull()
      expect(summary).not.toHaveAttribute('open')
    }
    // the reader's block comes before the folded ones in the document
    const ownHeading = screen.getByRole('heading', { level: 3, name: own[0] })
    const folded = screen.getByText('Also in this release')
    expect(ownHeading.compareDocumentPosition(folded) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    // the shared block stays open, marked For everyone
    expect(screen.getByText('For everyone')).toBeInTheDocument()
  })

  it('signed in as admin: everything open, nothing folded, no For you', async () => {
    signIn('admin')
    renderAt('/releases')
    expect(await screen.findByRole('button', { name: 'Sign out' })).toBeInTheDocument()
    for (const b of latest.blocks) expect(screen.getByRole('heading', { level: 3, name: b.heading })).toBeInTheDocument()
    expect(screen.queryByText('Also in this release')).not.toBeInTheDocument()
    expect(screen.queryByText('For you')).not.toBeInTheDocument()
  })

  it('opens an earlier release by version and falls back to the newest for an unknown one', () => {
    const earlier = RELEASE_NOTES.releases[1]
    renderAt(`/releases/${earlier.version}`)
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(new RegExp(earlier.title.slice(1), 'i'))
    expect(screen.getByRole('link', { name: new RegExp(earlier.version) })).toHaveAttribute('aria-current', 'page')
  })

  it('an unknown version shows the newest release', () => {
    renderAt('/releases/v9.9.9')
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(new RegExp(latest.title.slice(1), 'i'))
  })

  it('marks this build as read; the build line copes without the API', async () => {
    vi.spyOn(healthApi, 'getHealth').mockRejectedValue(new Error('down'))
    expect(hasSeenRelease(__APP_VERSION__)).toBe(false)
    renderAt('/releases')
    expect(hasSeenRelease(__APP_VERSION__)).toBe(true)
    const build = screen.getByTestId('build-line')
    expect(build).toHaveTextContent(`v${__APP_VERSION__}`)
    await new Promise((r) => setTimeout(r, 10))
    expect(build).not.toHaveTextContent('environment')
  })
})
