import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import * as api from '@/api/applications'
import { AppError } from '@/api/client'
import * as visitApi from '@/api/siteVisit'
import type { SiteVisitOperator, SiteVisitProposal } from '@/api/siteVisit'
import { AppProviders } from '@/app/providers'
import { applicationView } from '@/test/fixtures'
import { ApplicationPage } from './ApplicationPage'
import { HistoryPage } from './HistoryPage'

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

function visit(over: Partial<SiteVisitOperator> = {}): SiteVisitOperator {
  return {
    visit_no: 1,
    status: 'proposed',
    status_label: 'Waiting for your reply',
    date: '2026-09-22',
    slot: 'morning',
    when: officerRound.when,
    note: 'Have the pest control contract on the premises.',
    reply_by: '2026-09-24',
    can_accept: true,
    can_counter: true,
    can_reschedule: false,
    earliest_date: '2026-09-23',
    rounds_left: 5,
    round_limit_reason: null,
    rounds: [officerRound],
    date_stands: false,
    is_current: true,
    ...over,
  }
}

const pendingVisit = (v: SiteVisitOperator | null) =>
  applicationView({
    id: 'a1',
    status_label: 'Pending Site Visit',
    status_tone: 'warning',
    status_explanation: 'A site visit is being arranged.',
    needs_operator_action: v?.status === 'proposed',
    site_visit: v,
  })

