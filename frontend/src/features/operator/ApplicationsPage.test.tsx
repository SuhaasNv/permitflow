import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'

import * as api from '@/api/applications'
import type { ApplicationSummary } from '@/api/applications'
import { AppProviders } from '@/app/providers'
import { ApplicationsPage } from './ApplicationsPage'

const base: ApplicationSummary = {
  id: 'a1',
  reference_no: 'PF-2026-001000',
  licence_title: 'Food Establishment Licence',
  status_label: 'Draft',
  status_tone: 'neutral',
  business_name: 'Kopi Corner',
  premises_summary: '10 Jalan Besar #01-12',
  percent: 40,
  revision_count: 0,
  needs_operator_action: false,
  created_at: '2026-09-18T01:00:00Z',
  updated_at: '2026-09-18T01:00:00Z',
}

function renderPage() {
  return render(
    <AppProviders>
      <MemoryRouter>
        <ApplicationsPage />
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('ApplicationsPage', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('searches by reference, business or address and can clear the search', async () => {
    vi.spyOn(api, 'listApplications').mockResolvedValue([
      base,
      { ...base, id: 'a2', reference_no: 'PF-2026-001001', business_name: 'Nasi Lemak Corner', premises_summary: '5 Tampines Street 11' },
    ])
    renderPage()
    expect(await screen.findByText('PF-2026-001001')).toBeInTheDocument()
    const box = screen.getByRole('searchbox', { name: /Search reference/ })
    await userEvent.type(box, 'jalan')
    expect(screen.getByText('PF-2026-001000')).toBeInTheDocument()
    expect(screen.queryByText('PF-2026-001001')).not.toBeInTheDocument()
    await userEvent.clear(box)
    await userEvent.type(box, '001001')
    expect(screen.getByText('PF-2026-001001')).toBeInTheDocument()
    await userEvent.clear(box)
    await userEvent.type(box, 'nowhere')
    expect(screen.getByText(/No applications match "nowhere"/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(screen.getByText('PF-2026-001000')).toBeInTheDocument()
  })
})
