import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import type { ApplicationView } from '@/api/applications'
import { CompletionCard } from './CompletionCard'

const view: ApplicationView = {
  id: 'a1',
  reference_no: 'PF-2026-001000',
  licence_title: 'Food Establishment Licence',
  status_label: 'Draft',
  status_tone: 'neutral',
  status_explanation: '',
  can_edit: true,
  can_submit: false,
  sections: [
    { key: 'business', title: 'Business details', description: '', data: {}, complete: true, started: true, errors: {}, editable: true },
    {
      key: 'premises',
      title: 'Premises',
      description: '',
      data: { postal_code: '1' },
      complete: false,
      started: true,
      errors: { postal_code: 'x' },
      editable: true,
    },
  ],
  document_slots: [{ type: 'floor_plan', label: 'Floor plan', present: false, editable: true, document: null }],
  completeness: {
    percent: 33,
    is_complete: false,
    sections_complete: 1,
    sections_total: 2,
    documents_present: 0,
    documents_total: 1,
    missing: ['Section: Premises', 'Document: Floor plan'],
  },
  revision_count: 0,
  needs_operator_action: false,
  created_at: '2026-09-18T00:00:00Z',
  updated_at: '2026-09-18T00:00:00Z',
}

describe('CompletionCard', () => {
  it('renders the server percentage and per-item states with actions', () => {
    render(
      <MemoryRouter>
        <CompletionCard view={view} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '33')
    expect(screen.getByText('Needs attention')).toBeInTheDocument()
    expect(screen.getByText('Fix')).toHaveAttribute('href', '/app/applications/a1/form/premises')
    expect(screen.getByText('Upload')).toHaveAttribute('href', '/app/applications/a1/documents')
  })
})
