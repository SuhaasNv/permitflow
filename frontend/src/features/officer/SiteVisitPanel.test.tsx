import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import { AppError } from '@/api/client'
import * as formApi from '@/api/formSchema'
import * as api from '@/api/officer'
import * as visitApi from '@/api/siteVisit'
import type { SiteVisitOfficer, SiteVisitProposal } from '@/api/siteVisit'
import { AppProviders } from '@/app/providers'
import { formSchema, officerView } from '@/test/fixtures'
import { OfficerCasePage } from './CasePage'
import { shortWhen } from './SiteVisitPanel'

const officerRound: SiteVisitProposal = {
  round: 1,
  author_role: 'officer',
  author_name: 'Lim Hui Ling',
  date: '2026-09-22',
  slot: 'morning',
  when: 'Tuesday 22 September 2026, morning (09:00 to 12:00)',
  reason: null,
  outcome: 'pending',
  created_at: '2026-09-19T08:02:00Z',
  decided_at: null,
}

const counterRound: SiteVisitProposal = {
  round: 2,
  author_role: 'operator',
  author_name: 'Tan Wei Ling',
  date: '2026-09-24',
  slot: 'afternoon',
  when: 'Thursday 24 September 2026, afternoon (14:00 to 17:00)',
  reason: 'The shop is closed on Tuesdays.',
  outcome: 'pending',
  created_at: '2026-09-20T01:40:00Z',
  decided_at: null,
}

function visit(over: Partial<SiteVisitOfficer> = {}): SiteVisitOfficer {
  return {
    visit_no: 1,
    status: 'proposed',
    status_label: 'Waiting for the operator',
    date: '2026-09-22',
    slot: 'morning',
    when: officerRound.when,
    note: null,
    reply_deadline: '2026-09-24',
    can_confirm_without_reply: false,
    confirm_without_reply_reason: 'Available from 24 Sep 2026 if the operator has not replied.',
    original: officerRound,
    counter: null,
    can_reschedule: false,
    rounds_left: 5,
    round_limit_reason: null,
    rounds: [officerRound],
    ...over,
  }
}

const underReview = officerView({
  id: 'a1',
  status: 'under_review',
  status_label: 'Under Review',
  actions: [
    { target: 'site_visit_scheduled', label: 'Mark site visit scheduled', enabled: true, reason: null, requires_note: false },
    { target: 'rejected', label: 'Reject', enabled: true, reason: null, requires_note: true },
  ],
  version: 7,
})

const scheduled = (v: SiteVisitOfficer | null) =>
  officerView({
    id: 'a1',
    status: 'site_visit_scheduled',
    status_label: 'Site Visit Scheduled',
    actions: [
      {
        target: 'site_visit_done',
        label: 'Mark site visit done',
        enabled: v?.status === 'confirmed',
        reason: v?.status === 'confirmed' ? null : 'Confirm the visit date with the operator first.',
        requires_note: false,
      },
      { target: 'rejected', label: 'Reject', enabled: true, reason: null, requires_note: true },
    ],
    site_visit: v,
    version: 8,
  })

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

