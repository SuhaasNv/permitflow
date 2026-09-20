import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import { AppError } from '@/api/client'
import * as formApi from '@/api/formSchema'
import * as api from '@/api/officer'
import type { OfficerApplication } from '@/api/officer'
import { AppProviders } from '@/app/providers'
import { OfficerCasePage } from './CasePage'
import { ReadOnlyProvider } from './readOnly'

const schema = {
  sections: [
    {
      key: 'business',
      title: 'Business details',
      description: '',
      fields: [
        {
          key: 'business_name',
          label: 'Business name',
          kind: 'text',
          required: true,
          max_length: 120,
          pattern: null,
          pattern_message: null,
          options: [],
          min_value: null,
          max_value: null,
          help: null,
          must_be_true: false,
        },
      ],
    },
  ],
}

const view: OfficerApplication = {
  id: 'a1',
  reference_no: 'PF-2026-001005',
  licence_title: 'Food Establishment Licence',
  status: 'application_received',
  status_label: 'Application Received',
  status_tone: 'info',
  applicant: { id: 'u1', full_name: 'Tan Wei Ling', email: 'op@example.sg' },
  business_name: 'Kopi & Kaya Toast House Pte. Ltd.',
  premises_summary: '10 Jalan Besar #01-12',
  sections: [
    {
      key: 'business',
      title: 'Business details',
      description: '',
      data: { business_name: 'Kopi & Kaya Toast House Pte. Ltd.' },
      complete: true,
    },
  ],
  documents: [
    {
      id: 'd1',
      document_type: 'floor_plan',
      label: 'Floor plan',
      original_filename: 'plan.pdf',
      content_type: 'application/pdf',
      size_bytes: 1024,
      uploaded_at: '2026-09-18T01:40:00Z',
      in_current_revision: true,
      verification: {
        status: 'issues_found',
        summary: '1 issue found.',
        confidence: 0.7,
        issues: [
          {
            code: 'wrong_document_type',
            severity: 'high',
            message: 'This does not look like a floor plan.',
            evidence: 'ACRA business profile',
          },
        ],
        missing_information: [],
        error_reason: null,
        provider: 'mock',
        requested_at: '2026-09-18T01:40:00Z',
        model: 'mock-1',
        finished_at: '2026-09-18T01:40:10Z',
      },
    },
  ],
  missing_document_types: [],
  verification_summary: { total: 1, verified: 0, issues_found: 1, needs_review: 0, checking: 0, other: 0 },
  revisions: [{ id: 'r1', number: 1, submitted_at: '2026-09-18T01:40:00Z', submitted_by: 'Tan Wei Ling' }],
  current_revision_number: 1,
  previous_revision_number: null,
  changed_sections: [],
  changed_document_types: [],
  addressed_unresolved_count: 0,
  feedback: [],
  open_feedback_count: 0,
  feedback_editable: false,
  feedback_locked_reason: 'Start the review to add feedback.',
  actions: [
    { target: 'under_review', label: 'Start review', enabled: true, reason: null, requires_note: false },
    { target: 'rejected', label: 'Reject', enabled: true, reason: null, requires_note: true },
  ],
  decision_note: null,
  withdrawal_reason: null,
  licence: null,
  site_visit: null,
  checklist: null,
  clarification: null,
  version: 3,
  created_at: '2026-09-18T01:00:00Z',
  updated_at: '2026-09-18T01:40:00Z',
}

