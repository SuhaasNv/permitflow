import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/api/admin'
import type { AdminOverview, AdminUsers, AuditFeed } from '@/api/admin'
import { AppError } from '@/api/client'
import { AppProviders } from '@/app/providers'
import { AdminActivityPage } from './ActivityPage'
import { AdminOverviewPage } from './OverviewPage'
import { AdminUsersPage, conflictMessage, lockedReason } from './UsersPage'

const overview: AdminOverview = {
  as_of: '2026-09-21T06:32:00Z',
  totals: { applications: 30, submitted: 25, drafts: 5, with_office: 12, waiting_on_operators: 6, idle_over_7_days: 2 },
  counts: [
    { status: 'draft', label: 'Draft', tone: 'neutral', turn: 'draft', count: 5 },
    { status: 'application_received', label: 'Application Received', tone: 'info', turn: 'office', count: 3 },
    { status: 'pending_pre_site_resubmission', label: 'Pending Pre-Site Resubmission', tone: 'warning', turn: 'operator', count: 6 },
    { status: 'approved', label: 'Approved', tone: 'success', turn: 'decided', count: 16 },
  ],
  idle: [
    {
      id: 'a-209',
      reference_no: 'PF-2026-000209',
      business_name: 'Nasi Padang Corner',
      status: 'pending_pre_site_resubmission',
      label: 'Pending Pre-Site Resubmission',
      tone: 'warning',
      days_idle: 9,
      last_activity_at: '2026-09-12T02:00:00Z',
    },
  ],
  today: {
    day: '2026-09-21',
    submissions: 2,
    resubmissions: 1,
    checklists_submitted: 1,
    clarification_rounds: 1,
    runs_today: 41,
    runs_per_day_quota: 1000,
  },
  checks: {
    runs: 38,
    verified: 29,
    issues_found: 6,
    needs_review: 2,
    unreadable: 0,
    failed_or_unavailable: 1,
    still_running: 0,
    average_seconds: 4.1,
    p95_seconds: 9.8,
    provider: 'OpenAI',
    model: 'gpt-4.1-mini',
  },
}

const page1: AuditFeed = {
  events: [
    {
      id: 'e1',
      event_type: 'user.role_changed',
      summary: 'lim@example.sg: role changed from operator to officer',
      actor_name: 'Priya Nair',
      actor_role: 'admin',
      application_id: null,
      reference_no: null,
      created_at: '2026-09-21T06:05:00Z',
    },
    {
      id: 'e2',
      event_type: 'status.changed',
      summary: 'Status: Under Review → Site Visit Scheduled',
      actor_name: 'Rahim bin Abdullah',
      actor_role: 'officer',
      application_id: 'a-231',
      reference_no: 'PF-2026-000231',
      created_at: '2026-09-21T05:58:00Z',
    },
  ],
  next_cursor: '1000,e2',
}
const page2: AuditFeed = {
  events: [
    {
      id: 'e3',
      event_type: 'licence.issued',
      summary: 'Licence FEL-2026-000011 issued, valid to 2027-09-21',
      actor_name: 'Rahim bin Abdullah',
      actor_role: 'officer',
      application_id: 'a-202',
      reference_no: 'PF-2026-000202',
      created_at: '2026-09-21T00:50:00Z',
    },
  ],
  next_cursor: null,
}

const users: AdminUsers = {
  self_id: 'u-admin',
  users: [
    {
      id: 'u-admin',
      email: 'admin@permitflow.example.sg',
      full_name: 'Priya Nair',
      role: 'admin',
      is_active: true,
      is_protected: true,
      created_at: '2026-09-17T00:00:00Z',
    },
    {
      id: 'u-off',
      email: 'officer@permitflow.example.sg',
      full_name: 'Rahim bin Abdullah',
      role: 'officer',
      is_active: true,
      is_protected: true,
      created_at: '2026-09-17T00:00:00Z',
    },
    {
      id: 'u-lim',
      email: 'officer2@permitflow.example.sg',
      full_name: 'Lim Jun Hao',
      role: 'operator',
      is_active: true,
      is_protected: false,
      created_at: '2026-09-20T00:00:00Z',
    },
    {
      id: 'u-con',
      email: 'contractor@permitflow.example.sg',
      full_name: 'Contractor account',
      role: 'operator',
      is_active: false,
      is_protected: false,
      created_at: '2026-09-18T00:00:00Z',
    },
  ],
}

