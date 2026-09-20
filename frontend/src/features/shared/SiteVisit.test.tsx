import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import { AppError } from '@/api/client'
import type { SiteVisitProposal } from '@/api/siteVisit'
import { SlotControl, VisitRounds, dateBounds, fieldErrorsOf, roundTitle, todayInSingapore } from './SiteVisit'

describe('site visit helpers', () => {
  it('reads the Singapore date, not the browser one, around midnight', () => {
    // 16:00 UTC is already the next day in Singapore (UTC+8)
    expect(todayInSingapore(new Date('2026-09-21T15:59:00Z'))).toBe('2026-09-21')
    expect(todayInSingapore(new Date('2026-09-21T16:00:00Z'))).toBe('2026-09-22')
  })

  it('bounds the picker from tomorrow in Singapore to 60 days out, or from the server earliest', () => {
    expect(dateBounds(undefined, new Date('2026-09-21T16:00:00Z'))).toEqual({ min: '2026-09-23', max: '2026-11-21' })
    expect(dateBounds('2026-09-25', new Date('2026-09-21T16:00:00Z'))).toEqual({ min: '2026-09-25', max: '2026-11-21' })
  })

  it('extracts per-field messages from a 422 only', () => {
    const e = new AppError(422, { code: 'validation_failed', message: 'x', details: { fields: { date: 'Choose a working day.', n: 1 } } })
    expect(fieldErrorsOf(e)).toEqual({ date: 'Choose a working day.' })
    expect(fieldErrorsOf(new AppError(409, { code: 'conflict', message: 'moved' }))).toEqual({})
    expect(fieldErrorsOf(new Error('boom'))).toEqual({})
  })

  it('titles a round from the reader side and never names the officer to the operator', () => {
    const officer: SiteVisitProposal = {
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
    const operator: SiteVisitProposal = { ...officer, round: 2, author_role: 'operator', author_name: 'Tan Wei Ling', outcome: 'accepted' }
    expect(roundTitle(officer, 'operator')).toBe('The officer proposed Tuesday 22 September 2026, morning (09:00 to 12:00)')
    expect(roundTitle(officer, 'officer')).toBe('You proposed Tuesday 22 September 2026, morning (09:00 to 12:00)')
    expect(roundTitle(operator, 'officer')).toBe('Tan Wei Ling proposed another date: Tuesday 22 September 2026, morning (09:00 to 12:00)')
    expect(roundTitle(operator, 'operator')).toBe('You proposed another date: Tuesday 22 September 2026, morning (09:00 to 12:00)')
    render(<VisitRounds rounds={[officer, operator]} reader="operator" />)
    expect(screen.getByRole('list', { name: 'Site visit rounds' })).toBeInTheDocument()
    expect(screen.getByText(/Round 1 .* Waiting/)).toBeInTheDocument()
    expect(screen.getByText(/Round 2 .* Accepted/)).toBeInTheDocument()
    expect(screen.queryByText(/Lim Hui Ling/)).not.toBeInTheDocument()
  })

  it('the slot control is a pressed-state group', async () => {
    const onChange = vi.fn()
    render(<SlotControl value="morning" onChange={onChange} />)
    expect(screen.getByRole('button', { name: /Morning/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: /Afternoon/ })).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(screen.getByRole('button', { name: /Afternoon/ }))
    expect(onChange).toHaveBeenCalledWith('afternoon')
  })
})