function renderPage() {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={['/officer/applications/a1']}>
        <Routes>
          <Route path="/officer/applications/:id" element={<OfficerCasePage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

function renderReadOnly() {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={['/admin/applications/a1']}>
        <Routes>
          <Route
            path="/admin/applications/:id"
            element={
              <ReadOnlyProvider value={true}>
                <OfficerCasePage />
              </ReadOnlyProvider>
            }
          />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('OfficerCasePage read-only for an administrator (S-43, US-072)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(schema as never)
  })

  it('renders the case with the banner and no control, and never asks for the officer-only templates', async () => {
    const underReview: OfficerApplication = {
      ...view,
      status: 'under_review',
      status_label: 'Under Review',
      feedback_editable: true,
      feedback_locked_reason: null,
      actions: [],
      feedback: [
        {
          id: 'f1',
          target_type: 'section',
          section_key: 'business',
          document_type: null,
          target_label: 'Business details',
          message: 'Please confirm the UEN.',
          template_key: null,
          resolution: 'addressed',
          raised_in_revision: 1,
          author_name: 'Rahim',
          created_at: '2026-09-18T01:50:00Z',
          released_to_operator_at: '2026-09-18T01:55:00Z',
          addressed_in_revision: 2,
          resolved_at: null,
          can_undo: false,
        },
      ],
    }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(underReview)
    const templates = vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([])
    renderReadOnly()
    expect(await screen.findByText('Read-only')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Overview' })).toHaveAttribute('href', '/admin/overview')
    expect(screen.getByText('Every action on this case stays with the licensing officer; you are reading it.')).toBeInTheDocument()
    expect(screen.getByText('Feedback is written by the licensing officer.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add feedback' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark resolved' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Not fixed' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Re-run check' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start review' })).not.toBeInTheDocument()
    expect(screen.getByText('Need officer review')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to the overview' })).toBeInTheDocument()
    expect(templates).not.toHaveBeenCalled()
  })
})

describe('OfficerCasePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(schema as never)
    vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([])
  })

  it('shows the submission, the check evidence and the internal status label', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(view)
    renderPage()
    expect(await screen.findByText('Kopi & Kaya Toast House Pte. Ltd.', { selector: 'h1' })).toBeInTheDocument()
    expect(screen.getByText('Application Received')).toBeInTheDocument()
    expect(screen.getByText('confidence 70%')).toBeInTheDocument()
    expect(screen.getByText('ACRA business profile')).toBeInTheDocument()
    expect(screen.getByText('wrong_document_type')).toBeInTheDocument()
  })

  it('shows the hidden check rows only when they are non-zero', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...view,
      verification_summary: { total: 4, verified: 1, issues_found: 1, needs_review: 0, checking: 1, other: 1 },
    })
    renderPage()
    const card = (await screen.findByRole('heading', { name: 'Document checks' })).closest('section')!
    expect(within(card).getByText('Documents').nextElementSibling).toHaveTextContent('4')
    expect(within(card).getByText('Still checking').nextElementSibling).toHaveTextContent('1')
    expect(within(card).getByText('Not checked').nextElementSibling).toHaveTextContent('1')
    expect(screen.queryByText('Analysed')).not.toBeInTheDocument()
  })

  it('hides Still checking and Not checked when they are zero', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(view)
    renderPage()
    await screen.findByRole('heading', { name: 'Document checks' })
    expect(screen.queryByText('Still checking')).not.toBeInTheDocument()
    expect(screen.queryByText('Not checked')).not.toBeInTheDocument()
  })

  it('starts the review through the transition endpoint with the expected version', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(view)
    const spy = vi
      .spyOn(api, 'transitionApplication')
      .mockResolvedValue({ ...view, status: 'under_review', status_label: 'Under Review', version: 4, actions: [] })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Start review' }))
    const confirm = screen.getAllByRole('button', { name: 'Start review' }).at(-1)!
    await userEvent.click(confirm)
    await waitFor(() => expect(spy).toHaveBeenCalledWith('a1', { target: 'under_review', note: undefined, expected_version: 3 }))
    expect(await screen.findByText('Under Review')).toBeInTheDocument()
  })

  it('warns in the Approve dialog when checks are unresolved, and stays silent when they are not', async () => {
    const approvable = {
      ...view,
      status: 'pending_approval',
      status_label: 'Route to Approval',
      actions: [{ target: 'approved', label: 'Approve', enabled: true, reason: null, requires_note: false }],
    }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...approvable,
      verification_summary: { total: 4, verified: 2, issues_found: 1, needs_review: 0, checking: 0, other: 1 },
    })
    const { unmount } = renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByText('2 documents still have unresolved check results')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Approve' }).at(-1)).toBeEnabled()
    unmount()

    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...approvable,
      verification_summary: { total: 4, verified: 4, issues_found: 0, needs_review: 0, checking: 0, other: 0 },
    })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Approve' }))
    expect(await screen.findByRole('dialog', { name: 'Approve this application?' })).toBeInTheDocument()
    expect(screen.queryByText(/unresolved check results/)).not.toBeInTheDocument()
  })

  it('requires a note before rejecting', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(view)
    const spy = vi.spyOn(api, 'transitionApplication')
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Reject' }))
    await userEvent.click(screen.getAllByRole('button', { name: 'Reject' }).at(-1)!)
    expect(await screen.findByText(/Write a note for the operator/)).toBeInTheDocument()
    expect(spy).not.toHaveBeenCalled()
  })

  it('adds feedback tied to a section while under review', async () => {
    const underReview: OfficerApplication = {
      ...view,
      status: 'under_review',
      status_label: 'Under Review',
      feedback_editable: true,
      feedback_locked_reason: null,
      actions: [],
    }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(underReview)
    const spy = vi.spyOn(api, 'createFeedback').mockResolvedValue({
      ...underReview,
      open_feedback_count: 1,
      feedback: [
        {
          id: 'f1',
          target_type: 'section',
          section_key: 'business',
          document_type: null,
          target_label: 'Business details',
          message: 'Please confirm the UEN.',
          template_key: null,
          resolution: 'open',
          raised_in_revision: 1,
          author_name: 'Rahim',
          created_at: '2026-09-19T01:00:00Z',
          released_to_operator_at: null,
          addressed_in_revision: null,
          resolved_at: null,
          can_undo: false,
        },
      ],
    })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Add feedback' }))
    await userEvent.selectOptions(screen.getByLabelText(/About/), 'section:business')
    await userEvent.type(screen.getByLabelText(/Feedback for the operator/), 'Please confirm the UEN.')
    await userEvent.click(screen.getByRole('button', { name: 'Add feedback' }))
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith('a1', {
        target_type: 'section',
        section_key: 'business',
        document_type: null,
        message: 'Please confirm the UEN.',
        template_key: null,
      }),
    )
    expect(await screen.findByText('1 open feedback')).toBeInTheDocument()
    expect(screen.getByText('Draft, not sent yet')).toBeInTheDocument()
  })

  it('shows the stale banner on a version conflict and reloads the case on request', async () => {
    const get = vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(view)
    vi.spyOn(api, 'transitionApplication').mockRejectedValue(
      new AppError(409, { code: 'version_conflict', message: 'The application changed.', details: { current: 4 } }),
    )
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Start review' }))
    await userEvent.click(screen.getAllByRole('button', { name: 'Start review' }).at(-1)!)
    expect(await screen.findByText('This application changed since you opened it')).toBeInTheDocument()
    const calls = get.mock.calls.length
    await userEvent.click(screen.getByRole('button', { name: /Reload/ }))
    await waitFor(() => expect(get.mock.calls.length).toBeGreaterThan(calls))
  })

  it('re-runs a document check from the case and reports a refusal', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(view)
    const rerun = vi
      .spyOn(api, 'rerunOfficerCheck')
      .mockRejectedValue(new AppError(409, { code: 'check_in_progress', message: 'A check is already running.' }))
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Re-run check' }))
    await waitFor(() => expect(rerun).toHaveBeenCalledWith('a1', 'd1'))
    expect(await screen.findByText('Could not re-run the check')).toBeInTheDocument()
  })

  it('fills the composer from a template and lets the officer change the target', async () => {
    const underReview: OfficerApplication = {
      ...view,
      status: 'under_review',
      status_label: 'Under Review',
      feedback_editable: true,
      feedback_locked_reason: null,
      actions: [],
    }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(underReview)
    vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([
      {
        key: 'floor_plan_unclear',
        title: 'Floor plan does not show the food preparation area',
        target_type: 'document',
        section_key: null,
        document_type: 'floor_plan',
        message: 'Please upload a plan that marks the preparation, storage and washing areas.',
      },
    ])
    const spy = vi.spyOn(api, 'createFeedback').mockResolvedValue(underReview)
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Add feedback' }))
    await userEvent.selectOptions(screen.getByLabelText(/Template/), 'floor_plan_unclear')
    expect(screen.getByLabelText(/Feedback for the operator/)).toHaveValue(
      'Please upload a plan that marks the preparation, storage and washing areas.',
    )
    expect(screen.getByLabelText(/About/)).toHaveValue('document:floor_plan')
    await userEvent.click(screen.getByRole('button', { name: 'Add feedback' }))
    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        'a1',
        expect.objectContaining({ target_type: 'document', document_type: 'floor_plan', template_key: 'floor_plan_unclear' }),
      ),
    )
  })

  it('offers Withdraw only on an unsent draft item, and Undo after withdrawing (US-039)', async () => {
    const draftItem = {
      id: 'f1',
      target_type: 'section' as const,
      section_key: 'business',
      document_type: null,
      target_label: 'Business details',
      message: 'Please confirm the UEN.',
      template_key: null,
      resolution: 'open' as const,
      raised_in_revision: 1,
      author_name: 'Rahim',
      created_at: '2026-09-19T01:00:00Z',
      released_to_operator_at: null,
      addressed_in_revision: null,
      resolved_at: null,
      can_undo: false,
    }
    const underReview = {
      ...view,
      status: 'under_review',
      status_label: 'Under Review',
      feedback_editable: true,
      feedback_locked_reason: null,
      actions: [],
      open_feedback_count: 1,
      feedback: [draftItem],
    }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(underReview)
    const withdrawn = {
      ...underReview,
      open_feedback_count: 0,
      feedback: [{ ...draftItem, resolution: 'withdrawn' as const, can_undo: true }],
    }
    const withdraw = vi.spyOn(api, 'withdrawFeedback').mockResolvedValue(withdrawn)
    const restore = vi.spyOn(api, 'restoreFeedback').mockResolvedValue(underReview)
    renderPage()
    expect(await screen.findByRole('button', { name: 'Withdraw' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark resolved' })).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Withdraw' }))
    await waitFor(() => expect(withdraw).toHaveBeenCalledWith('a1', 'f1'))
    await userEvent.click(await screen.findByRole('button', { name: 'Undo' }))
    await waitFor(() => expect(restore).toHaveBeenCalledWith('a1', 'f1'))
    expect(await screen.findByRole('button', { name: 'Withdraw' })).toBeInTheDocument()
  })
})
