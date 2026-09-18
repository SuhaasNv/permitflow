import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import * as api from '@/api/applications'
import type { ApplicationView } from '@/api/applications'
import { AppProviders } from '@/app/providers'
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
