import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import * as api from '@/api/officer'
import type { QueueItem } from '@/api/officer'
import { AppProviders } from '@/app/providers'
import { OfficerQueuePage } from './QueuePage'

const base: QueueItem = {
  id: 'a1',
  reference_no: 'PF-2026-001005',
  licence_title: 'Food Establishment Licence',
  business_name: 'Kopi & Kaya Toast House Pte. Ltd.',
  premises_summary: '10 Jalan Besar #01-12',
  applicant_name: 'Tan Wei Ling',
  status: 'application_received',
  status_label: 'Application Received',
  status_tone: 'info',
  next_action: 'Start review',
  officer_turn: true,
  decided: false,
  revision_count: 1,
  open_feedback_count: 0,
  documents_attention: 1,
  documents_checking: 0,
  submitted_at: '2026-09-18T01:40:00Z',
  last_activity_at: '2026-09-18T01:40:00Z',
}

function renderPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <OfficerQueuePage />
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('OfficerQueuePage', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('shows the empty state when nothing has been submitted', async () => {
    vi.spyOn(api, 'getQueue').mockResolvedValue({ items: [], officer_turn_count: 0, waiting_on_operator_count: 0, decided_count: 0 })
    renderPage()
    expect(await screen.findByText('Nothing has been submitted yet')).toBeInTheDocument()
  })

  it('lists the officer label and next action, and filters by whose turn it is', async () => {
    const waiting: QueueItem = {
      ...base,
      id: 'a2',
      reference_no: 'PF-2026-001006',
      status: 'pending_pre_site_resubmission',
      status_label: 'Pending Pre-Site Resubmission',
      status_tone: 'warning',
      next_action: 'Waiting on operator',
      officer_turn: false,
    }
    vi.spyOn(api, 'getQueue').mockResolvedValue({
      items: [base, waiting],
      officer_turn_count: 1,
      waiting_on_operator_count: 1,
      decided_count: 0,
    })
    renderPage()
    expect(await screen.findByText('PF-2026-001005')).toBeInTheDocument()
    expect(screen.getByText('Application Received')).toBeInTheDocument()
    expect(screen.getByText('Start review')).toBeInTheDocument()
    expect(screen.queryByText('PF-2026-001006')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Waiting on operator/ }))
    expect(await screen.findByText('PF-2026-001006')).toBeInTheDocument()
    expect(screen.queryByText('PF-2026-001005')).not.toBeInTheDocument()
  })
})
