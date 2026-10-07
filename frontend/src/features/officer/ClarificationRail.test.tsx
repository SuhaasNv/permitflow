import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import type { ClarificationOfficerView, ClarificationThread } from '@/api/clarification'
import * as formApi from '@/api/formSchema'
import * as api from '@/api/officer'
import { AppProviders } from '@/app/providers'
import { formSchema, officerView } from '@/test/fixtures'
import { OfficerCasePage } from './CasePage'

function thread(over: Partial<ClarificationThread> = {}): ClarificationThread {
  return {
    item_id: 'i1',
    key: 'floor_trap_graded',
    title: 'Floor trap in the food preparation area',
    result: 'unsatisfactory',
    comment: 'Trap present but the floor slopes away from it.',
    status: 'answered',
    round_no: 1,
    requests: [
      {
        id: 'q1',
        round_no: 1,
        message: 'Trap present but the floor slopes away from it.',
        author_name: 'Rahim bin Abdullah',
        created_at: '2026-09-22T08:40:00Z',
        released_at: '2026-09-22T08:40:00Z',
        withdrawn_at: null,
        response: {
          id: 'r1',
          round_no: 1,
          message: 'Regraded on 24 Sep; water now runs to the trap.',
          created_at: '2026-09-25T01:00:00Z',
          sent_at: '2026-09-25T01:12:00Z',
          attachments: [
            {
              id: 'a1',
              original_filename: 'floor-trap.jpg',
              content_type: 'image/jpeg',
              size_bytes: 1_800_000,
              uploaded_at: '2026-09-25T01:05:00Z',
            },
          ],
        },
      },
    ],
    can_resolve: true,
    can_reopen: true,
    can_withdraw: false,
    pending_release: false,
    ...over,
  }
}

const clarification: ClarificationOfficerView = {
  visit_no: 1,
  round: 1,
  open_count: 0,
  answered_count: 1,
  resolved_count: 0,
  withdrawn_count: 0,
  unreleased_count: 0,
  turn: 'Round 1, your turn',
  items: [thread()],
}

