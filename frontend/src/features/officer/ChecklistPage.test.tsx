import { render, screen, waitFor, within } from '@testing-library/react'
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
import { ChecklistPage, summarise } from './ChecklistPage'

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

describe('site visit checklist (US-060)', () => {
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

  it('opens the draft with a POST, renders every item, and saves the whole list with the version and a save id', async () => {
    const open = vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const save = vi.spyOn(checklistApi, 'saveChecklist').mockResolvedValue({ ...draft, version: 4, updated_at: '2026-09-24T06:10:00Z' })
    renderAt('/officer/applications/a1/checklist')
    expect(await screen.findByRole('heading', { name: 'Site visit checklist' })).toBeInTheDocument()
    expect(open).toHaveBeenCalledWith('a1')
    expect(screen.getAllByRole('group', { name: 'Result' })).toHaveLength(3)
    expect(screen.getAllByText('Not assessed')).toHaveLength(3)
    expect(screen.getAllByText('0 of 3 assessed, 0 flagged')).toHaveLength(2) // progress line and sticky card
    expect(screen.getByRole('button', { name: 'Mark visit done and submit' })).toBeDisabled()
    // no comment field until an item is unsatisfactory or flagged
    expect(screen.queryByLabelText(/Comment/)).not.toBeInTheDocument()
    const groups = screen.getAllByRole('group', { name: 'Result' })
    await userEvent.click(within(groups[0]!).getByRole('button', { name: 'Satisfactory' }))
    await userEvent.click(within(groups[1]!).getByRole('button', { name: 'Unsatisfactory' }))
    expect(within(groups[1]!).getByRole('button', { name: 'Unsatisfactory' })).toHaveAttribute('aria-pressed', 'true')
    expect(await screen.findByText('A comment is required for an unsatisfactory or flagged item.')).toBeInTheDocument()
    expect(screen.getByText('1 comment missing')).toBeInTheDocument()
    expect(screen.getByText('Assess 1 more item and add 1 comment to submit.')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText(/Comment/), 'Floor slopes away from the trap.')
    await userEvent.click(screen.getAllByLabelText('Need further clarification')[2]!)
    // item 2 has its comment now; item 3 is flagged without one
    expect(await screen.findAllByText('A comment is required for an unsatisfactory or flagged item.')).toHaveLength(1)
    expect(screen.getByText('Unsaved changes')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() => expect(save).toHaveBeenCalledTimes(1))
    const [id, body] = save.mock.calls[0]!
    expect(id).toBe('a1')
    expect(body.version).toBe(3)
    expect(body.save_id).toMatch(/^[0-9a-f-]{36}$/)
    expect(body.items).toEqual([
      { key: 'layout_matches_plan', result: 'satisfactory', comment: null, needs_clarification: false },
      { key: 'floor_trap_graded', result: 'unsatisfactory', comment: 'Floor slopes away from the trap.', needs_clarification: false },
      { key: 'sink_provided', result: 'not_assessed', comment: null, needs_clarification: true },
    ])
    expect(await screen.findByText('Saved just now')).toBeInTheDocument()
    // the next save is based on the returned version
    await userEvent.click(within(groups[2]!).getByRole('button', { name: 'Not applicable' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() => expect(save).toHaveBeenCalledTimes(2))
    expect(save.mock.calls[1]![1].version).toBe(4)
  })

  it('a stale version shows the other version with Keep my entries or Take theirs', async () => {
    vi.spyOn(checklistApi, 'openChecklist').mockResolvedValue(draft)
    const theirs: Checklist = {
      ...draft,
      version: 5,
      items: [item('layout_matches_plan', 'premises', 1, { result: 'not_applicable' }), draft.items[1]!, draft.items[2]!],
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
    await userEvent.click(within(groups[0]!).getByRole('button', { name: 'Satisfactory' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }))
    expect(await screen.findByText('Another tab or device saved this checklist')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Keep my entries' }))
    // my entry stands and the next save is based on their version
    expect(within(groups[0]!).getByRole('button', { name: 'Satisfactory' })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() => expect(save).toHaveBeenCalledTimes(2))
    expect(save.mock.calls[1]![1].version).toBe(5)
  })

  it('a case without a scheduled visit explains why the checklist is closed', async () => {
    vi.spyOn(checklistApi, 'openChecklist').mockRejectedValue(
      new AppError(409, { code: 'conflict', message: 'The checklist opens once a site visit is scheduled.' }),
    )
    renderAt('/officer/applications/a1/checklist')
    expect(await screen.findByText('The checklist opens once a site visit is scheduled')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to the case' })).toBeInTheDocument()
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