function renderAt(path: string) {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/admin/overview" element={<AdminOverviewPage />} />
          <Route path="/admin/activity" element={<AdminActivityPage />} />
          <Route path="/admin/users" element={<AdminUsersPage />} />
          <Route path="/admin/applications/:id" element={<div>CASE</div>} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('admin overview (S-40, US-070)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('shows the strip, every status with its count, the health block, today and the idle list', async () => {
    vi.spyOn(api, 'getAdminOverview').mockResolvedValue(overview)
    renderAt('/admin/overview')
    expect(await screen.findByText('30 applications · 12 with the office · 6 waiting on operators')).toBeInTheDocument()
    const strip = screen.getByRole('list', { name: 'Key numbers' })
    expect(within(strip).getByText('Idle over 7 days')).toBeInTheDocument()
    expect(within(strip).getByText('Oldest since 12 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('(not visible to officers)')).toBeInTheDocument()
    expect(screen.getByRole('row', { name: /Pending Pre-Site Resubmission/ })).toHaveTextContent('6')
    expect(screen.getByText('Slowest 5 % of checks').nextElementSibling).toHaveTextContent('9.8 s')
    expect(screen.getByText(/Provider: OpenAI, gpt-4.1-mini/)).toBeInTheDocument()
    expect(screen.getByText('41 of 1,000')).toBeInTheDocument()
    expect(screen.getByText('Singapore calendar day, 21 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('Nasi Padang Corner')).toBeInTheDocument()
    expect(screen.getByText('9 d')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('link', { name: 'Open' }))
    expect(await screen.findByText('CASE')).toBeInTheDocument()
  })

  it('says when nothing is idle and when the provider is the mock', async () => {
    vi.spyOn(api, 'getAdminOverview').mockResolvedValue({
      ...overview,
      idle: [],
      totals: { ...overview.totals, idle_over_7_days: 0 },
      checks: { ...overview.checks, runs: 0, provider: 'none (mock)', model: null, average_seconds: null, p95_seconds: null },
    })
    renderAt('/admin/overview')
    expect(await screen.findByText(/Nothing has been idle for more than seven days/)).toBeInTheDocument()
    expect(screen.getByText('Nothing is stuck')).toBeInTheDocument()
    expect(screen.getByText(/Provider: none \(mock\)\./)).toBeInTheDocument()
    expect(screen.getAllByText('no runs yet')).toHaveLength(2)
  })

  it('shows the error state with a retry', async () => {
    // a 4xx is not retried by the query client, so the panel shows at once
    vi.spyOn(api, 'getAdminOverview').mockRejectedValue(new AppError(403, { code: 'forbidden', message: 'Not available for your role.' }))
    renderAt('/admin/overview')
    expect(await screen.findByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
})

describe('admin activity (S-42, US-072)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('lists events newest first, user rows without a case link, filters by family and loads older pages', async () => {
    const feed = vi.spyOn(api, 'getAuditFeed').mockResolvedValueOnce(page1).mockResolvedValueOnce(page2)
    renderAt('/admin/activity')
    expect(await screen.findByText('lim@example.sg: role changed from operator to officer')).toBeInTheDocument()
    expect(screen.getByText('no case')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'PF-2026-000231' })).toHaveAttribute('href', '/admin/applications/a-231')
    expect(screen.getByText('Priya Nair · administrator')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'User' }))
    expect(screen.queryByText(/Under Review → Site Visit Scheduled/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /^All/ }))
    await userEvent.click(screen.getByRole('button', { name: 'Show older activity' }))
    expect(await screen.findByText(/Licence FEL-2026-000011 issued/)).toBeInTheDocument()
    expect(feed).toHaveBeenLastCalledWith('1000,e2')
    expect(screen.getByText('That is everything.')).toBeInTheDocument()
    expect(screen.getByText('3 events loaded')).toBeInTheDocument()
  })

  it('says so when nothing has happened', async () => {
    vi.spyOn(api, 'getAuditFeed').mockResolvedValue({ events: [], next_cursor: null })
    renderAt('/admin/activity')
    expect(await screen.findByText('Nothing has happened yet')).toBeInTheDocument()
  })
})