function renderPage(path = '/app/applications/a1') {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/applications/:id" element={<ApplicationPage />} />
          <Route path="/app/applications/:id/history" element={<HistoryPage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('site visit appointment, operator side (US-084)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('shows the proposal in the operator words, then accepts through a confirmation', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(pendingVisit(visit()))
    const accept = vi.spyOn(visitApi, 'acceptSiteVisit').mockResolvedValue(
      pendingVisit(
        visit({
          status: 'confirmed',
          status_label: 'Confirmed',
          can_accept: false,
          can_counter: false,
          can_reschedule: true,
          reply_by: null,
        }),
      ),
    )
    renderPage()
    expect(await screen.findByText('Waiting for your reply')).toBeInTheDocument()
    expect(screen.getByText(officerRound.when, { selector: 'p' })).toBeInTheDocument()
    expect(screen.getByText(/Proposed by the licensing officer on 19 Sep 2026\. Note: Have the pest control contract/)).toBeInTheDocument()
    expect(screen.getByText(/Reply by 24 Sep 2026/)).toBeInTheDocument()
    expect(screen.queryByText(/Waiting for the operator/)).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Accept this date' }))
    const dialog = await screen.findByRole('dialog', { name: 'Accept this visit date?' })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Accept the date' }))
    await waitFor(() => expect(accept).toHaveBeenCalledWith('a1'))
    expect(await screen.findByText('Confirmed')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Request a different date' })).toBeEnabled()
    expect(screen.queryByRole('button', { name: 'Accept this date' })).not.toBeInTheDocument()
  })

  it('a counter-proposal needs a date and a reason, then posts both', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(pendingVisit(visit()))
    const counter = vi.spyOn(visitApi, 'counterSiteVisit').mockResolvedValue(
      pendingVisit(
        visit({
          status: 'counter_proposed',
          status_label: 'Waiting for the officer',
          can_accept: false,
          can_counter: false,
          reply_by: null,
          rounds: [
            officerRound,
            {
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
            },
          ],
        }),
      ),
    )
    renderPage()
    const form = await screen.findByRole('form', { name: 'Propose this date' })
    expect(within(form).getByText("Monday to Friday, 23 Sep 2026 or later (two working days' notice).")).toBeInTheDocument()
    await userEvent.click(within(form).getByRole('button', { name: 'Propose this date' }))
    expect(await within(form).findByText('Choose a date.')).toBeInTheDocument()
    expect(within(form).getByText('Say why, in a sentence the officer will read.')).toBeInTheDocument()
    expect(counter).not.toHaveBeenCalled()
    await userEvent.type(within(form).getByLabelText(/Date/), '2026-09-24')
    await userEvent.click(within(form).getByRole('button', { name: /Afternoon/ }))
    await userEvent.type(within(form).getByLabelText(/Reason/), 'The shop is closed on Tuesdays.')
    await userEvent.click(within(form).getByRole('button', { name: 'Propose this date' }))
    await waitFor(() =>
      expect(counter).toHaveBeenCalledWith('a1', { date: '2026-09-24', slot: 'afternoon', reason: 'The shop is closed on Tuesdays.' }),
    )
    expect(await screen.findByText('Waiting for the officer')).toBeInTheDocument()
    expect(screen.getByText('You proposed Thursday 24 September 2026, afternoon (14:00 to 17:00)')).toBeInTheDocument()
    expect(screen.getByText('You proposed another date: Thursday 24 September 2026, afternoon (14:00 to 17:00)')).toBeInTheDocument()
  })

  it('checks the date and the reason together before sending (UAT run 5, F5)', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(pendingVisit(visit()))
    const counter = vi.spyOn(visitApi, 'counterSiteVisit')
    renderPage()
    const form = await screen.findByRole('form', { name: 'Propose this date' })
    await userEvent.type(within(form).getByLabelText(/Date/), '2026-09-22')
    await userEvent.click(within(form).getByRole('button', { name: 'Propose this date' }))
    // Too early and no reason: both messages at once, nothing sent.
    expect(await within(form).findByText('Choose a date at least 2 working days ahead.')).toBeInTheDocument()
    expect(within(form).getByText('Say why, in a sentence the officer will read.')).toBeInTheDocument()
    expect(counter).not.toHaveBeenCalled()
  })

  it('shows the server date rule under the field and reloads on a 409', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(pendingVisit(visit()))
    const counter = vi.spyOn(visitApi, 'counterSiteVisit').mockRejectedValueOnce(
      new AppError(422, {
        code: 'validation_failed',
        message: 'Some fields need attention.',
        details: { fields: { date: 'Choose a date at least two working days ahead.' } },
      }),
    )
    renderPage()
    const form = await screen.findByRole('form', { name: 'Propose this date' })
    // A date the form itself accepts (a weekday a week or so ahead), so the server's rule is the one shown.
    const ahead = new Date(Date.now() + 7 * 86_400_000)
    while (ahead.getUTCDay() === 0 || ahead.getUTCDay() === 6) ahead.setUTCDate(ahead.getUTCDate() + 1)
    await userEvent.type(within(form).getByLabelText(/Date/), ahead.toISOString().slice(0, 10))
    await userEvent.type(within(form).getByLabelText(/Reason/), 'Sooner please.')
    await userEvent.click(within(form).getByRole('button', { name: 'Propose this date' }))
    expect(await within(form).findByText('Choose a date at least two working days ahead.')).toBeInTheDocument()
    counter.mockRejectedValueOnce(new AppError(409, { code: 'conflict', message: 'There is no proposal waiting for your reply.' }))
    await userEvent.click(within(form).getByRole('button', { name: 'Propose this date' }))
    expect(await screen.findByText('This application changed since you opened it. Showing the latest.')).toBeInTheDocument()
  })

  it('at the round cap the counter form gives way to the reason', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(
      pendingVisit(
        visit({
          can_counter: false,
          rounds_left: 0,
          round_limit_reason: 'No more dates can be proposed for this visit. You can still accept this one.',
        }),
      ),
    )
    renderPage()
    expect(await screen.findByText('No more dates can be proposed for this visit. You can still accept this one.')).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: 'Propose this date' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Accept this date' })).toBeEnabled()
  })

  it('a confirmed visit can be moved with a reason before the date', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(
      pendingVisit(
        visit({
          status: 'confirmed',
          status_label: 'Confirmed',
          can_accept: false,
          can_counter: false,
          can_reschedule: true,
          reply_by: null,
        }),
      ),
    )
    const reschedule = vi
      .spyOn(visitApi, 'rescheduleSiteVisitAsOperator')
      .mockResolvedValue(
        pendingVisit(visit({ status: 'counter_proposed', status_label: 'Waiting for the officer', can_accept: false, can_counter: false })),
      )
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Request a different date' }))
    const form = screen.getByRole('form', { name: 'Send the request' })
    await userEvent.type(within(form).getByLabelText(/Date/), '2026-09-30')
    await userEvent.type(within(form).getByLabelText(/Reason/), 'Renovation that week.')
    await userEvent.click(within(form).getByRole('button', { name: 'Send the request' }))
    await waitFor(() =>
      expect(reschedule).toHaveBeenCalledWith('a1', { date: '2026-09-30', slot: 'morning', reason: 'Renovation that week.' }),
    )
  })

  it('the history page lists the rounds', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(pendingVisit(visit()))
    const formApi = await import('@/api/formSchema')
    const { formSchema } = await import('@/test/fixtures')
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
    renderPage('/app/applications/a1/history')
    expect(await screen.findByRole('heading', { name: 'Site visit' })).toBeInTheDocument()
    expect(screen.getByText('Visit 1 · 1 round')).toBeInTheDocument()
    expect(screen.getByText(`The officer proposed ${officerRound.when}`)).toBeInTheDocument()
  })

  it("a second visit is answered on the page even with the first visit's clarification on record (UAT run 5, F16)", async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue({
      ...pendingVisit(visit({ visit_no: 2 })),
      clarification: { can_respond: false, open_count: 0, answered_count: 0, round: 2 },
    })
    renderPage()
    expect(await screen.findByRole('button', { name: 'Accept this date' })).toBeInTheDocument()
  })

  it('the history keeps an earlier visit with its rounds and answers (UAT run 5, F18)', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue({
      ...pendingVisit(visit({ visit_no: 2 })),
      earlier_visits: [
        {
          visit_no: 1,
          site_visit: visit({
            visit_no: 1,
            status: 'done',
            status_label: 'Done',
            can_accept: false,
            can_counter: false,
            is_current: false,
          }),
          clarification: {
            application_id: 'a1',
            visit_no: 1,
            items: [
              {
                item_id: 'i1',
                key: 'sink_provided',
                title: 'At least one sink in the food preparation area',
                guidance: '',
                status: 'Clarified',
                round_no: 1,
                requests: [{ id: 'q1', round_no: 1, message: 'Show where a second sink will go.', released_at: '2026-09-24T04:43:00Z' }],
                responses: [
                  {
                    id: 'r1',
                    round_no: 1,
                    message: 'Second sink on the left wall.',
                    created_at: '2026-09-24T04:45:00Z',
                    sent_at: '2026-09-24T04:49:00Z',
                    attachments: [
                      {
                        id: 'f1',
                        original_filename: 'sink-plan.pdf',
                        content_type: 'application/pdf',
                        size_bytes: 1000,
                        uploaded_at: '2026-09-24T04:46:00Z',
                      },
                    ],
                  },
                ],
                can_respond: false,
              },
            ],
            open_count: 0,
            answered_count: 0,
            resolved_count: 1,
            round: 1,
            can_respond: false,
            can_send: false,
            storage: null,
          },
        },
      ],
    })
    const formApi = await import('@/api/formSchema')
    const { formSchema } = await import('@/test/fixtures')
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
    renderPage('/app/applications/a1/history')
    expect(await screen.findByText(/Visit 1 · round 1 · 1 item/)).toBeInTheDocument()
    expect(screen.getByText('Second sink on the left wall.')).toBeInTheDocument()
    expect(screen.getByText(/sink-plan\.pdf/)).toBeInTheDocument()
    expect(screen.getByText(/Visit 2 · 1 round/)).toBeInTheDocument()
    expect(screen.getByText(/Visit 1 · 1 round/)).toBeInTheDocument()
  })
})
