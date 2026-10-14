import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from '@/api/admin'
import type { AdminUsers } from '@/api/admin'
import * as usageApi from '@/api/aiUsage'
import type { AiUsagePage as Page, AiUsageRow } from '@/api/aiUsage'
import { AppError } from '@/api/client'
import { AppProviders } from '@/app/providers'
import { todayInSingapore } from '@/lib/format'
import { AiUsagePage, usd } from './AiUsagePage'

const APP_ID = '5b0c7a52-6c7b-4d6e-9d0e-1a2b3c4d5e6f'
const USER_ID = '0d9f3d0a-1111-4222-8333-444455556666'

const row = (over: Partial<AiUsageRow> = {}): AiUsageRow => ({
  id: 'r1',
  created_at: '2026-10-10T07:42:00Z',
  application_id: APP_ID,
  reference_no: 'PF-2026-001109',
  business_name: 'Kopi & Kaya Toast House Pte. Ltd.',
  user_id: USER_ID,
  user_name: 'Tan Wei Ling',
  document_type: 'floor_plan',
  model: 'gpt-4.1-mini',
  input_tokens: 3812,
  output_tokens: 1000,
  cost_usd: '0.00160000',
  latency_ms: 5900,
  outcome: 'verified',
  ...over,
})

const page = (over: Partial<Page> = {}): Page => ({
  items: [row(), row({ id: 'r2', document_type: 'tenancy_agreement', outcome: 'issues_found', cost_usd: '0.00210000', latency_ms: 8400 })],
  next_cursor: null,
  totals: { runs: 412, input_tokens: 1401982, output_tokens: 443778, cost_usd: '0.64000000', avg_latency_ms: 6800 },
  today: { runs: 412, input_tokens: 1401982, output_tokens: 443778, cost_usd: '0.64000000', daily_cap: 600 },
  ...over,
})

const users: AdminUsers = {
  self_id: 'u-admin',
  users: [
    { id: USER_ID, email: 'wl@example.sg', full_name: 'Tan Wei Ling', role: 'operator', is_active: true, is_protected: false, created_at: '2026-09-17T00:00:00Z' },
  ],
}

function Where() {
  return <output data-testid="where">{useLocation().search}</output>
}