describe('admin users (S-41, US-073)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('disables the own row and protected rows with the reason, and filters by role and search', async () => {
    vi.spyOn(api, 'getAdminUsers').mockResolvedValue(users)
    renderAt('/admin/users')
    expect(await screen.findByText('4 accounts · 2 operators · 1 licensing officer · 1 administrator')).toBeInTheDocument()
    const own = screen.getByText('(you)').closest('li')!
    const ownButtons = within(own).getAllByRole('button')
    expect(ownButtons.every((b) => b.hasAttribute('disabled'))).toBe(true)
    expect(ownButtons[0]).toHaveAttribute('title', 'You cannot change your own account')
    const protectedRow = screen.getByText('Rahim bin Abdullah').closest('li')!
    expect(within(protectedRow).getByRole('button', { name: 'Change role' })).toHaveAttribute('title', 'Demonstration account, protected')
    expect(within(protectedRow).getByText('Protected')).toBeInTheDocument()
    expect(screen.getByText('Deactivated')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Licensing officers/ }))
    expect(screen.queryByText('Lim Jun Hao')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /^All/ }))
    await userEvent.type(screen.getByRole('searchbox', { name: 'Search by name or email' }), 'contractor')
    expect(screen.getByText('Contractor account')).toBeInTheDocument()
    expect(screen.queryByText('Lim Jun Hao')).not.toBeInTheDocument()
    await userEvent.clear(screen.getByRole('searchbox', { name: 'Search by name or email' }))
    await userEvent.type(screen.getByRole('searchbox', { name: 'Search by name or email' }), 'zzz')
    expect(screen.getByText('No accounts match')).toBeInTheDocument()
  })

  it('changes a role through the dialog with the consequence sentence, and shows a 409 as the server says it', async () => {
    vi.spyOn(api, 'getAdminUsers').mockResolvedValue(users)
    const patch = vi
      .spyOn(api, 'patchAdminUser')
      .mockRejectedValueOnce(
        new AppError(409, { code: 'last_admin', message: 'This is the last active administrator; it cannot be changed.' }),
      )
      .mockResolvedValueOnce({ ...users.users[2]!, role: 'officer' })
    renderAt('/admin/users')
    const row = (await screen.findByText('Lim Jun Hao')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Change role' }))
    const dialog = await screen.findByRole('dialog', { name: "Change Lim Jun Hao's role?" })
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Licensing officer' }))
    expect(
      within(dialog).getByText('They get licensing officer permissions on their next request. This does not sign them out.'),
    ).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Change role' }))
    expect(await within(dialog).findByText('This is the last active administrator.')).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Change role' }))
    await waitFor(() => expect(patch).toHaveBeenCalledTimes(2))
    expect(patch).toHaveBeenLastCalledWith('u-lim', { role: 'officer' })
    await waitFor(() => expect(screen.queryByRole('dialog', { name: "Change Lim Jun Hao's role?" })).not.toBeInTheDocument())
    expect(within(screen.getByText('Lim Jun Hao').closest('li')!).getByText('Licensing officer')).toBeInTheDocument()
  })

  it('deactivates and reactivates with a danger dialog, and creates an account from the page', async () => {
    vi.spyOn(api, 'getAdminUsers').mockResolvedValue(users)
    const patch = vi.spyOn(api, 'patchAdminUser').mockImplementation(async (id, body) => ({
      ...users.users.find((u) => u.id === id)!,
      ...(body.is_active !== undefined ? { is_active: body.is_active } : {}),
    }))
    const create = vi.spyOn(api, 'createAdminUser').mockResolvedValue({
      id: 'u-new',
      email: 'ng.liying@example.sg',
      full_name: 'Ng Li Ying',
      role: 'officer',
      is_active: true,
      is_protected: false,
      created_at: '2026-09-21T06:00:00Z',
    })
    renderAt('/admin/users')
    const row = (await screen.findByText('Lim Jun Hao')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Deactivate' }))
    const dialog = await screen.findByRole('dialog', { name: 'Deactivate Lim Jun Hao?' })
    expect(within(dialog).getByText(/signed out on their next request/)).toBeInTheDocument()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Deactivate' }))
    await waitFor(() => expect(patch).toHaveBeenCalledWith('u-lim', { is_active: false }))
    const contractor = screen.getByText('Contractor account').closest('li')!
    await userEvent.click(within(contractor).getByRole('button', { name: 'Reactivate' }))
    await userEvent.click(
      within(await screen.findByRole('dialog', { name: 'Reactivate Contractor account?' })).getByRole('button', { name: 'Reactivate' }),
    )
    await waitFor(() => expect(patch).toHaveBeenCalledWith('u-con', { is_active: true }))

    await userEvent.click(screen.getByRole('button', { name: 'Add an account' }))
    const add = await screen.findByRole('dialog', { name: 'Add an account' })
    await userEvent.click(within(add).getByRole('button', { name: 'Create account' }))
    expect(within(add).getByText("Enter the person's name.")).toBeInTheDocument()
    expect(within(add).getByText('At least 12 characters.')).toBeInTheDocument()
    await userEvent.type(within(add).getByLabelText(/Full name/), 'Ng Li Ying')
    await userEvent.type(within(add).getByLabelText(/Email address/), 'Ng.LiYing@Example.sg')
    await userEvent.type(within(add).getByLabelText(/Temporary password/), 'Correct-Horse-9-Battery')
    await userEvent.click(within(add).getByRole('button', { name: 'Create account' }))
    await waitFor(() =>
      expect(create).toHaveBeenCalledWith({
        email: 'ng.liying@example.sg',
        full_name: 'Ng Li Ying',
        role: 'officer',
        password: 'Correct-Horse-9-Battery',
      }),
    )
  })

  it('words the reasons and the conflicts as the design says', () => {
    const me = users.users[0]!
    expect(lockedReason(me, 'u-admin')).toBe('You cannot change your own account')
    expect(lockedReason(users.users[1]!, 'u-admin')).toBe('Demonstration account, protected')
    expect(lockedReason(users.users[2]!, 'u-admin')).toBeNull()
    expect(conflictMessage(new AppError(409, { code: 'self_change', message: 'x' }))).toBe('You cannot change your own account.')
    expect(conflictMessage(new AppError(409, { code: 'protected_account', message: 'x' }))).toBe('Demonstration account, protected.')
    expect(conflictMessage(new AppError(409, { code: 'try_again', message: 'x' }))).toMatch(/Try again/)
    expect(conflictMessage(new AppError(500, { code: 'internal_error', message: 'Server said so.' }))).toBe('Server said so.')
    expect(conflictMessage(new Error('boom'))).toBe('Something went wrong. Try again.')
  })
})
