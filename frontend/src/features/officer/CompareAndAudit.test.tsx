import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as formApi from '@/api/formSchema'
import * as api from '@/api/officer'
import { AppProviders } from '@/app/providers'
import { formSchema, officerView } from '@/test/fixtures'
import { AuditTrail } from './AuditTrail'
import { ComparePanel } from './ComparePanel'

const compare: api.Compare = {
  application_id: 'app-1',
  from_revision: 1,
  to_revision: 2,
  sections: [
    { key: 'business', title: 'Business details', changed: false, fields: [] },
    {
      key: 'premises',
      title: 'Premises',
      changed: true,
      fields: [{ key: 'postal_code', label: 'Postal code', old: '208787', new: '208788' }],
    },
  ],
  documents: [
    {
      type: 'business_profile',
      label: 'Business profile (ACRA)',
      change: 'unchanged',
      old: { id: 'a', filename: 'bp.pdf' },
      new: { id: 'a', filename: 'bp.pdf' },
    },
    {
      type: 'floor_plan',
      label: 'Floor plan',
      change: 'replaced',
      old: { id: 'b', filename: 'old.pdf' },
      new: { id: 'c', filename: 'new.pdf' },
    },
  ],
  changed_section_count: 1,
  changed_document_count: 1,
}

describe('ComparePanel (FR-022, FR-023)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
  })

  it('needs two revisions', () => {
    render(
      <AppProviders>
        <ComparePanel
          view={officerView({ revisions: [officerView().revisions[0]], current_revision_number: 1, previous_revision_number: null })}
        />
      </AppProviders>,
    )
    expect(screen.getByText(/Only one revision so far/)).toBeInTheDocument()
  })

  it('defaults to previous → current, shows only what changed, and can reveal the unchanged parts', async () => {
    const spy = vi.spyOn(api, 'compareRevisions').mockResolvedValue(compare)
    render(
      <AppProviders>
        <ComparePanel view={officerView()} />
      </AppProviders>,
    )
    await waitFor(() => expect(spy).toHaveBeenCalledWith('app-1', 1, 2))
    expect(await screen.findByText('Postal code')).toBeInTheDocument()
    expect(screen.getByText('208787')).toBeInTheDocument()
    expect(screen.getByText('208788')).toBeInTheDocument()
    expect(screen.getByText('Floor plan')).toBeInTheDocument()
    expect(screen.queryByText('Business profile (ACRA)')).not.toBeInTheDocument()
    expect(screen.queryByText('Business details')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Show unchanged' }))
    expect(screen.getByText('Business profile (ACRA)')).toBeInTheDocument()
    expect(screen.getByText('Business details')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hide unchanged' })).toBeInTheDocument()
  })

  it('refetches when the pair changes and says so when the pair is identical', async () => {
    const spy = vi
      .spyOn(api, 'compareRevisions')
      .mockResolvedValue({ ...compare, sections: [], documents: [], changed_section_count: 0, changed_document_count: 0 })
    render(
      <AppProviders>
        <ComparePanel view={officerView()} />
      </AppProviders>,
    )
    await waitFor(() => expect(spy).toHaveBeenCalledWith('app-1', 1, 2))
    await userEvent.selectOptions(screen.getByLabelText('From'), '2')
    expect(screen.getByText('Pick two different revisions.')).toBeInTheDocument()
  })
})

describe('AuditTrail (FR-025)', () => {
  const events: api.AuditEvent[] = [
    {
      id: 'e1',
      event_type: 'application.created',
      summary: 'Application PF-2026-001000 created',
      actor_name: 'Tan Wei Ling',
      actor_role: 'operator',
      payload: {},
      created_at: '2026-09-19T00:50:00Z',
    },
    {
      id: 'e2',
      event_type: 'status.changed',
      summary: 'Status: Draft → Application Received',
      actor_name: 'Tan Wei Ling',
      actor_role: 'operator',
      payload: { from: 'draft', to: 'application_received' },
      created_at: '2026-09-19T01:10:00Z',
    },
    {
      id: 'e3',
      event_type: 'feedback.released',
      summary: '1 feedback item sent to the operator',
      actor_name: 'Rahim bin Abdullah',
      actor_role: 'officer',
      payload: {},
      created_at: '2026-09-19T02:00:00Z',
    },
    {
      id: 'e4',
      event_type: 'verification.completed',
      summary: 'Check finished: verified (openai)',
      actor_name: null,
      actor_role: null,
      payload: {},
      created_at: '2026-09-19T02:50:10Z',
    },
  ]

  beforeEach(() => vi.restoreAllMocks())

  it('loads only when opened, lists every event with its actor, and filters by family', async () => {
    const spy = vi.spyOn(api, 'getAuditTrail').mockResolvedValue({ application_id: 'app-1', events })
    render(
      <AppProviders>
        <AuditTrail applicationId="app-1" />
      </AppProviders>,
    )
    expect(spy).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Show' }))
    await waitFor(() => expect(spy).toHaveBeenCalledWith('app-1'))
    expect(await screen.findByText('Status: Draft → Application Received')).toBeInTheDocument()
    expect(screen.getByText(/Rahim bin Abdullah \(officer\)/)).toBeInTheDocument()
    expect(screen.getByText(/System/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /All 4/ })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Feedback' }))
    expect(screen.getByText('1 feedback item sent to the operator')).toBeInTheDocument()
    expect(screen.queryByText('Status: Draft → Application Received')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Hide' }))
    expect(screen.queryByText('1 feedback item sent to the operator')).not.toBeInTheDocument()
  })
})
