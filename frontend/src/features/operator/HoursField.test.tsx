import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { vi } from 'vitest'

import type { HoursValue } from '@/lib/hours'
import { EMPTY_HOURS, HoursField } from './HoursField'

const sixDays: HoursValue = { days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat'], opens: '07:00', closes: '21:00', open_24h: false }

/** The picker wired to state, the way the form holds it, so each click shows its result. */
function Harness({ initial, onChange = () => {}, error }: { initial?: HoursValue; onChange?: (v: HoursValue) => void; error?: string }) {
  const [value, setValue] = useState<HoursValue | undefined>(initial)
  return (
    <HoursField
      label="Operating hours"
      required
      value={value}
      error={error}
      onChange={(v) => {
        setValue(v)
        onChange(v)
      }}
    />
  )
}

const day = (name: string) => screen.getByRole('button', { name })

describe('HoursField', () => {
  it('shows seven day toggles with their pressed state, and the summary the officer will read', () => {
    render(<Harness initial={sixDays} />)
    expect(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].every((d) => day(d).getAttribute('aria-pressed') === 'true')).toBe(true)
    expect(day('Sun')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText('Mon to Sat, 07:00 to 21:00')).toBeInTheDocument()
    expect(screen.getByText('Shown to the officer as')).toBeInTheDocument()
  })

  it('toggles a day and keeps the week in order', async () => {
    const onChange = vi.fn()
    render(<Harness initial={{ ...sixDays, days: ['mon', 'fri'] }} onChange={onChange} />)
    await userEvent.click(day('Wed'))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ days: ['mon', 'wed', 'fri'] }))
    await userEvent.click(day('Mon'))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ days: ['wed', 'fri'] }))
    expect(day('Mon')).toHaveAttribute('aria-pressed', 'false')
  })

  it('quick links set Every day, Mon to Fri and Clear', async () => {
    const onChange = vi.fn()
    render(<Harness initial={EMPTY_HOURS} onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: 'Every day' }))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] }))
    await userEvent.click(screen.getByRole('button', { name: 'Mon to Fri' }))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ days: ['mon', 'tue', 'wed', 'thu', 'fri'] }))
    await userEvent.click(screen.getByRole('button', { name: 'Clear' }))
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ days: [] }))
  })

  it('offers 48 half-hour times in each list and reports the pick', async () => {
    const onChange = vi.fn()
    render(<Harness initial={EMPTY_HOURS} onChange={onChange} />)
    const opens = screen.getByLabelText('Opens')
    const closes = screen.getByLabelText('Closes')
    expect(opens.querySelectorAll('option')).toHaveLength(49) // 48 times and the prompt
    expect(closes.querySelectorAll('option')).toHaveLength(49)
    await userEvent.selectOptions(opens, '07:30')
    await userEvent.selectOptions(closes, '23:30')
    expect(onChange).toHaveBeenLastCalledWith({ days: [], opens: '07:30', closes: '23:30', open_24h: false })
  })

  it('Open 24 hours hides the times, and unticking brings back the last ones', async () => {
    render(<Harness initial={sixDays} />)
    const box = screen.getByRole('checkbox', { name: 'Open 24 hours' })
    await userEvent.click(box)
    expect(screen.queryByLabelText('Opens')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Closes')).not.toBeInTheDocument()
    expect(screen.getByText('Mon to Sat, open 24 hours')).toBeInTheDocument()
    await userEvent.click(box)
    expect(screen.getByLabelText('Opens')).toHaveValue('07:00')
    expect(screen.getByLabelText('Closes')).toHaveValue('21:00')
  })

  it('says when the shop closes after midnight', async () => {
    render(<Harness initial={{ ...sixDays, opens: '18:00', closes: '21:00' }} />)
    expect(screen.queryByText(/Closes after midnight/)).not.toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Closes'), '02:00')
    expect(screen.getByText('Closes after midnight, at 02:00 the next day.')).toBeInTheDocument()
    expect(screen.getByText('Mon to Sat, 18:00 to 02:00 (next day)')).toBeInTheDocument()
  })

  it('puts a days error under the days and a times error under the times', () => {
    const { rerender } = render(<Harness initial={EMPTY_HOURS} error="Choose at least one day you open." />)
    expect(screen.getByRole('alert')).toHaveTextContent('Choose at least one day you open.')
    expect(day('Mon')).toHaveAttribute('aria-pressed', 'false')
    rerender(<Harness initial={sixDays} error="Opening and closing time cannot be the same." />)
    expect(screen.getByRole('alert')).toHaveTextContent('Opening and closing time cannot be the same.')
    expect(screen.getByLabelText('Opens')).toHaveAttribute('aria-invalid', 'true')
  })

  it('names an older free-text entry once so it can be re-picked', () => {
    render(
      <HoursField label="Operating hours" required value={undefined} onChange={() => {}} legacy="Mon-Sun 7am-9pm" />,
    )
    expect(screen.getByText(/Your earlier entry was/)).toHaveTextContent('Mon-Sun 7am-9pm')
  })

  it('on a read-only section shows the older entry as saved, with no instruction to pick', () => {
    render(
      <HoursField label="Operating hours" required value={undefined} onChange={() => {}} legacy="Mon-Sun 7am-9pm" disabled />,
    )
    expect(screen.getByText(/Saved as/)).toHaveTextContent('Saved as “Mon-Sun 7am-9pm”.')
    expect(screen.queryByText(/Pick your opening days/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Your earlier entry was/)).not.toBeInTheDocument()
  })

  it('does nothing when disabled', async () => {
    const onChange = vi.fn()
    render(<HoursField label="Operating hours" required value={sixDays} onChange={onChange} disabled />)
    await userEvent.click(day('Sun'))
    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Opens')).toBeDisabled()
  })

  describe('accessibility (audit of 9 Oct 2026)', () => {
    it('keeps both live regions in the page, empty, and only fills them (WCAG 4.1.3)', async () => {
      const { container } = render(<Harness initial={{ ...sixDays, days: [], opens: null, closes: null }} />)
      const status = container.querySelector('[role="status"]')
      const summary = container.querySelector('[aria-live="polite"]')
      expect(status).not.toBeNull()
      expect(summary).not.toBeNull()
      expect(status).toBeEmptyDOMElement()
      expect(summary).toBeEmptyDOMElement()

      await userEvent.click(day('Mon'))
      await userEvent.selectOptions(screen.getByLabelText('Opens'), '18:00')
      await userEvent.selectOptions(screen.getByLabelText('Closes'), '02:00')
      // The same two elements, now carrying the hint and the summary: the page did not insert new regions.
      expect(container.querySelector('[role="status"]')).toBe(status)
      expect(container.querySelector('[aria-live="polite"]')).toBe(summary)
      expect(status).toHaveTextContent('Closes after midnight, at 02:00 the next day.')
      expect(summary).toHaveTextContent('Shown to the officer as')
      // The alert inside does not announce itself a second time.
      expect(status?.querySelector('[role]')).toBeNull()

      await userEvent.selectOptions(screen.getByLabelText('Closes'), '21:00')
      expect(status).toBeEmptyDOMElement()
    })

    it('links the hours error to both time lists and to the day group', () => {
      const { rerender } = render(<Harness initial={sixDays} error="Opening and closing time cannot be the same." />)
      const errorId = screen.getByRole('alert').id
      expect(errorId).not.toBe('')
      expect(screen.getByLabelText('Opens')).toHaveAttribute('aria-describedby', errorId)
      expect(screen.getByLabelText('Closes')).toHaveAttribute('aria-describedby', errorId)
      rerender(<Harness initial={EMPTY_HOURS} error="Choose at least one day you open." />)
      expect(screen.getByRole('group', { name: 'Open on' })).toHaveAttribute('aria-describedby', screen.getByRole('alert').id)
      expect(screen.getByLabelText('Opens')).not.toHaveAttribute('aria-describedby')
    })

    it('shows the check on a pressed day at every width, not only from sm up', () => {
      render(<Harness initial={{ ...sixDays, days: ['mon'] }} />)
      const check = day('Mon').querySelector('svg')
      expect(check).not.toBeNull()
      expect(check?.closest('.hidden')).toBeNull()
      expect(day('Tue').querySelector('svg')).toBeNull()
    })

    it('reports a blur only when focus leaves the picker, not between its own controls', async () => {
      const onBlur = vi.fn()
      render(
        <>
          <HoursField label="Operating hours" required value={sixDays} onChange={() => {}} onBlur={onBlur} />
          <button type="button">After</button>
        </>,
      )
      day('Mon').focus()
      await userEvent.tab()
      expect(day('Tue')).toHaveFocus()
      expect(onBlur).not.toHaveBeenCalled()
      screen.getByRole('button', { name: 'After' }).focus()
      expect(onBlur).toHaveBeenCalledTimes(1)
    })
  })
})
