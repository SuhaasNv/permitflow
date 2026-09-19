import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as appsApi from '@/api/applications'
import { AppError } from '@/api/client'
import * as formApi from '@/api/formSchema'
import { AppProviders } from '@/app/providers'
import { applicationView, formSchema, respondingView, sectionView, slotView } from '@/test/fixtures'
import { HistoryPage } from './HistoryPage'
import { ReviewPage } from './ReviewPage'

function renderReview() {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={['/app/applications/app-1/review']}>
        <Routes>
          <Route path="/app/applications/:id/review" element={<ReviewPage />} />
          <Route path="/app/applications/:id/submitted" element={<div>SUBMITTED PAGE</div>} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

const draftBase = () =>
  applicationView({
    status_label: 'Draft',
    status_tone: 'neutral',
    can_edit: true,
    can_submit: true,
    revision_count: 0,
    revisions: [],
    sections: [sectionView('business', { editable: true }), sectionView('premises', { editable: true })],
    document_slots: [slotView('business_profile', { editable: true }), slotView('floor_plan', { editable: true })],
  })

describe('ReviewPage (submit readiness, FR-007)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
  })

  it('submits only after confirmation and then moves to the submitted page', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draftBase())
    const submit = vi.spyOn(appsApi, 'submitApplication').mockResolvedValue(applicationView())
    renderReview()
    expect(await screen.findByText('Ready to submit')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Submit application' }))
    expect(submit).not.toHaveBeenCalled()
    await userEvent.click(screen.getAllByRole('button', { name: 'Submit application' }).at(-1)!)
    await waitFor(() => expect(submit).toHaveBeenCalledWith('app-1'))
    expect(await screen.findByText('SUBMITTED PAGE')).toBeInTheDocument()
  })

  it('disables submission while the server says the application is incomplete', async () => {
    const incomplete = draftBase()
    incomplete.can_submit = false
    incomplete.completeness = { ...incomplete.completeness, percent: 50, is_complete: false, documents_present: 1, missing: ['Floor plan'] }
    incomplete.document_slots = [
      slotView('business_profile', { editable: true }),
      slotView('floor_plan', { editable: true, present: false, document: null }),
    ]
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(incomplete)
    renderReview()
    expect(await screen.findByText('Not ready yet')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit application' })).toBeDisabled()
  })

  it('warns about unresolved check results without blocking submission (AI-005)', async () => {
    const flagged = draftBase()
    const slot = slotView('floor_plan', { editable: true })
    slot.document!.verification = {
      ...slot.document!.verification!,
      status: 'issues_found',
      issues: [{ code: 'field_mismatch', severity: 'high', message: 'Address differs.' }],
    }
    flagged.document_slots = [slotView('business_profile', { editable: true }), slot]
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(flagged)
    renderReview()
    expect(await screen.findByText('1 document has unresolved check results')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Submit application' })).toBeEnabled()
  })

  it('shows the server message when submission is refused', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draftBase())
    vi.spyOn(appsApi, 'submitApplication').mockRejectedValue(
      new AppError(422, { code: 'incomplete', message: 'Upload the floor plan before submitting.' }),
    )
    renderReview()
    await userEvent.click(await screen.findByRole('button', { name: 'Submit application' }))
    await userEvent.click(screen.getAllByRole('button', { name: 'Submit application' }).at(-1)!)
    expect(await screen.findByText(/Upload the floor plan before submitting/)).toBeInTheDocument()
  })
})

describe('HistoryPage (US-019)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
  })

  it('lists revisions newest first, marks the current one, and compares with the previous on request', async () => {
    const view = respondingView({
      status_label: 'Pre-Site Resubmitted',
      revision_count: 2,
      revisions: [
        { number: 1, submitted_at: '2026-09-19T01:10:00Z' },
        { number: 2, submitted_at: '2026-09-19T03:00:00Z' },
      ],
      feedback: [{ ...respondingView().feedback[0], resolution: 'addressed', addressed_in_revision: 2 }],
      resubmit: null,
    })
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(view)
    const compare = vi.spyOn(appsApi, 'compareMyRevisions').mockResolvedValue({
      application_id: 'app-1',
      from_revision: 1,
      to_revision: 2,
      sections: [
        {
          key: 'premises',
          title: 'Premises',
          changed: true,
          fields: [{ key: 'postal_code', label: 'Postal code', old: '208787', new: '208788' }],
        },
        { key: 'business', title: 'Business details', changed: false, fields: [] },
      ],
      documents: [
        {
          type: 'floor_plan',
          label: 'Floor plan',
          change: 'replaced',
          old: { id: 'a', filename: 'old.pdf' },
          new: { id: 'b', filename: 'new.pdf' },
        },
      ],
      changed_section_count: 1,
      changed_document_count: 1,
    })
    render(
      <AppProviders>
        <MemoryRouter initialEntries={['/app/applications/app-1/history']}>
          <Routes>
            <Route path="/app/applications/:id/history" element={<HistoryPage />} />
          </Routes>
        </MemoryRouter>
      </AppProviders>,
    )
    const rows = await screen.findAllByText(/^Revision \d$/)
    expect(rows.map((r) => r.textContent)).toEqual(['Revision 2', 'Revision 1'])
    expect(screen.getByText('Current')).toBeInTheDocument()
    expect(screen.getByText(/Changed, awaiting review|Addressed/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'What changed from Revision 1' }))
    await waitFor(() => expect(compare).toHaveBeenCalledWith('app-1', 1, 2))
    expect(await screen.findByText('Postal code')).toBeInTheDocument()
    expect(screen.getByText('208788')).toBeInTheDocument()
    expect(screen.getByText('old.pdf')).toHaveClass('line-through')
    expect(screen.getByText((_, el) => el?.textContent === 'old.pdf → new.pdf')).toBeInTheDocument()
    expect(screen.queryByText('Business details')).not.toBeInTheDocument()
  })
})