describe('site visit appointment, officer side (US-084)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
    vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([])
  })

  it('Mark site visit scheduled opens the proposal dialog and posts date, slot, note and version', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(underReview)
    const transition = vi.spyOn(api, 'transitionApplication')
    const propose = vi.spyOn(visitApi, 'proposeSiteVisit').mockResolvedValue(scheduled(visit()))
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Mark site visit scheduled' }))
    const dialog = await screen.findByRole('dialog', { name: 'Propose a site visit?' })
    expect(within(dialog).getByText(/The case moves to Site Visit Scheduled now/)).toBeInTheDocument()
    // no date yet: the dialog says so and nothing is sent
    await userEvent.click(within(dialog).getByRole('button', { name: 'Propose visit' }))
    expect(await within(dialog).findByText('Choose a date.')).toBeInTheDocument()
    expect(propose).not.toHaveBeenCalled()
    const date = within(dialog).getByLabelText(/Date/)
    await userEvent.type(date, '2026-09-22')
    await userEvent.click(within(dialog).getByRole('button', { name: /Afternoon/ }))
    await userEvent.type(within(dialog).getByLabelText(/Note for the operator/), 'Pest control contract on site.')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Propose visit' }))
    await waitFor(() =>
      expect(propose).toHaveBeenCalledWith('a1', {
        date: '2026-09-22',
        slot: 'afternoon',
        note: 'Pest control contract on site.',
        expected_version: 7,
      }),
    )
    expect(transition).not.toHaveBeenCalled()
    expect(await screen.findByText('Waiting for the operator')).toBeInTheDocument()
    expect(screen.getByText('The operator has until 24 Sep 2026 to reply.')).toBeInTheDocument()
  })

  it('shows the server date rule under the field on a 422', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(underReview)
    const { AppError } = await import('@/api/client')
    vi.spyOn(visitApi, 'proposeSiteVisit').mockRejectedValue(
      new AppError(422, {
        code: 'validation_failed',
        message: 'Some fields need attention.',
        details: { fields: { date: 'Choose a working day (Monday to Friday).' } },
      }),
    )
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Mark site visit scheduled' }))
    const dialog = await screen.findByRole('dialog', { name: 'Propose a site visit?' })
    await userEvent.type(within(dialog).getByLabelText(/Date/), '2026-09-26')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Propose visit' }))
    expect(await within(dialog).findByText('Choose a working day (Monday to Friday).')).toBeInTheDocument()
  })

  it('on a counter-proposal offers accept, keep and a third date; accept posts the decision', async () => {
    const countered = visit({
      status: 'counter_proposed',
      status_label: 'Waiting for you',
      counter: counterRound,
      rounds: [officerRound, counterRound],
      rounds_left: 4,
    })
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(scheduled(countered))
    const decide = vi.spyOn(visitApi, 'decideSiteVisit').mockResolvedValue(
      scheduled(
        visit({
          status: 'confirmed',
          status_label: 'Confirmed',
          date: '2026-09-24',
          slot: 'afternoon',
          when: counterRound.when,
          can_reschedule: true,
          rounds: [
            { ...officerRound, outcome: 'declined' },
            { ...counterRound, outcome: 'accepted' },
          ],
        }),
      ),
    )
    renderPage()
    expect(await screen.findByText('Waiting for you')).toBeInTheDocument()
    expect(screen.getByText(`Operator proposes ${counterRound.when}`)).toBeInTheDocument()
    expect(screen.getByText('"The shop is closed on Tuesdays."')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Keep Tue 22 Sep, morning' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Propose another date' })).toBeEnabled()
    // the done step stays behind the confirmation
    expect(screen.getByRole('button', { name: 'Mark site visit done' })).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: 'Accept Thu 24 Sep, afternoon' }))
    await waitFor(() => expect(decide).toHaveBeenCalledWith('a1', { action: 'accept_operator' }))
    expect(await screen.findByText('Confirmed')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark site visit done' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Request a different date' })).toBeEnabled()
  })

  it('a 409 on a stale decision reloads the case and shows the latest, not the server reason', async () => {
    const countered = visit({
      status: 'counter_proposed',
      status_label: 'Waiting for you',
      counter: counterRound,
      rounds: [officerRound, counterRound],
      rounds_left: 4,
    })
    const settled = scheduled(
      visit({
        status: 'confirmed',
        status_label: 'Confirmed',
        date: '2026-09-24',
        slot: 'afternoon',
        when: counterRound.when,
        can_reschedule: true,
        rounds: [
          { ...officerRound, outcome: 'declined' },
          { ...counterRound, outcome: 'accepted' },
        ],
      }),
    )
    // First load: the counter-proposal is still open. Second load (after the 409): another device accepted it.
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValueOnce(scheduled(countered)).mockResolvedValue(settled)
    const decide = vi
      .spyOn(visitApi, 'decideSiteVisit')
      .mockRejectedValue(new AppError(409, { code: 'conflict', message: 'The operator has not proposed another date.' }))
    renderPage()
    expect(await screen.findByText('Waiting for you')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Keep Tue 22 Sep, morning' }))
    await waitFor(() => expect(decide).toHaveBeenCalledWith('a1', { action: 'keep_original' }))
    expect(await screen.findByText('This application changed since you opened it. Showing the latest.')).toBeInTheDocument()
    expect(screen.queryByText('The operator has not proposed another date.')).not.toBeInTheDocument()
    expect(await screen.findByText('Confirmed')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Keep Tue 22 Sep, morning' })).not.toBeInTheDocument()
  })

  it('a third date goes through the inline form with action propose', async () => {
    const countered = visit({
      status: 'counter_proposed',
      status_label: 'Waiting for you',
      counter: counterRound,
      rounds: [officerRound, counterRound],
    })
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(scheduled(countered))
    const decide = vi.spyOn(visitApi, 'decideSiteVisit').mockResolvedValue(scheduled(visit()))
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Propose another date' }))
    const form = screen.getByRole('form', { name: 'Propose another date' })
    await userEvent.type(within(form).getByLabelText(/Date/), '2026-09-28')
    await userEvent.click(within(form).getByRole('button', { name: 'Propose this date' }))
    await waitFor(() => expect(decide).toHaveBeenCalledWith('a1', { action: 'propose', date: '2026-09-28', slot: 'morning', note: null }))
  })

  it('at the round cap the third-date button is disabled with the reason; accept and keep remain', async () => {
    const capped = visit({
      status: 'counter_proposed',
      status_label: 'Waiting for you',
      counter: counterRound,
      rounds: [officerRound, counterRound],
      rounds_left: 0,
      round_limit_reason: "No more dates can be proposed for this visit: accept the operator's date or keep the one on the table.",
    })
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(scheduled(capped))
    renderPage()
    expect(await screen.findByRole('button', { name: 'Propose another date' })).toBeDisabled()
    expect(screen.getByText(/No more dates can be proposed for this visit/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept Thu 24 Sep, afternoon' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Keep Tue 22 Sep, morning' })).toBeEnabled()
  })

  it('confirm without a reply is disabled until the deadline, then posts', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(scheduled(visit()))
    const { unmount } = renderPage()
    expect(await screen.findByRole('button', { name: 'Confirm without a reply' })).toBeDisabled()
    expect(screen.getByText('Available from 24 Sep 2026 if the operator has not replied.')).toBeInTheDocument()
    unmount()

    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(
      scheduled(visit({ can_confirm_without_reply: true, confirm_without_reply_reason: null })),
    )
    const confirm = vi
      .spyOn(visitApi, 'confirmSiteVisitWithoutReply')
      .mockResolvedValue(scheduled(visit({ status: 'confirmed', status_label: 'Confirmed', can_reschedule: true })))
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Confirm without a reply' }))
    await waitFor(() => expect(confirm).toHaveBeenCalledWith('a1'))
    expect(await screen.findByText('Confirmed')).toBeInTheDocument()
  })

  it('a legacy case in Site Visit Scheduled without a visit offers Propose a visit date', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(scheduled(null))
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Propose a visit date' }))
    const dialog = await screen.findByRole('dialog', { name: 'Propose a site visit?' })
    expect(within(dialog).queryByText(/moves to Site Visit Scheduled now/)).not.toBeInTheDocument()
  })

  it('shortWhen keeps the weekday, day, month and slot', () => {
    expect(shortWhen('Tuesday 22 September 2026, morning (09:00 to 12:00)')).toBe('Tue 22 Sep, morning')
    expect(shortWhen('odd')).toBe('odd')
  })
})