const resubmitted = officerView({
  id: 'a1',
  status: 'post_site_clarification_resubmitted',
  status_label: 'Post-Site Clarification Resubmitted',
  actions: [
    {
      target: 'pending_post_site_resubmission',
      label: 'Request another round',
      enabled: false,
      reason: 'At least one item must still need clarification.',
      requires_note: false,
    },
    {
      target: 'pending_approval',
      label: 'Route to approval',
      enabled: false,
      reason: 'Mark every clarification item clarified or withdraw it before routing to approval.',
      requires_note: false,
    },
    { target: 'rejected', label: 'Reject', enabled: true, reason: null, requires_note: true },
  ],
  clarification,
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

describe('clarification rail (US-066)', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
    vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([])
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(resubmitted)
  })

  it('shows the thread with the finding on top, the answer and its file, and the two decisions', async () => {
    renderPage()
    const rail = (await screen.findByRole('heading', { name: 'Clarification' })).closest('section')!
    expect(within(rail).getByText('Round 1, your turn.')).toBeInTheDocument()
    expect(within(rail).getByText('0 open · 1 answered · 0 clarified')).toBeInTheDocument()
    expect(within(rail).getByText('Trap present but the floor slopes away from it.', { selector: 'p' })).toBeInTheDocument()
    expect(within(rail).getByText('Result: Unsatisfactory')).toBeInTheDocument()
    expect(within(rail).getByText('Tan Wei Ling answered')).toBeInTheDocument()
    expect(within(rail).getByText('Regraded on 24 Sep; water now runs to the trap.')).toBeInTheDocument()
    expect(within(rail).getByRole('button', { name: /floor-trap.jpg/ })).toBeInTheDocument()
    expect(within(rail).getByRole('button', { name: 'Mark clarified' })).toBeInTheDocument()
    expect(within(rail).getByRole('button', { name: 'Still needs clarification' })).toBeInTheDocument()
    expect(within(rail).queryByRole('button', { name: 'Withdraw' })).not.toBeInTheDocument()
    // the feedback panel gives way to the rail in the post-site states
    expect(screen.queryByRole('heading', { name: 'Feedback' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Route to approval' })).toBeDisabled()
  })

  it('a 409 on Mark clarified (another officer decided it first) reloads the case with the shared sentence', async () => {
    const { AppError } = await import('@/api/client')
    const decided = {
      ...resubmitted,
      clarification: {
        ...clarification,
        answered_count: 0,
        resolved_count: 1,
        items: [thread({ status: 'resolved', can_resolve: false, can_reopen: false })],
      },
    }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValueOnce(resubmitted).mockResolvedValue(decided)
    const resolve = vi
      .spyOn(api, 'resolveClarification')
      .mockRejectedValue(new AppError(409, { code: 'conflict', message: 'Only an answered item can be marked clarified.' }))
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Mark clarified' }))
    await waitFor(() => expect(resolve).toHaveBeenCalledWith('a1', 'i1'))
    expect(await screen.findByText('This application changed since you opened it. Showing the latest.')).toBeInTheDocument()
    expect(screen.queryByText('Only an answered item can be marked clarified.')).not.toBeInTheDocument()
    expect(await screen.findByText('0 open · 0 answered · 1 clarified')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark clarified' })).not.toBeInTheDocument()
  })

  it('Mark clarified posts the resolve; Still needs clarification drafts a question and shows Not sent yet', async () => {
    const resolve = vi.spyOn(api, 'resolveClarification').mockResolvedValue({
      ...resubmitted,
      clarification: {
        ...clarification,
        answered_count: 0,
        resolved_count: 1,
        items: [thread({ status: 'resolved', can_resolve: false, can_reopen: false })],
      },
    })
    const { unmount } = renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Mark clarified' }))
    await waitFor(() => expect(resolve).toHaveBeenCalledWith('a1', 'i1'))
    expect(await screen.findByText('0 open · 0 answered · 1 clarified')).toBeInTheDocument()
    unmount()

    const reopen = vi.spyOn(api, 'reopenClarification').mockResolvedValue({
      ...resubmitted,
      clarification: {
        ...clarification,
        open_count: 1,
        answered_count: 0,
        unreleased_count: 1,
        items: [
          thread({
            status: 'open',
            round_no: 2,
            can_resolve: false,
            can_reopen: false,
            can_withdraw: true,
            pending_release: true,
            requests: [
              ...thread().requests,
              {
                id: 'q2',
                round_no: 2,
                message: 'Please attach a photo of the drainage test.',
                author_name: 'Rahim bin Abdullah',
                created_at: '2026-09-25T06:00:00Z',
                released_at: null,
                withdrawn_at: null,
                response: null,
              },
            ],
          }),
        ],
      },
    })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Still needs clarification' }))
    const form = screen.getByRole('form', { name: 'Still needs clarification' })
    await userEvent.click(within(form).getByRole('button', { name: 'Draft the question' }))
    expect(await within(form).findByText('Write what is still unclear; the operator reads it.')).toBeInTheDocument()
    await userEvent.type(within(form).getByLabelText(/What is still unclear/), 'Please attach a photo of the drainage test.')
    await userEvent.click(within(form).getByRole('button', { name: 'Draft the question' }))
    await waitFor(() => expect(reopen).toHaveBeenCalledWith('a1', 'i1', 'Please attach a photo of the drainage test.'))
    expect(await screen.findByText('Not sent yet')).toBeInTheDocument()
    expect(screen.getByText('1 question waits for Request another round.', { exact: false })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Withdraw' })).toBeInTheDocument()
  })

  it('a withdrawn question can be undone from the toast (UAT run 5, F19)', async () => {
    const open = thread({ status: 'open', can_resolve: false, can_reopen: false, can_withdraw: true })
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...resubmitted,
      status: 'awaiting_post_site_clarification',
      clarification: { ...clarification, open_count: 1, answered_count: 0, items: [open] },
    })
    const withdrawn = vi
      .spyOn(api, 'withdrawClarification')
      .mockResolvedValue({
        ...resubmitted,
        clarification: { ...clarification, items: [{ ...open, status: 'withdrawn', can_withdraw: false }] },
      })
    const restore = vi
      .spyOn(api, 'restoreClarification')
      .mockResolvedValue({ ...resubmitted, clarification: { ...clarification, items: [open] } })
    renderPage()
    await userEvent.click(await screen.findByRole('button', { name: 'Withdraw' }))
    await waitFor(() => expect(withdrawn).toHaveBeenCalledWith('a1', 'i1'))
    await userEvent.click(await screen.findByRole('button', { name: 'Undo' }))
    await waitFor(() => expect(restore).toHaveBeenCalledWith('a1', 'i1'))
    expect(await screen.findByText('The question is open again.')).toBeInTheDocument()
  })

  it('back in review after a visit: the feedback panel returns and the visit is listed as history (UAT run 5, F15, F18)', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...resubmitted,
      status: 'under_review',
      status_label: 'Under Review',
      feedback_editable: true,
      feedback_locked_reason: null,
      clarification: null,
      site_visit: null,
      checklist: null,
      actions: [
        {
          target: 'pending_pre_site_resubmission',
          label: 'Request resubmission',
          enabled: false,
          reason: 'At least one open feedback item is required.',
          requires_note: false,
        },
      ],
      earlier_visits: [
        {
          visit_no: 1,
          site_visit: null,
          checklist: {
            visit_no: 1,
            status: 'submitted',
            version: 5,
            counts: { total: 18, assessed: 18, flagged: 3, unsatisfactory: 4, not_applicable: 1, missing_comments: 0 },
            updated_at: '2026-09-24T04:43:00Z',
            submitted_at: '2026-09-24T04:43:00Z',
          },
          clarification: { ...clarification, items: [thread({ status: 'resolved', can_resolve: false, can_reopen: false })] },
        },
      ],
    })
    renderPage()
    expect(await screen.findByRole('button', { name: 'Add feedback' })).toBeInTheDocument()
    const earlier = screen.getByRole('heading', { name: 'Earlier visits' }).closest('section')!
    expect(within(earlier).getByText('18 of 18 assessed, 3 flagged')).toBeInTheDocument()
    expect(within(earlier).getByRole('link', { name: 'View visit 1 checklist' })).toHaveAttribute(
      'href',
      '/officer/applications/a1/checklist?visit=1',
    )
    // The first visit's thread is there, read-only.
    expect(within(earlier).getByText('Regraded on 24 Sep; water now runs to the trap.')).toBeInTheDocument()
    expect(within(earlier).queryByRole('button', { name: 'Mark clarified' })).not.toBeInTheDocument()
  })
})
