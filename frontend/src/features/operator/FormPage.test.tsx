import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as appsApi from '@/api/applications'
import { AppError } from '@/api/client'
import * as formApi from '@/api/formSchema'
import * as sectionsApi from '@/api/sections'
import { AppProviders } from '@/app/providers'
import { applicationView, formSchema, respondingView, sectionView, slotView } from '@/test/fixtures'
import { FormPage } from './FormPage'

function renderAt(path: string) {
  const router = createMemoryRouter(
    [
      { path: '/app/applications/:id/form/:sectionKey?', element: <FormPage /> },
      { path: '/app/applications/:id', element: <div>APPLICATION PAGE</div> },
      { path: '/app/applications/:id/documents', element: <div>DOCUMENTS PAGE</div> },
    ],
    { initialEntries: [path] },
  )
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  )
  return router
}

describe('FormPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
  })

  it('opens the first incomplete section of a draft and "Save and continue" moves to the next one', async () => {
    const draft = applicationView({
      status_label: 'Draft',
      status_tone: 'neutral',
      can_edit: true,
      revision_count: 0,
      revisions: [],
      sections: [
        sectionView('business', { editable: true }),
        sectionView('premises', { editable: true, complete: false, started: false, data: {} }),
      ],
    })
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(draft)
    const update = vi.spyOn(sectionsApi, 'updateSection').mockResolvedValue(draft)
    const router = renderAt('/app/applications/app-1/form')
    expect(await screen.findByRole('heading', { name: 'Premises' })).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText(/Premises address/), '10 Jalan Besar #01-12')
    await userEvent.type(screen.getByLabelText(/Postal code/), '208787')
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    await waitFor(() => expect(update).toHaveBeenCalledWith('app-1', 'premises', expect.objectContaining({ postal_code: '208787' })))
    await waitFor(() => expect(router.state.location.pathname).toBe('/app/applications/app-1/documents'))
  })

  it('in respond mode locks the unflagged section, walks only flagged targets and ends at Resubmit', async () => {
    const view = respondingView()
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(view)
    vi.spyOn(sectionsApi, 'updateSection').mockResolvedValue(view)
    const router = renderAt('/app/applications/app-1/form')

    // Lands on the flagged section, not the first one.
    expect(await screen.findByRole('heading', { name: 'Premises' })).toBeInTheDocument()
    expect(screen.getByText(/Responding to feedback: 1 flagged item needs your changes/)).toBeInTheDocument()
    expect(screen.getByTitle('The licensing officer did not ask for changes here.')).toHaveTextContent('Business details')
    // The primary action names the destination: nothing else is flagged, so it goes straight to Resubmit.
    expect(screen.getByRole('button', { name: 'Save and go to resubmit' })).toBeInTheDocument()

    await userEvent.clear(screen.getByLabelText(/Postal code/))
    await userEvent.type(screen.getByLabelText(/Postal code/), '208788')
    await userEvent.click(screen.getByRole('button', { name: 'Save and go to resubmit' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/app/applications/app-1'))
  })

  it('shows a locked, read-only section when the URL names one the officer did not flag', async () => {
    vi.spyOn(appsApi, 'getApplication').mockResolvedValue(respondingView())
    renderAt('/app/applications/app-1/form/business')
    expect(await screen.findByRole('heading', { name: 'Business details' })).toBeInTheDocument()
    expect(screen.getByText(/did not ask for changes here/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save section' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Save and (continue|go to)/ })).not.toBeInTheDocument()
    expect(screen.getByLabelText(/Business name/)).toBeDisabled()
  })

  it('refetches and locks when a save is refused because the round closed (409)', async () => {
    const before = respondingView()
    const after = applicationView({ status_label: 'Under Review', status_tone: 'info' })
    const get = vi.spyOn(appsApi, 'getApplication').mockResolvedValueOnce(before).mockResolvedValue(after)
    vi.spyOn(sectionsApi, 'updateSection').mockRejectedValue(
      new AppError(409, { code: 'not_editable', message: 'This application changed since you opened it.' }),
    )
    renderAt('/app/applications/app-1/form/premises')
    expect(await screen.findByRole('heading', { name: 'Premises' })).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText(/Postal code/))
    await userEvent.type(screen.getByLabelText(/Postal code/), '208788')
    await userEvent.click(screen.getByRole('button', { name: 'Save and go to resubmit' }))
    expect(await screen.findByText(/This application changed since you opened it/)).toBeInTheDocument()
    await waitFor(() => expect(get.mock.calls.length).toBeGreaterThan(1))
  })

  it('keeps the form and the typed text when a background refetch fails', async () => {
    // A running check makes the page poll every 2 s; the poll then fails with a 429 (not retried).
    const checking = slotView('floor_plan', {
      document: { ...slotView('floor_plan').document!, verification: { ...slotView('floor_plan').document!.verification!, status: 'running', requested_at: new Date().toISOString(), finished_at: null } },
    })
    const draft = applicationView({
      status_label: 'Draft',
      status_tone: 'neutral',
      can_edit: true,
      revision_count: 0,
      revisions: [],
      sections: [sectionView('business', { editable: true }), sectionView('premises', { editable: true, data: {} })],
      document_slots: [slotView('business_profile'), checking],
    })
    const get = vi
      .spyOn(appsApi, 'getApplication')
      .mockResolvedValueOnce(draft)
      .mockRejectedValue(new AppError(429, { code: 'rate_limited', message: 'Too many requests.' }))
    renderAt('/app/applications/app-1/form/premises')
    expect(await screen.findByRole('heading', { name: 'Premises' })).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/Postal code/), '208788')
    await waitFor(() => expect(get.mock.calls.length).toBeGreaterThan(1), { timeout: 5_000 })
    expect(screen.getByRole('heading', { name: 'Premises' })).toBeInTheDocument()
    expect(screen.getByLabelText(/Postal code/)).toHaveValue('208788')
    expect(screen.queryByRole('button', { name: /Try again/ })).not.toBeInTheDocument()
  })

  it('shows Not found for an unknown application', async () => {
    vi.spyOn(appsApi, 'getApplication').mockRejectedValue(new AppError(404, { code: 'not_found', message: 'Application not found.' }))
    renderAt('/app/applications/nope/form')
    expect(await screen.findByText(/Back to my applications/)).toBeInTheDocument()
  })
})
