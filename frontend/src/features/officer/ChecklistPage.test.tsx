import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'

import * as checklistApi from '@/api/checklist'
import type { Checklist, ChecklistItem, ChecklistSchema } from '@/api/checklist'
import { AppError } from '@/api/client'
import * as formApi from '@/api/formSchema'
import * as api from '@/api/officer'
import { AppProviders } from '@/app/providers'
import { formSchema, officerView } from '@/test/fixtures'
import { OfficerCasePage } from './CasePage'

// The signed-in officer, for the device copy's key; the page is rendered without the auth provider.
vi.mock('@/features/auth/AuthContext', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/features/auth/AuthContext')>()),
  useCurrentUserId: () => 'officer-1',
}))
import { AUTOSAVE_DELAY_MS, ChecklistPage, adoptServerKeys, localCopy, mergeFindings, retryDelay, summarise, toInput } from './ChecklistPage'

const defs = [
  ['premises', 'Premises', ['layout_matches_plan', 'floor_trap_graded']],
  ['kitchen', 'Kitchen', ['sink_provided']],
] as const

const schema: ChecklistSchema = {
  version: 1,
  description: 'Three items for the test.',
  sections: defs.map(([key, title, keys]) => ({
    key,
    title,
    items: keys.map((k) => ({ key: k, section: key, title: k.replaceAll('_', ' '), guidance: '', applicable_by_default: true })),
  })),
  item_count: 3,
}

function item(key: string, section: string, position: number, over: Partial<ChecklistItem> = {}): ChecklistItem {
  return {
    id: `i-${key}`,
    key,
    section,
    title: key.replaceAll('_', ' '),
    guidance: '',
    position,
    result: 'not_assessed',
    comment: null,
    needs_clarification: false,
    clarification_status: 'none',
    is_extra: false,
    custom_title: null,
    parent_key: null,
    ...over,
  }
}

const draft: Checklist = {
  id: 'c1',
  application_id: 'a1',
  visit_no: 1,
  schema_version: 1,
  status: 'draft',
  version: 3,
  created_by: 'Lim Hui Ling',
  created_at: '2026-09-22T01:00:00Z',
  updated_at: null,
  submitted_by: null,
  submitted_at: null,
  counts: { total: 3, assessed: 0, flagged: 0, unsatisfactory: 0, not_applicable: 0, missing_comments: 0 },
  remaining: 'Assess 3 more items to submit.',
  items: [item('layout_matches_plan', 'premises', 1), item('floor_trap_graded', 'premises', 2), item('sink_provided', 'kitchen', 3)],
}

const scheduled = officerView({
  id: 'a1',
  status: 'site_visit_scheduled',
  status_label: 'Site Visit Scheduled',
  site_visit: {
    visit_no: 1,
    status: 'confirmed',
    status_label: 'Confirmed',
    date: '2026-09-24',
    slot: 'afternoon',
    when: 'Thursday 24 September 2026, afternoon (14:00 to 17:00)',
    note: null,
    reply_deadline: null,
    can_confirm_without_reply: false,
    confirm_without_reply_reason: null,
    original: null,
    counter: null,
    can_reschedule: true,
    rounds_left: 5,
    round_limit_reason: null,
    rounds: [],
    date_stands: true,
    visit_day_reached: true,
    is_current: true,
  },
  actions: [
    { target: 'site_visit_done', label: 'Mark site visit done', enabled: true, reason: null, requires_note: false },
    { target: 'rejected', label: 'Reject', enabled: true, reason: null, requires_note: true },
  ],
})

function renderAt(path: string) {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/officer/applications/:id" element={<OfficerCasePage />} />
          <Route path="/officer/applications/:id/checklist" element={<ChecklistPage />} />
        </Routes>
      </MemoryRouter>
    </AppProviders>,
  )
}

