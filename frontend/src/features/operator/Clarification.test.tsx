import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import * as api from '@/api/applications'
import { AppError } from '@/api/client'
import * as clarApi from '@/api/clarification'
import type { ClarificationView } from '@/api/clarification'
import { AppProviders } from '@/app/providers'
import { applicationView } from '@/test/fixtures'
import { ApplicationPage } from './ApplicationPage'
import { ClarificationPage } from './ClarificationPage'

const afterVisit = applicationView({
  id: 'a1',
  status_label: 'Pending Post-Site Clarification',
  status_tone: 'warning',
  status_explanation: 'The licensing officer needs more information on 2 items after the site visit.',
  needs_operator_action: true,
  clarification: { can_respond: true, open_count: 2, answered_count: 0, round: 1 },
})

const view: ClarificationView = {
  application_id: 'a1',
  visit_no: 1,
  items: [
    {
      item_id: 'i1',
      key: 'floor_trap_graded',
      title: 'Floor trap in the food preparation area',
      guidance: 'Kitchen floor graded to the trap',
      status: 'Waiting for your response',
      round_no: 1,
      requests: [{ id: 'q1', round_no: 1, message: 'Please send a photo of the regraded floor.', released_at: '2026-09-24T08:40:00Z' }],
      responses: [],
      can_respond: true,
    },
    {
      item_id: 'i2',
      key: 'coved_edges',
      title: 'Edge between wall and floor coved',
      guidance: '',
      status: 'Clarified',
      round_no: 1,
      requests: [{ id: 'q2', round_no: 1, message: 'Confirm the coving work.', released_at: '2026-09-24T08:40:00Z' }],
      responses: [],
      can_respond: false,
    },
  ],
  open_count: 1,
  answered_count: 0,
  resolved_count: 1,
  round: 1,
  can_respond: true,
  can_send: false,
  storage: { used_bytes: 3 * 1024 * 1024, budget_bytes: 150 * 1024 * 1024, remaining_bytes: 147 * 1024 * 1024 },
}

