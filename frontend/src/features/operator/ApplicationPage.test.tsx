import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import * as api from '@/api/applications'
import type { ApplicationView } from '@/api/applications'
import { AppProviders } from '@/app/providers'
import { respondingView } from '@/test/fixtures'
import { ApplicationPage } from './ApplicationPage'

const submitted: ApplicationView = {
  id: 'a1',
  reference_no: 'PF-2026-001000',
  licence_title: 'Food Establishment Licence',
  status_label: 'Submitted',
  status_tone: 'info',
  status_explanation: 'Received by the licensing office.',
  can_edit: false,
  can_submit: false,
  sections: [
    { key: 'business', title: 'Business details', description: '', data: {}, complete: true, started: true, errors: {}, editable: false },
  ],
  document_slots: [{ type: 'floor_plan', label: 'Floor plan', present: true, editable: false, document: null }],
  completeness: {
    percent: 100,
    is_complete: true,
    sections_complete: 1,
    sections_total: 1,
    documents_present: 1,
    documents_total: 1,
    missing: [],
  },
  revision_count: 1,
  needs_operator_action: false,
  feedback: [],
  resubmit: null,
  revisions: [{ number: 1, submitted_at: '2026-09-18T00:00:00Z' }],
  decision_note: null,
  can_withdraw: true,
  can_delete: false,
  withdrawal_reason: null,
  licence: null,
  site_visit: null,
  clarification: null,
  storage: { used_bytes: 3 * 1024 * 1024, budget_bytes: 150 * 1024 * 1024, remaining_bytes: 147 * 1024 * 1024 },
  created_at: '2026-09-18T00:00:00Z',
  updated_at: '2026-09-18T00:00:00Z',
}

function renderPage() {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={['/app/applications/a1']}>
        <Routes>
          <Route path="/app/applications/:id" element={<ApplicationPage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('ApplicationPage withdraw (US-038)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('withdraws with a reason after confirmation and shows the outcome', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(submitted)
    const withdraw = vi.spyOn(api, 'withdrawApplication').mockResolvedValue({
      ...submitted,
      status_label: 'Withdrawn',
      status_tone: 'neutral',
      can_withdraw: false,
      withdrawal_reason: 'Not opening after all.',
    })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Withdraw application' }))
    const dialog = await screen.findByRole('dialog', { name: 'Withdraw this application?' })
    expect(dialog).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/Reason/), 'Not opening after all.')
    await userEvent.click(screen.getAllByRole('button', { name: 'Withdraw application' }).at(-1)!)
    expect(withdraw).toHaveBeenCalledWith('a1', 'Not opening after all.')
    expect(await screen.findByText('You withdrew this application')).toBeInTheDocument()
    expect(screen.getByText(/Your reason:/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Withdraw application' })).not.toBeInTheDocument()
  })

  it('discards an untouched draft after confirmation and returns to the list (US-045)', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue({
      ...submitted,
      status_label: 'Draft',
      status_tone: 'neutral',
      can_edit: true,
      can_withdraw: false,
      can_delete: true,
      revision_count: 0,
      revisions: [],
      completeness: { ...submitted.completeness, percent: 0, is_complete: false, sections_complete: 0, documents_present: 0 },
    })
    const remove = vi.spyOn(api, 'deleteDraft').mockResolvedValue(undefined)
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Discard draft' }))
    expect(await screen.findByRole('dialog', { name: 'Discard this draft?' })).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: 'Discard draft' }).at(-1)!)
    expect(remove).toHaveBeenCalledWith('a1')
  })

  it('does not offer withdrawal when the server says it is not allowed', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue({
      ...submitted,
      status_label: 'Approved',
      status_tone: 'success',
      can_withdraw: false,
    })
    renderPage()
    expect((await screen.findAllByText('Business details')).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: 'Withdraw application' })).not.toBeInTheDocument()
  })
})

describe('ApplicationPage outcome (US-051)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('offers the licence download after approval even when the officer left no note', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue({
      ...submitted,
      status_label: 'Approved',
      status_tone: 'success',
      can_withdraw: false,
      decision_note: null,
      licence: {
        licence_no: 'FEL-2026-000005',
        issued_at: '2026-09-19T00:00:00Z',
        valid_from: '2026-09-19',
        valid_to: '2027-09-18',
        verification_code: 'ABCD-EFGH',
      },
    })
    renderPage()
    expect(await screen.findByText('Your licence application was approved')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Download licence (PDF)' })).toBeInTheDocument()
    expect(screen.getByText(/Licence FEL-2026-000005/)).toBeInTheDocument()
    expect(screen.queryByText(/Officer's note:/)).not.toBeInTheDocument()
  })
})

describe('ApplicationPage feedback placement (UC1: officer comments at the top)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('renders the feedback notice above the application sections, with each item linked to its target', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(respondingView({ id: 'a1' }))
    renderPage()
    const notice = await screen.findByRole('region', { name: /asked for 1 change/i })
    const sections = screen.getByRole('region', { name: /^application$/i })
    // DOM order is reading order: the notice must come before the sections and the documents.
    expect(notice.compareDocumentPosition(sections) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByText('The floor area does not match the tenancy agreement.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Edit section' })).toHaveAttribute('href', '/app/applications/a1/form/premises')
    expect(screen.getByText('Only the flagged parts are open for editing. Everything else is kept as submitted.')).toBeInTheDocument()
  })
})
