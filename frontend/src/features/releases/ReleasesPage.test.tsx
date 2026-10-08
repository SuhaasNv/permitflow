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

// What a reader sees first without /health: the newest release (candidates are hidden until it answers).
const latest = RELEASE_NOTES.releases.find((r) => !r.candidate)!
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
    const earlier = RELEASE_NOTES.releases.filter((r) => !r.candidate)[1]
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

  it('signed out, the footer carries the policy links', () => {
    vi.spyOn(healthApi, 'getHealth').mockRejectedValue(new Error('offline'))
    renderAt('/releases')
    const policies = screen.getByRole('navigation', { name: 'Policies' })
    expect(within(policies).getByRole('link', { name: 'Privacy' })).toHaveAttribute('href', '/privacy')
    expect(within(policies).getByRole('link', { name: 'Terms' })).toHaveAttribute('href', '/terms')
    expect(within(policies).getByRole('link', { name: 'Cookies' })).toHaveAttribute('href', '/cookies')
  })
})

describe('ReleasesPage release candidates (US-110)', () => {
  const candidates = RELEASE_NOTES.releases.filter((r) => r.candidate)
  const releases = RELEASE_NOTES.releases.filter((r) => !r.candidate)
  const listHrefs = () =>
    within(screen.getByRole('navigation', { name: 'Releases' }))
      .getAllByRole('link')
      .map((l) => l.getAttribute('href'))

  afterEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  function mockHealth(environment: 'development' | 'production' | 'test', version: string = __APP_VERSION__) {
    vi.spyOn(healthApi, 'getHealth').mockResolvedValue({ status: 'ok', database: 'ok', version, commit: 'abc1234', environment })
  }

  it('has candidates in the real notes, so the checks below are not vacuous', () => {
    expect(candidates.length).toBeGreaterThanOrEqual(2)
  })

  it('development: every candidate is listed in file order with a Release candidate badge beside its version', async () => {
    mockHealth('development')
    renderAt('/releases')
    const list = screen.getByRole('navigation', { name: 'Releases' })
    await vi.waitFor(() => expect(listHrefs()).toEqual(RELEASE_NOTES.releases.map((r) => `/releases/${r.version}`)))
    for (const c of candidates) {
      const link = within(list).getByRole('link', { name: new RegExp(`${c.version.replace(/\./g, '\\.')}.*Release candidate`) })
      const badge = within(link).getByText('Release candidate')
      expect(badge).toHaveAttribute('data-tone', 'warning')
      // a dot plus the words, never colour alone
      expect(badge.querySelector('span[aria-hidden="true"]')).not.toBeNull()
    }
    // released versions carry no badge
    const badged = within(list)
      .getAllByRole('link')
      .filter((l) => within(l).queryByText('Release candidate') !== null)
      .map((l) => l.getAttribute('href'))
    expect(badged).toEqual(candidates.map((c) => `/releases/${c.version}`))
    expect(releases.length).toBeGreaterThan(0)
  })

  it('development: opening a candidate shows its notes with the badge beside the version in the heading', async () => {
    mockHealth('development')
    const rc = candidates[0]
    renderAt(`/releases/${rc.version}`)
    const heading = await screen.findByRole('heading', { level: 2, name: new RegExp(rc.title.slice(1), 'i') })
    const article = heading.closest('article')
    expect(article).not.toBeNull()
    expect(within(article as HTMLElement).getByText(rc.version)).toBeInTheDocument()
    expect(within(article as HTMLElement).getByText('Release candidate')).toBeInTheDocument()
  })

  it('production: candidates are not in the list, and opening one by URL shows its release instead', async () => {
    mockHealth('production')
    renderAt(`/releases/${candidates[0].version}`)
    await vi.waitFor(() => expect(healthApi.getHealth).toHaveBeenCalled())
    await new Promise((r) => setTimeout(r, 10))
    expect(listHrefs()).toEqual(releases.map((r) => `/releases/${r.version}`))
    expect(screen.queryByText('Release candidate')).toBeNull()
    // The build line and version chip name the running build; production never runs a candidate, but this suite's build may.
    for (const c of candidates.filter((x) => x.version !== `v${__APP_VERSION__}`)) expect(screen.queryByText(c.version)).toBeNull()
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(new RegExp(releases[0].title.slice(1), 'i'))
  })

  it('loading: candidates stay hidden until /health answers, then appear on development', async () => {
    let answer: (h: Awaited<ReturnType<typeof healthApi.getHealth>>) => void = () => undefined
    vi.spyOn(healthApi, 'getHealth').mockReturnValue(new Promise((resolve) => (answer = resolve)))
    renderAt('/releases')
    expect(listHrefs()).toEqual(releases.map((r) => `/releases/${r.version}`))
    expect(screen.queryByText('Release candidate')).toBeNull()
    answer({ status: 'ok', database: 'ok', version: __APP_VERSION__, commit: 'abc1234', environment: 'development' })
    await vi.waitFor(() => expect(listHrefs()).toEqual(RELEASE_NOTES.releases.map((r) => `/releases/${r.version}`)))
  })

  it('failed: candidates stay hidden when /health cannot be read', async () => {
    vi.spyOn(healthApi, 'getHealth').mockRejectedValue(new Error('down'))
    renderAt('/releases')
    await new Promise((r) => setTimeout(r, 10))
    expect(listHrefs()).toEqual(releases.map((r) => `/releases/${r.version}`))
    expect(screen.queryByText('Release candidate')).toBeNull()
  })

  it('production: Coming next is unchanged and holds no candidate', async () => {
    mockHealth('production')
    renderAt('/releases')
    await new Promise((r) => setTimeout(r, 10))
    const coming = screen.getAllByRole('complementary', { name: 'Coming next' })[0]
    expect(coming).toHaveTextContent(/v0\.5\.0/)
    expect(coming).not.toHaveTextContent(/candidate|-rc\./i)
  })

  it('This build marks a running release candidate, not the release it belongs to', async () => {
    vi.stubGlobal('__APP_VERSION__', '0.4.0-rc.2')
    mockHealth('development', '0.4.0-rc.2')
    renderAt('/releases')
    const list = screen.getByRole('navigation', { name: 'Releases' })
    await vi.waitFor(() => expect(within(list).getByRole('link', { name: /v0\.4\.0-rc\.2/ })).toBeInTheDocument())
    const rc2 = within(list).getByRole('link', { name: /v0\.4\.0-rc\.2/ })
    expect(within(rc2).getByText('This build')).toBeInTheDocument()
    expect(within(rc2).getByText('Release candidate')).toBeInTheDocument()
    expect(within(list).getAllByText('This build')).toHaveLength(1)
    expect(screen.getByTestId('build-line')).toHaveTextContent('v0.4.0-rc.2')
  })
})