function renderAt(path: string) {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/app/applications/:id" element={<ApplicationPage />} />
          <Route path="/app/applications/:id/clarification" element={<ClarificationPage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('clarification after the site visit, operator side (US-064)', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('the application page carries the notice with the primary action and no edit links', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    renderAt('/app/applications/a1')
    expect(
      await screen.findByRole('heading', { name: 'The licensing officer needs more information on 2 items after the site visit' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Respond to clarification (2 items)' })).toHaveAttribute(
      'href',
      '/app/applications/a1/clarification',
    )
    expect(screen.queryByRole('link', { name: /Continue application|Start application/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Waiting for the operator')).not.toBeInTheDocument()
  })

  it('the notice reads differently once every item is answered', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue({
      ...afterVisit,
      needs_operator_action: false,
      clarification: { can_respond: false, open_count: 0, answered_count: 2, round: 1 },
    })
    renderAt('/app/applications/a1')
    expect(await screen.findByRole('heading', { name: 'Your answers were sent to the licensing office' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'View clarification' })).toBeInTheDocument()
  })

  it('the clarification page lists only the flagged items, the officer question first, with operator words', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(view)
    renderAt('/app/applications/a1/clarification')
    expect(await screen.findByText('Round 1: 1 of 2 items need your response')).toBeInTheDocument()
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(within(items[0]!).getByRole('heading', { name: 'Floor trap in the food preparation area' })).toBeInTheDocument()
    expect(within(items[0]!).getByText('Please send a photo of the regraded floor.')).toBeInTheDocument()
    expect(within(items[0]!).getByText('Waiting for your response')).toBeInTheDocument()
    expect(within(items[0]!).getByLabelText(/Your answer/)).toBeInTheDocument()
    expect(within(items[1]!).getByText('Clarified')).toBeInTheDocument()
    expect(within(items[1]!).queryByLabelText(/Your answer/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Unsatisfactory|Satisfactory/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send responses' })).toBeDisabled()
  })

  it('an answer saves on blur, files attach and remove, and the send needs every item answered (US-065)', async () => {
    const userEvent = (await import('@testing-library/user-event')).default
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    const onlyOpen: ClarificationView = { ...view, items: [view.items[0]!], resolved_count: 0 }
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(onlyOpen)
    const answered: ClarificationView = {
      ...onlyOpen,
      can_send: true,
      items: [
        {
          ...onlyOpen.items[0]!,
          responses: [
            { id: 'r1', round_no: 1, message: 'Regraded on 23 Sep.', created_at: '2026-09-25T01:00:00Z', sent_at: null, attachments: [] },
          ],
        },
      ],
    }
    const respond = vi.spyOn(clarApi, 'respondToClarification').mockResolvedValue(answered)
    const withFile: ClarificationView = {
      ...answered,
      items: [
        {
          ...answered.items[0]!,
          responses: [
            {
              ...answered.items[0]!.responses[0]!,
              attachments: [
                {
                  id: 'att1',
                  original_filename: 'floor.jpg',
                  content_type: 'image/jpeg',
                  size_bytes: 2048,
                  uploaded_at: '2026-09-25T01:01:00Z',
                },
              ],
            },
          ],
        },
      ],
    }
    const attach = vi.spyOn(clarApi, 'attachToResponse').mockResolvedValue({ view: withFile, unchanged: false })
    const remove = vi.spyOn(clarApi, 'removeAttachment').mockResolvedValue(answered)
    const sendSpy = vi.spyOn(clarApi, 'sendClarifications').mockResolvedValue({
      ...answered,
      open_count: 0,
      answered_count: 1,
      can_respond: false,
      can_send: false,
      items: [
        {
          ...answered.items[0]!,
          status: 'Sent',
          can_respond: false,
          responses: [{ ...answered.items[0]!.responses[0]!, sent_at: '2026-09-25T01:05:00Z' }],
        },
      ],
    })
    renderAt('/app/applications/a1/clarification')
    const field = await screen.findByLabelText(/Your answer/)
    expect(screen.getByRole('button', { name: 'Send responses' })).toBeDisabled()
    expect(screen.getByText('Write your answer first; files can be attached once it is saved.')).toBeInTheDocument()
    await userEvent.type(field, 'Regraded on 23 Sep.')
    await userEvent.tab()
    await waitFor(() => expect(respond).toHaveBeenCalledWith('a1', 'i1', 'Regraded on 23 Sep.'))
    expect(await screen.findByRole('button', { name: 'Choose a file' })).toBeInTheDocument()
    // the room left is stated beside the file picker (US-085)
    expect(screen.getByTestId('storage-room')).toHaveTextContent("147 MB of the application's 150 MB storage room is left.")
    expect(screen.getByRole('button', { name: 'Send responses' })).toBeEnabled()
    const input = document.querySelector('input[type=file][multiple]') as HTMLInputElement
    await userEvent.upload(input, new File(['x'], 'floor.jpg', { type: 'image/jpeg' }))
    await waitFor(() => expect(attach).toHaveBeenCalledTimes(1))
    expect(await screen.findByRole('button', { name: 'floor.jpg' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Remove' }))
    await waitFor(() => expect(remove).toHaveBeenCalledWith('a1', 'r1', 'att1'))
    await userEvent.click(screen.getByRole('button', { name: 'Send responses' }))
    await userEvent.click(
      within(await screen.findByRole('dialog', { name: 'Send your answers?' })).getByRole('button', { name: 'Send responses' }),
    )
    await waitFor(() => expect(sendSpy).toHaveBeenCalledWith('a1'))
    expect(await screen.findByText('Sent')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Send responses' })).not.toBeInTheDocument()
  })

  it('keeps an answer through a lost connection and saves it on the retry (US-087)', async () => {
    const userEvent = (await import('@testing-library/user-event')).default
    const { AppError } = await import('@/api/client')
    const { retryDelay } = await import('@/lib/connection')
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    const onlyOpen: ClarificationView = { ...view, items: [view.items[0]!], resolved_count: 0 }
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(onlyOpen)
    const answered: ClarificationView = {
      ...onlyOpen,
      items: [
        {
          ...onlyOpen.items[0]!,
          responses: [
            { id: 'r1', round_no: 1, message: 'Regraded on 23 Sep.', created_at: '2026-09-25T01:00:00Z', sent_at: null, attachments: [] },
          ],
        },
      ],
    }
    const respond = vi
      .spyOn(clarApi, 'respondToClarification')
      .mockRejectedValueOnce(new AppError(0, { code: 'network_error', message: 'Could not reach the server.' }))
      .mockResolvedValueOnce(answered)
    vi.useFakeTimers({ shouldAdvanceTime: true })
    renderAt('/app/applications/a1/clarification')
    const field = await screen.findByLabelText(/Your answer/)
    await userEvent.type(field, 'Regraded on 23 Sep.')
    await userEvent.tab()
    await waitFor(() => expect(respond).toHaveBeenCalledTimes(1))
    // the text stays, the help line says a retry is coming, no error toast
    expect(field).toHaveValue('Regraded on 23 Sep.')
    expect(await screen.findByText('Could not save your answer yet; trying again. Your text stays here.')).toBeInTheDocument()
    expect(screen.queryByText('Could not save your answer')).not.toBeInTheDocument()
    await vi.advanceTimersByTimeAsync(retryDelay(1) + 20)
    await waitFor(() => expect(respond).toHaveBeenCalledTimes(2))
    expect(await screen.findByText('Saved. Sent with the round when you press Send responses.')).toBeInTheDocument()
    vi.useRealTimers()
  })

  it('never lets a slow first save land over a newer answer: one save in flight, the edit queued', async () => {
    const userEvent = (await import('@testing-library/user-event')).default
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    const onlyOpen: ClarificationView = { ...view, items: [view.items[0]!], resolved_count: 0 }
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(onlyOpen)
    const answeredWith = (message: string): ClarificationView => ({
      ...onlyOpen,
      items: [
        {
          ...onlyOpen.items[0]!,
          responses: [{ id: 'r1', round_no: 1, message, created_at: '2026-09-25T01:00:00Z', sent_at: null, attachments: [] }],
        },
      ],
    })
    let release: (() => void) | null = null
    const respond = vi
      .spyOn(clarApi, 'respondToClarification')
      .mockImplementationOnce(
        (_id, _item, message) =>
          new Promise((resolve) => {
            release = () => resolve(answeredWith(message))
          }),
      )
      .mockImplementation(async (_id, _item, message) => answeredWith(message))
    renderAt('/app/applications/a1/clarification')
    const field = await screen.findByLabelText(/Your answer/)
    await userEvent.type(field, 'Draft one')
    await userEvent.tab()
    await waitFor(() => expect(respond).toHaveBeenCalledTimes(1))
    // a second edit while the first save is still in flight: no second request yet
    await userEvent.click(field)
    await userEvent.type(field, ', more detail')
    await userEvent.tab()
    expect(respond).toHaveBeenCalledTimes(1)
    release!()
    // the first settles, the queued edit goes out with the newest text, and the newest text stays
    await waitFor(() => expect(respond).toHaveBeenCalledTimes(2))
    expect(respond).toHaveBeenLastCalledWith('a1', 'i1', 'Draft one, more detail')
    await waitFor(() => expect(field).toHaveValue('Draft one, more detail'))
    // the first save landing must not remount the field: same element, still in the document
    await waitFor(() => expect(screen.getByLabelText(/Your answer/)).toBe(field))
    expect(field.isConnected).toBe(true)
  })

  it('a file that failed while offline is sent when the connection returns (US-087)', async () => {
    const userEvent = (await import('@testing-library/user-event')).default
    const { act } = await import('@testing-library/react')
    const { AppError } = await import('@/api/client')
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    const answered: ClarificationView = {
      ...view,
      can_send: true,
      resolved_count: 0,
      items: [
        {
          ...view.items[0]!,
          responses: [
            { id: 'r1', round_no: 1, message: 'Regraded on 23 Sep.', created_at: '2026-09-25T01:00:00Z', sent_at: null, attachments: [] },
          ],
        },
      ],
    }
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(answered)
    const onLine = vi.spyOn(navigator, 'onLine', 'get')
    onLine.mockReturnValue(false)
    const attach = vi
      .spyOn(clarApi, 'attachToResponse')
      .mockRejectedValueOnce(new AppError(0, { code: 'network_error', message: 'Could not reach the server.' }))
      .mockResolvedValue({ view: answered, unchanged: false })
    renderAt('/app/applications/a1/clarification')
    const input = (await screen.findByRole('button', { name: 'Choose a file' })) && (document.querySelector('input[type=file][multiple]') as HTMLInputElement)
    await userEvent.upload(input, new File(['x'], 'floor.jpg', { type: 'image/jpeg' }))
    await waitFor(() => expect(attach).toHaveBeenCalledTimes(1))
    // offline: no timer, the file waits
    onLine.mockReturnValue(true)
    act(() => window.dispatchEvent(new Event('online')))
    await waitFor(() => expect(attach).toHaveBeenCalledTimes(2))
  })

  it('an answer save refused with 409 shows the shared sentence and reloads, never the server reason', async () => {
    const userEvent = (await import('@testing-library/user-event')).default
    const { AppError } = await import('@/api/client')
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    const onlyOpen: ClarificationView = { ...view, items: [view.items[0]!], resolved_count: 0 }
    const withdrawn: ClarificationView = { ...onlyOpen, items: [], open_count: 0, can_respond: false }
    const list = vi.spyOn(clarApi, 'getClarifications').mockResolvedValueOnce(onlyOpen).mockResolvedValue(withdrawn)
    vi.spyOn(clarApi, 'respondToClarification').mockRejectedValue(
      new AppError(409, { code: 'conflict', message: 'This item is not waiting for your response.' }),
    )
    renderAt('/app/applications/a1/clarification')
    const field = await screen.findByLabelText(/Your answer/)
    await userEvent.type(field, 'Too late.')
    await userEvent.tab()
    expect(await screen.findByText('This application changed since you opened it. Showing the latest.')).toBeInTheDocument()
    expect(screen.queryByText('This item is not waiting for your response.')).not.toBeInTheDocument()
    await waitFor(() => expect(list).toHaveBeenCalledTimes(2))
    expect(await screen.findByRole('heading', { name: 'Nothing needs your response yet' })).toBeInTheDocument()
  })

  it('shows the offline notice while the browser is offline and clears it when back (US-087)', async () => {
    const { act } = await import('@testing-library/react')
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(view)
    renderAt('/app/applications/a1/clarification')
    await screen.findAllByLabelText(/Your answer/)
    const onLine = vi.spyOn(navigator, 'onLine', 'get')
    onLine.mockReturnValue(false)
    act(() => window.dispatchEvent(new Event('offline')))
    expect(await screen.findByText('You are offline: answers and files wait here until you reconnect')).toBeInTheDocument()
    onLine.mockReturnValue(true)
    act(() => window.dispatchEvent(new Event('online')))
    await waitFor(() =>
      expect(screen.queryByText('You are offline: answers and files wait here until you reconnect')).not.toBeInTheDocument(),
    )
  })

  it('a send refused with 409 (the officer withdrew the question) reloads the list and the header line', async () => {
    const userEvent = (await import('@testing-library/user-event')).default
    const answered: ClarificationView = {
      ...view,
      can_send: true,
      resolved_count: 0,
      items: [
        {
          ...view.items[0]!,
          responses: [
            { id: 'r1', round_no: 1, message: 'Regraded on 23 Sep.', created_at: '2026-09-25T01:00:00Z', sent_at: null, attachments: [] },
          ],
        },
      ],
    }
    const withdrawn: ClarificationView = { ...answered, items: [], open_count: 0, can_respond: false, can_send: false }
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValueOnce(answered).mockResolvedValue(withdrawn)
    vi.spyOn(api, 'getApplication')
      .mockResolvedValueOnce(afterVisit)
      .mockResolvedValue({
        ...afterVisit,
        status_explanation: 'The site visit is recorded. The licensing office is finalising its assessment.',
        needs_operator_action: false,
        clarification: { can_respond: false, open_count: 0, answered_count: 0, round: 1 },
      })
    const sendSpy = vi
      .spyOn(clarApi, 'sendClarifications')
      .mockRejectedValue(new AppError(409, { code: 'conflict', message: 'Nothing is waiting to be sent.' }))
    renderAt('/app/applications/a1/clarification')
    expect(await screen.findByText('The licensing officer needs more information on 2 items after the site visit.')).toBeInTheDocument()
    await userEvent.click(await screen.findByRole('button', { name: 'Send responses' }))
    await userEvent.click(
      within(await screen.findByRole('dialog', { name: 'Send your answers?' })).getByRole('button', { name: 'Send responses' }),
    )
    await waitFor(() => expect(sendSpy).toHaveBeenCalledWith('a1'))
    expect(await screen.findByText('This application changed since you opened it. Showing the latest.')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Nothing needs your response yet' })).toBeInTheDocument()
    expect(await screen.findByText('The site visit is recorded. The licensing office is finalising its assessment.')).toBeInTheDocument()
    expect(screen.queryByText('The licensing officer needs more information on 2 items after the site visit.')).not.toBeInTheDocument()
  })

  it('with nothing released the page says so', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(applicationView({ id: 'a1' }))
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue({
      ...view,
      items: [],
      open_count: 0,
      resolved_count: 0,
      round: 0,
      can_respond: false,
    })
    renderAt('/app/applications/a1/clarification')
    expect(await screen.findByRole('heading', { name: 'Nothing needs your response yet' })).toBeInTheDocument()
  })

  it('an answer typed and not saved stays on the device and comes back after a reload (UAT run 5, F13)', async () => {
    vi.spyOn(api, 'getApplication').mockResolvedValue(afterVisit)
    vi.spyOn(clarApi, 'getClarifications').mockResolvedValue(view)
    const respond = vi.spyOn(clarApi, 'respondToClarification').mockRejectedValue(new AppError(0, { code: 'network', message: 'Failed to fetch' }))
    const { unmount } = renderAt('/app/applications/a1/clarification')
    const field = await screen.findByRole('textbox', { name: /Your answer/ })
    fireEvent.change(field, { target: { value: 'Regraded on 25 Sep; photo to follow.' } })
    const key = 'permitflow.unsaved.clarification.a1.i1.1'
    await waitFor(() => expect(JSON.parse(localStorage.getItem(key) ?? 'null')?.value).toBe('Regraded on 25 Sep; photo to follow.'))
    unmount()
    // The page loads again (a reload, a discarded tab): the answer is back and goes to the server.
    respond.mockReset()
    respond.mockResolvedValue({
      ...view,
      items: [{ ...view.items[0]!, responses: [{ id: 'r1', round_no: 1, message: 'Regraded on 25 Sep; photo to follow.', created_at: '', sent_at: null, attachments: [] }] }, view.items[1]!],
    })
    renderAt('/app/applications/a1/clarification')
    expect(await screen.findByDisplayValue('Regraded on 25 Sep; photo to follow.')).toBeInTheDocument()
    await waitFor(() => expect(respond).toHaveBeenCalledWith('a1', 'i1', 'Regraded on 25 Sep; photo to follow.'))
    await waitFor(() => expect(localStorage.getItem(key)).toBeNull())
  })
})