describe('site visit checklist (US-060, US-061)', () => {
  afterEach(() => vi.useRealTimers())
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue(scheduled)
    vi.spyOn(api, 'getFeedbackTemplates').mockResolvedValue([])
    vi.spyOn(checklistApi, 'getChecklistSchema').mockResolvedValue(schema)
    vi.spyOn(formApi, 'getFormSchema').mockResolvedValue(formSchema)
  })

  it('the case offers Open checklist once the visit is confirmed, and Continue once a draft exists', async () => {
    const { unmount } = renderAt('/officer/applications/a1')
    expect(await screen.findByRole('link', { name: 'Open checklist' })).toHaveAttribute('href', '/officer/applications/a1/checklist')
    unmount()
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...scheduled,
      checklist: {
        visit_no: 1,
        status: 'draft',
        version: 4,
        counts: { ...draft.counts, assessed: 8, flagged: 2 },
        updated_at: '2026-09-24T06:10:00Z',
        submitted_at: null,
      },
    })
    renderAt('/officer/applications/a1')
    expect(await screen.findByRole('link', { name: 'Continue checklist' })).toBeInTheDocument()
    expect(screen.getByText('Visit 1: 8 of 3 assessed, 2 flagged.')).toBeInTheDocument()
  })

  it('opens the draft with a POST, renders every item, and autosaves the whole list 1.5 s after the last touch', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const open = vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4, updated_at: '2026-09-24T06:10:00Z' })
    renderAt('/officer/applications/a1/checklist')
    expect(await screen.findByRole('heading', { name: 'Site visit checklist' })).toBeInTheDocument()
    expect(open).toHaveBeenCalledWith('a1')
    expect(screen.getAllByRole('group', { name: 'Result' })).toHaveLength(3)
    expect(screen.getAllByText('Not assessed')).toHaveLength(3)
    expect(screen.getAllByText('0 of 3 assessed, 0 flagged')).toHaveLength(2) // progress line and sticky card
    expect(screen.getByRole('button', { name: 'Mark visit done and submit' })).toBeDisabled()
    expect(screen.queryByLabelText(/Comment/)).not.toBeInTheDocument()
    const groups = screen.getAllByRole('group', { name: 'Result' })
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    // pressing the selected result again clears it
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    expect(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ })).toHaveAttribute('aria-pressed', 'false')
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    await user.click(within(groups[1]!).getByRole('button', { name: /^Unsatisfactory$/ }))
    expect(within(groups[1]!).getByRole('button', { name: /^Unsatisfactory$/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('A comment is required for an unsatisfactory or flagged item.')).toBeInTheDocument()
    expect(screen.getByText('1 comment missing')).toBeInTheDocument()
    expect(screen.getByText('Assess 1 more item and add 1 comment to submit.')).toBeInTheDocument()
    await user.type(screen.getByLabelText(/Comment/), 'Floor slopes away from the trap.')
    await user.click(screen.getAllByLabelText('Need further clarification')[2]!)
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument()
    // nothing sent yet: the debounce is still running
    expect(save).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 10)
    expect(save).toHaveBeenCalledTimes(1)
    const [id, body] = save.mock.calls[0]!
    expect(id).toBe('a1')
    expect(body.version).toBe(3)
    expect(body.save_id).toMatch(/^[0-9a-f-]{36}$/)
    expect(body.items).toEqual([
      { key: 'layout_matches_plan', result: 'satisfactory', comment: null, needs_clarification: false },
      { key: 'floor_trap_graded', result: 'unsatisfactory', comment: 'Floor slopes away from the trap.', needs_clarification: false },
      { key: 'sink_provided', result: 'not_assessed', comment: null, needs_clarification: true },
    ])
    await vi.advanceTimersByTimeAsync(10)
    expect(screen.getByText('Saved just now')).toBeInTheDocument()
    // Save draft goes at once and is based on the returned version
    await user.click(within(groups[2]!).getByRole('button', { name: 'Not applicable' }))
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    await vi.advanceTimersByTimeAsync(10)
    expect(save).toHaveBeenCalledTimes(2)
    expect(save.mock.calls[1]![1].version).toBe(4)
    vi.useRealTimers()
  })

  it('a failed save keeps the entries and retries with backoff', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi
      .spyOn(checklistApi, 'saveChecklist')
      .mockRejectedValueOnce(new AppError(0, { code: 'network_error', message: 'Could not reach the server.' }))
      .mockRejectedValueOnce(new AppError(503, { code: 'unavailable', message: 'Busy.' }))
      .mockResolvedValueOnce({ ...draft, version: 4 })
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 10)
    expect(save).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(10)
    expect(screen.getByText('Could not save, retrying')).toBeInTheDocument()
    expect(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ })).toHaveAttribute('aria-pressed', 'true')
    await vi.advanceTimersByTimeAsync(retryDelay(1) + 10)
    expect(save).toHaveBeenCalledTimes(2)
    // the retry carries the same save id, so a save whose reply was lost is recognised server-side
    expect(save.mock.calls[1]![1].save_id).toBe(save.mock.calls[0]![1].save_id)
    await vi.advanceTimersByTimeAsync(retryDelay(2) + 10)
    expect(save).toHaveBeenCalledTimes(3)
    await vi.advanceTimersByTimeAsync(10)
    expect(screen.getByText('Saved just now')).toBeInTheDocument()
    expect(retryDelay(1)).toBe(1000)
    expect(retryDelay(4)).toBe(8000)
    expect(retryDelay(9)).toBe(30_000)
    vi.useRealTimers()
  })

  it('offline: the banner shows, nothing is sent, and the save goes when the connection returns', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4 })
    const onLine = vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    window.dispatchEvent(new Event('offline'))
    expect(await screen.findByText('You are offline: changes will not save until you reconnect')).toBeInTheDocument()
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 10)
    expect(save).not.toHaveBeenCalled()
    // Offline nothing is retried: the line says what it waits for (UAT run 5, F10).
    expect(screen.getByText('Waiting for the connection')).toBeInTheDocument()
    onLine.mockReturnValue(true)
    window.dispatchEvent(new Event('online'))
    await vi.advanceTimersByTimeAsync(20)
    expect(save).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('You are offline: changes will not save until you reconnect')).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('a stale version merges the other tab under my touched items and saves again', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const theirs: Checklist = {
      ...draft,
      version: 5,
      items: [
        item('layout_matches_plan', 'premises', 1, { result: 'not_applicable' }),
        item('floor_trap_graded', 'premises', 2, { result: 'satisfactory' }),
        draft.items[2]!,
      ],
    }
    const save = vi
      .spyOn(checklistApi, 'saveChecklist')
      .mockRejectedValueOnce(
        new AppError(409, {
          code: 'version_conflict',
          message: 'This checklist changed since you opened it.',
          details: { current: theirs },
        }),
      )
      .mockResolvedValueOnce({ ...theirs, version: 6 })
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 30)
    expect(await screen.findByText('Another tab or device saved this checklist')).toBeInTheDocument()
    // my touched item stands, their untouched one is taken, and the merge is saved on their version
    expect(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ })).toHaveAttribute('aria-pressed', 'true')
    expect(within(groups[1]!).getByRole('button', { name: /^Satisfactory$/ })).toHaveAttribute('aria-pressed', 'true')
    expect(save).toHaveBeenCalledTimes(2)
    expect(save.mock.calls[1]![1].version).toBe(5)
    expect(save.mock.calls[1]![1].items[0]).toEqual({
      key: 'layout_matches_plan',
      result: 'satisfactory',
      comment: null,
      needs_clarification: false,
    })
    expect(save.mock.calls[1]![1].items[1]!.result).toBe('satisfactory')
    vi.useRealTimers()
  })

  it('a save refused because another tab submitted the checklist drops the edit and reloads the case', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const submitted: Checklist = {
      ...draft,
      status: 'submitted',
      version: 9,
      submitted_by: 'Lim Hui Ling',
      submitted_at: '2026-09-24T07:00:00Z',
      items: [
        item('layout_matches_plan', 'premises', 1, { result: 'satisfactory' }),
        item('floor_trap_graded', 'premises', 2, { result: 'satisfactory' }),
        item('sink_provided', 'kitchen', 3, { result: 'satisfactory' }),
      ],
      counts: { total: 3, assessed: 3, flagged: 0, unsatisfactory: 0, not_applicable: 0, missing_comments: 0 },
      remaining: '',
    }
    const filled: Checklist = { ...submitted, status: 'draft', submitted_by: null, submitted_at: null, version: 8 }
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValueOnce(filled).mockResolvedValue(submitted)
    // First load: the visit is scheduled. After the 409: the other tab's submit moved the case on.
    vi.spyOn(api, 'getOfficerApplication')
      .mockResolvedValueOnce(scheduled)
      .mockResolvedValue(
        officerView({ ...scheduled, status: 'pending_post_site_clarification', status_label: 'Awaiting Post-Site Clarification' }),
      )
    const save = vi
      .spyOn(checklistApi, 'saveChecklist')
      .mockRejectedValue(
        new AppError(409, { code: 'conflict', message: 'This checklist was submitted; its findings can no longer change.' }),
      )
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    await user.click(within(groups[0]!).getByRole('button', { name: /^Not applicable$/ }))
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 30)
    expect(await screen.findByText('This checklist was submitted; its findings can no longer change.')).toBeInTheDocument()
    expect(save).toHaveBeenCalledTimes(1)
    // the server copy stands: the local edit is gone, the page is read-only and the case badge moved on
    await waitFor(() => expect(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ })).toHaveAttribute('aria-pressed', 'true'))
    expect(within(groups[0]!).getByRole('button', { name: /^Not applicable$/ })).toBeDisabled()
    expect(await screen.findByText('Awaiting Post-Site Clarification')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Mark visit done and submit' })).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it('a case without a scheduled visit explains why the checklist is closed', async () => {
    vi.spyOn(checklistApi, 'openChecklist').mockRejectedValue(
      new AppError(409, { code: 'conflict', message: 'The checklist opens once a site visit is scheduled.' }),
    )
    renderAt('/officer/applications/a1/checklist')
    expect(await screen.findByText('The checklist opens once a site visit is scheduled')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to the case' })).toBeInTheDocument()
  })

  it('an extra finding is added with a title, saved with a null key, adopts the server key and can be removed (US-092)', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const serverExtra = item('extra_1a2b3c4d', 'premises', 4, {
      result: 'unsatisfactory',
      comment: 'Second trap blocked.',
      is_extra: true,
      custom_title: 'Second floor trap blocked',
      parent_key: 'floor_trap_graded',
    })
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4, items: [...draft.items, serverExtra] })
    renderAt('/officer/applications/a1/checklist')
    await screen.findByRole('heading', { name: 'Site visit checklist' })
    expect(screen.getByRole('heading', { name: 'Other findings' })).toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: 'Add another finding' })[1]!)
    const title = await screen.findByLabelText(/Finding 2 on this item/)
    expect(screen.getByText('Give the finding a title.')).toBeInTheDocument()
    expect(screen.getByText('Assess 4 more items and title 1 finding to submit.')).toBeInTheDocument()
    // untitled: nothing is sent for it
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 10)
    expect(save).not.toHaveBeenCalled()
    await user.type(title, 'Second floor trap blocked')
    const groups = screen.getAllByRole('group', { name: 'Result' })
    await user.click(within(groups[2]!).getByRole('button', { name: /^Unsatisfactory$/ }))
    await user.type(screen.getByLabelText(/Comment/), 'Second trap blocked.')
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 30)
    expect(save).toHaveBeenCalled()
    const body = save.mock.calls.at(-1)![1]
    const extra = body.items.find((i) => i.custom_title)
    expect(extra).toEqual({
      key: null,
      result: 'unsatisfactory',
      comment: 'Second trap blocked.',
      needs_clarification: false,
      custom_title: 'Second floor trap blocked',
      parent_key: 'floor_trap_graded',
    })
    // the server key is adopted: the next save sends it, and Remove drops it
    await user.click(screen.getAllByLabelText('Need further clarification')[2]!)
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 30)
    const again = save.mock.calls.at(-1)![1].items.find((i) => i.custom_title)
    expect(again?.key).toBe('extra_1a2b3c4d')
    await user.click(screen.getByRole('button', { name: 'Remove' }))
    await vi.advanceTimersByTimeAsync(30)
    expect(save.mock.calls.at(-1)![1].items.some((i) => i.custom_title)).toBe(false)
    vi.useRealTimers()
  })

  it('hiding the page sends the last entries at once with keepalive', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4 })
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    expect(save).not.toHaveBeenCalled()
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' })
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(10)
    expect(save).toHaveBeenCalledTimes(1)
    expect(save.mock.calls[0]![2]).toBe(true)
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' })
    vi.useRealTimers()
  })

  it('leaving by a link inside the debounce sends the last entries with keepalive', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4 })
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    // fireEvent, not userEvent: a tapped button on an iPad never takes focus, so no blur can rescue the tap
    fireEvent.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    expect(save).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('link', { name: 'Back to the case' }))
    await vi.advanceTimersByTimeAsync(10)
    expect(save).toHaveBeenCalledTimes(1)
    expect(save.mock.calls[0]![1].items[0]!.result).toBe('satisfactory')
    expect(save.mock.calls[0]![2]).toBe(true)
    vi.useRealTimers()
  })

  it('hiding the page while a save is in flight still sends the newer entries with keepalive, as a new batch', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    let release: (c: Checklist) => void = () => undefined
    const save = vi
      .spyOn(checklistApi, 'saveChecklist')
      .mockImplementationOnce(() => new Promise<Checklist>((resolve) => (release = resolve)))
      .mockResolvedValue({ ...draft, version: 5 })
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    await user.click(within(groups[0]!).getByRole('button', { name: /^Satisfactory$/ }))
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DELAY_MS + 30)
    expect(save).toHaveBeenCalledTimes(1) // hangs
    await user.click(within(groups[1]!).getByRole('button', { name: /^Satisfactory$/ }))
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' })
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(10)
    expect(save).toHaveBeenCalledTimes(2)
    expect(save.mock.calls[1]![2]).toBe(true)
    expect(save.mock.calls[1]![1].items[1]!.result).toBe('satisfactory')
    // a touch after the first save went out is a new batch: never the in-flight id
    expect(save.mock.calls[1]![1].save_id).not.toBe(save.mock.calls[0]![1].save_id)
    release({ ...draft, version: 4 })
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' })
    vi.useRealTimers()
  })

  it('a keepalive body over the browser cap goes as a plain fetch instead', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4 })
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    await user.click(within(groups[0]!).getByRole('button', { name: /^Unsatisfactory$/ }))
    // 2,000 three-byte characters in one comment is already over 60 KB once JSON-encoded x 3 items? no:
    // one comment of 2,000 CJK characters is 6 KB; the page-wide cap is what matters, so paste a long one
    // into each of the three comments through a flag on every item
    for (const g of groups) await user.click(within(g).getByRole('button', { name: /^Unsatisfactory$/ }))
    const long = '漢'.repeat(2000)
    for (const box of screen.getAllByLabelText(/Comment/)) fireEvent.change(box, { target: { value: long } })
    // three comments of 6 KB each are under the cap: keepalive stays on
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' })
    document.dispatchEvent(new Event('visibilitychange'))
    await vi.advanceTimersByTimeAsync(10)
    expect(save).toHaveBeenCalledTimes(1)
    expect(save.mock.calls[0]![2]).toBe(true)
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'visible' })
    vi.useRealTimers()
  })

  it('toInput and adoptServerKeys handle extras', () => {
    const local = {
      a: { result: 'satisfactory' as const, comment: '', needs_clarification: false },
      new_1: {
        result: 'unsatisfactory' as const,
        comment: 'x',
        needs_clarification: true,
        extra: true,
        title: 'Loose tiles',
        parent: null,
      },
      new_2: { result: 'not_assessed' as const, comment: '', needs_clarification: false, extra: true, title: '', parent: 'a' },
    }
    expect(toInput(local)).toEqual([
      { key: 'a', result: 'satisfactory', comment: null, needs_clarification: false },
      { key: null, result: 'unsatisfactory', comment: 'x', needs_clarification: true, custom_title: 'Loose tiles', parent_key: null },
    ])
    const adopted = adoptServerKeys(local, [
      item('extra_9', 'other', 5, { is_extra: true, custom_title: 'Loose tiles', parent_key: null, result: 'unsatisfactory' }),
    ])
    expect(Object.keys(adopted).sort()).toEqual(['a', 'extra_9', 'new_2'])
    expect(adopted.extra_9).toMatchObject({ title: 'Loose tiles', comment: 'x', needs_clarification: true })
  })

  it('mergeFindings keeps my touched items on top of theirs', () => {
    const mine = {
      a: { result: 'satisfactory' as const, comment: '', needs_clarification: false },
      b: { result: 'unsatisfactory' as const, comment: 'x', needs_clarification: false },
    }
    const theirs = {
      a: { result: 'not_applicable' as const, comment: '', needs_clarification: false },
      b: { result: 'satisfactory' as const, comment: '', needs_clarification: true },
    }
    expect(mergeFindings(theirs, mine, ['b'])).toEqual({ a: theirs.a, b: mine.b })
  })

  it('summarise counts assessed, flagged and missing comments the way the server does', () => {
    expect(
      summarise({
        a: { result: 'satisfactory', comment: '', needs_clarification: false },
        b: { result: 'unsatisfactory', comment: '', needs_clarification: false },
        c: { result: 'not_assessed', comment: '', needs_clarification: true },
        d: { result: 'not_applicable', comment: '', needs_clarification: false },
      }),
    ).toEqual({ assessed: 3, flagged: 1, missing: 2, total: 4, remaining: 'Assess 1 more item and add 2 comments to submit.' })
    expect(summarise({ a: { result: 'satisfactory', comment: '', needs_clarification: false } }).remaining).toBeNull()
  })

  it('entries left on the device by a reload are put back over the draft and saved (UAT run 5, F11)', async () => {
    localStorage.setItem(
      'permitflow.unsaved.checklist.a1.1.officer-1',
      JSON.stringify({
        savedAt: Date.now(),
        value: {
          findings: {
            layout_matches_plan: { result: 'satisfactory', comment: '', needs_clarification: false },
            floor_trap_graded: { result: 'unsatisfactory', comment: 'Water pools by the sink.', needs_clarification: true },
            sink_provided: { result: 'not_assessed', comment: '', needs_clarification: false },
          },
          touched: ['floor_trap_graded'],
        },
      }),
    )
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4 })
    renderAt('/officer/applications/a1/checklist')
    expect(await screen.findByText('Unsaved entries restored from this device')).toBeInTheDocument()
    await waitFor(() => expect(save).toHaveBeenCalledTimes(1))
    const body = save.mock.calls[0]![1]
    // Only the touched item comes from the device; the rest is the server's draft.
    expect(body.items.find((i) => i.key === 'floor_trap_graded')).toMatchObject({ result: 'unsatisfactory', needs_clarification: true })
    expect(body.items.find((i) => i.key === 'layout_matches_plan')).toMatchObject({ result: 'not_assessed' })
    expect(body.version).toBe(3)
    await waitFor(() => expect(localStorage.getItem('permitflow.unsaved.checklist.a1.1.officer-1')).toBeNull())
  })

  it("another officer's copy on this device is never offered (security audit, 24 Sep)", async () => {
    // Left by a session that expired or was taken over; only the officer's own Sign out clears every copy.
    localStorage.setItem(
      'permitflow.unsaved.checklist.a1.1.officer-2',
      JSON.stringify({
        savedAt: Date.now(),
        value: {
          findings: { floor_trap_graded: { result: 'unsatisfactory', comment: 'Their finding.', needs_clarification: true } },
          touched: ['floor_trap_graded'],
        },
      }),
    )
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4 })
    renderAt('/officer/applications/a1/checklist')
    expect(await screen.findAllByRole('group', { name: 'Result' })).not.toHaveLength(0)
    expect(screen.queryByText('Unsaved entries restored from this device')).not.toBeInTheDocument()
    expect(save).not.toHaveBeenCalled()
    localStorage.removeItem('permitflow.unsaved.checklist.a1.1.officer-2')
  })

  it('an unsaved touch is kept on the device until the server confirms it (F11)', async () => {
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    vi.spyOn(checklistApi, 'saveChecklist').mockRejectedValue(new AppError(0, { code: 'network', message: 'Failed to fetch' }))
    renderAt('/officer/applications/a1/checklist')
    const groups = await screen.findAllByRole('group', { name: 'Result' })
    await userEvent.click(within(groups[1]!).getByRole('button', { name: /^Satisfactory$/ }))
    const stored = JSON.parse(localStorage.getItem('permitflow.unsaved.checklist.a1.1.officer-1') ?? 'null') as {
      value: { findings: Record<string, { result: string }>; touched: string[] }
    } | null
    expect(stored?.value.touched).toEqual(['floor_trap_graded'])
    expect(stored?.value.findings.floor_trap_graded?.result).toBe('satisfactory')
  })

  it('before the visit day the submit waits, with the server reason (UAT run 5, F12)', async () => {
    const complete = { ...draft, items: draft.items.map((i) => ({ ...i, result: 'satisfactory' as const })), remaining: null }
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...scheduled,
      actions: [
        {
          target: 'site_visit_done',
          label: 'Mark site visit done',
          enabled: false,
          reason: 'The visit is on Wed 30 Sep. Mark it done on or after that day.',
          requires_note: false,
        },
      ],
    })
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(complete)
    renderAt('/officer/applications/a1/checklist')
    const submit = await screen.findByRole('button', { name: 'Mark visit done and submit' })
    expect(submit).toBeDisabled()
    expect(screen.getByText(/The visit is on Wed 30 Sep\. Mark it done on or after that day\. You can keep filling the draft/)).toBeInTheDocument()
  })

  it("an earlier visit's checklist opens read-only by its number (UAT run 5, F17)", async () => {
    const open = vi.spyOn(checklistApi, 'openChecklist')
    const get = vi.spyOn(checklistApi, 'getChecklist').mockResolvedValue({ ...draft, status: 'submitted', submitted_by: 'Lim Hui Ling', submitted_at: '2026-09-24T04:43:00Z' })
    renderAt('/officer/applications/a1/checklist?visit=1')
    expect(await screen.findByText('Visit 1, an earlier visit')).toBeInTheDocument()
    expect(get).toHaveBeenCalledWith('a1', 1)
    expect(open).not.toHaveBeenCalled()
    for (const b of within(screen.getAllByRole('group', { name: 'Result' })[0]!).getAllByRole('button')) expect(b).toBeDisabled()
    expect(screen.queryByRole('button', { name: /submit/i })).not.toBeInTheDocument()
  })

  it('the checklist stays open while the operator asks to move a confirmed date (UAT run 5, F8)', async () => {
    vi.spyOn(api, 'getOfficerApplication').mockResolvedValue({
      ...scheduled,
      site_visit: { ...scheduled.site_visit!, status: 'counter_proposed', status_label: 'Waiting for you', date_stands: true },
    })
    renderAt('/officer/applications/a1')
    expect(await screen.findByRole('link', { name: 'Open checklist' })).toBeInTheDocument()
    expect(screen.getByText(/Confirmed date:/)).toBeInTheDocument()
  })

  it('the device copy keeps what has content and drops an empty new finding (F11)', () => {
    const findings = {
      sink_provided: { result: 'satisfactory' as const, comment: '', needs_clarification: false },
      new_a1b2c3d4: { result: 'not_assessed' as const, comment: '', needs_clarification: false, extra: true, title: '', parent: null },
      new_e5f6a7b8: { result: 'not_assessed' as const, comment: '', needs_clarification: false, extra: true, title: 'Loose tiles', parent: null },
    }
    expect(localCopy(findings, ['new_a1b2c3d4'])).toBeNull()
    const copy = localCopy(findings, ['sink_provided', 'new_a1b2c3d4', 'new_e5f6a7b8'])
    expect(copy?.touched).toEqual(['sink_provided', 'new_e5f6a7b8'])
    expect(Object.keys(copy?.findings ?? {})).toEqual(['sink_provided', 'new_e5f6a7b8'])
  })
})