function renderAt(path = '/admin/ai-usage') {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/admin/ai-usage" element={<AiUsagePage />} />
        </Routes>
        <Where />
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('AI usage (US-100)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'getAdminUsers').mockResolvedValue(users)
  })

  it('shows today against the cap, the one-line totals and each check with its cost in US dollars', async () => {
    vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(page())
    renderAt()
    expect(await screen.findByText('of 600 checks')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '412 of 600 checks used today' })).toBeInTheDocument()
    expect(screen.getByText(/188 left · resets at midnight, Singapore time · the cap is set in/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Settings' })).toHaveAttribute('href', '/admin/settings')
    expect(screen.getByLabelText('Totals for the selected range')).toHaveTextContent(
      '412 checks · 1,845,760 tokens (1,401,982 in, 443,778 out) · US$0.64 · average 6.8 s',
    )
    const first = screen.getAllByRole('row')[1]
    expect(first).toHaveTextContent('Tan Wei Ling')
    expect(first).toHaveTextContent('Floor plan')
    expect(first).toHaveTextContent('Verified')
    expect(first).toHaveTextContent('4,812')
    expect(first).toHaveTextContent('US$0.0016')
    expect(first).toHaveTextContent('5.9 s')
    expect(first).toHaveTextContent('Kopi & Kaya Toast House Pte. Ltd.')
    expect(within(first).getByRole('link', { name: 'PF-2026-001109' })).toHaveAttribute('href', `/admin/applications/${APP_ID}`)
    expect(screen.getByText('Issues found')).toBeInTheDocument()
    expect(screen.getByText('Showing 2 of 412 checks')).toBeInTheDocument()
    expect(screen.getByText(/A cell that starts with =, \+, - or @ is prefixed/)).toBeInTheDocument()
  })

  it('says Not run for a check that never reached the provider and Deleted draft for a gone application', async () => {
    vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(
      page({
        items: [
          row({ id: 'x1', input_tokens: 0, output_tokens: 0, latency_ms: 0, cost_usd: '0.00000000', outcome: 'unavailable' }),
          row({ id: 'x2', application_id: null, reference_no: null, business_name: null }),
        ],
      }),
    )
    renderAt()
    const rows = await screen.findAllByRole('row')
    expect(rows[1]).toHaveTextContent('Not run')
    expect(rows[1]).not.toHaveTextContent('0.0 s')
    expect(rows[2]).toHaveTextContent('Deleted draft')
  })

  it('writes the filters to the address and asks the server for them', async () => {
    const get = vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(page())
    renderAt()
    const today = todayInSingapore()
    await screen.findByText('of 600 checks')
    expect(get).toHaveBeenLastCalledWith({ user: '', reference: '', from: today, to: today }, null)

    await userEvent.selectOptions(screen.getByLabelText('Person'), USER_ID)
    expect(screen.getByTestId('where')).toHaveTextContent(`user=${USER_ID}`)
    expect(get).toHaveBeenLastCalledWith({ user: USER_ID, reference: '', from: today, to: today }, null)

    await userEvent.click(screen.getByRole('button', { name: '7 days' }))
    expect(screen.getByTestId('where')).toHaveTextContent('range=7')
    const last = get.mock.lastCall?.[0]
    expect(last?.to).toBe(today)
    expect(last !== undefined && last.from < today).toBe(true)
    expect(screen.getByRole('button', { name: '7 days' })).toHaveAttribute('aria-pressed', 'true')

    // A half-typed reference asks nothing; Enter applies it, upper-cased.
    const calls = get.mock.calls.length
    await userEvent.type(screen.getByLabelText('Application'), 'pf-2026-001109')
    expect(get.mock.calls.length).toBe(calls)
    await userEvent.keyboard('{Enter}')
    expect(get).toHaveBeenLastCalledWith(expect.objectContaining({ reference: 'PF-2026-001109' }), null)
    expect(screen.getByTestId('where')).toHaveTextContent('reference=PF-2026-001109')
  })

  it('reads the filters from a shared address, a custom range included', async () => {
    const get = vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(page())
    renderAt(`/admin/ai-usage?user=${USER_ID}&reference=PF-2026-001109&range=custom&from=2026-10-04&to=2026-10-10`)
    await screen.findByText('of 600 checks')
    expect(get).toHaveBeenCalledWith({ user: USER_ID, reference: 'PF-2026-001109', from: '2026-10-04', to: '2026-10-10' }, null)
    expect(screen.getByLabelText('From')).toHaveValue('2026-10-04')
    expect(screen.getByLabelText('To')).toHaveValue('2026-10-10')
    expect(screen.getByRole('button', { name: 'Custom' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('refuses a start day after the end day without asking the server', async () => {
    const get = vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(page())
    renderAt('/admin/ai-usage?range=custom&from=2026-10-10&to=2026-10-04')
    expect(await screen.findByText('The start day is after the end day.')).toBeInTheDocument()
    expect(get).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeDisabled()
  })

  it('pages older checks with the cursor', async () => {
    const get = vi
      .spyOn(usageApi, 'getAiUsage')
      .mockResolvedValueOnce(page({ items: [row()], next_cursor: 'cursor-1' }))
      .mockResolvedValueOnce(page({ items: [row({ id: 'r9', user_name: 'Rajesh Menon' })], next_cursor: null }))
    renderAt()
    await userEvent.click(await screen.findByRole('button', { name: 'Show older checks' }))
    expect(await screen.findByText('Rajesh Menon')).toBeInTheDocument()
    expect(get.mock.calls[1]?.[1]).toBe('cursor-1')
    expect(screen.getByText('Showing 2 of 412 checks')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Show older checks' })).not.toBeInTheDocument()
  })

  it('names the filters in the empty state and clears them', async () => {
    vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(
      page({ items: [], totals: { runs: 0, input_tokens: 0, output_tokens: 0, cost_usd: '0.00000000', avg_latency_ms: null } }),
    )
    renderAt(`/admin/ai-usage?user=${USER_ID}&range=7`)
    expect(await screen.findByText('No checks match these filters')).toBeInTheDocument()
    expect(screen.getByText(/No document checks by Tan Wei Ling between/)).toBeInTheDocument()
    expect(screen.getByLabelText('Totals for the selected range')).toHaveTextContent('0 checks · 0 tokens (0 in, 0 out) · US$0.00')
    expect(screen.getByLabelText('Totals for the selected range')).not.toHaveTextContent('average')
    await userEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByTestId('where')).toBeEmptyDOMElement()
  })

  it('downloads the CSV with the current filters', async () => {
    vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(page())
    const download = vi.spyOn(usageApi, 'downloadAiUsageCsv').mockResolvedValue(undefined)
    renderAt(`/admin/ai-usage?user=${USER_ID}&range=custom&from=2026-10-04&to=2026-10-10`)
    await userEvent.click(await screen.findByRole('button', { name: 'Export CSV' }))
    expect(download).toHaveBeenCalledWith({ user: USER_ID, reference: '', from: '2026-10-04', to: '2026-10-10' })
  })

  it('says so when the export fails', async () => {
    vi.spyOn(usageApi, 'getAiUsage').mockResolvedValue(page())
    vi.spyOn(usageApi, 'downloadAiUsageCsv').mockRejectedValue(new AppError(500, { code: 'http_error', message: 'Could not export the checks. Try again.' }))
    renderAt()
    await userEvent.click(await screen.findByRole('button', { name: 'Export CSV' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not export the checks. Try again.')
  })

  it('shows the error panel when the page cannot load', async () => {
    vi.spyOn(usageApi, 'getAiUsage').mockRejectedValue(new AppError(403, { code: 'forbidden', message: 'Not allowed.' }))
    renderAt()
    expect(await screen.findByText('We could not load this page')).toBeInTheDocument()
  })

  it('shows a pulse placeholder while loading', () => {
    vi.spyOn(usageApi, 'getAiUsage').mockReturnValue(new Promise(() => undefined))
    renderAt()
    expect(screen.getByRole('status', { name: 'Loading checks' })).toBeInTheDocument()
    expect(screen.getByLabelText('Loading totals')).toHaveAttribute('aria-busy', 'true')
  })
})

describe('usd', () => {
  it('shows the stored amount exactly, at least two decimals', () => {
    expect(usd('0.00160000')).toBe('US$0.0016')
    expect(usd('0.64000000')).toBe('US$0.64')
    expect(usd('0')).toBe('US$0.00')
    expect(usd('0.00000000')).toBe('US$0.00')
    expect(usd('1234.5')).toBe('US$1,234.50')
  })
})
