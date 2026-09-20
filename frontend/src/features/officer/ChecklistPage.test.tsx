import { render, screen, within } from '@testing-library/react'
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
import { AUTOSAVE_DELAY_MS, ChecklistPage, mergeFindings, retryDelay, summarise } from './ChecklistPage'

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
    expect(retryDelay(1)).toBe(3000)
    expect(retryDelay(4)).toBe(24_000)
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
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument()
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

  it('a case without a scheduled visit explains why the checklist is closed', async () => {
    vi.spyOn(checklistApi, 'openChecklist').mockRejectedValue(
      new AppError(409, { code: 'conflict', message: 'The checklist opens once a site visit is scheduled.' }),
    )
    renderAt('/officer/applications/a1/checklist')
    expect(await screen.findByText('The checklist opens once a site visit is scheduled')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to the case' })).toBeInTheDocument()
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
})
