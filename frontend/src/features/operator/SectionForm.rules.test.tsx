/** US-108: the form built from the server's real definition (the one in the shared fixture). */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import raw from 'virtual:form-rules-fixture'
import { vi } from 'vitest'

import type { FormSchema, SectionDef } from '@/api/formSchema'
import { SectionForm } from './SectionForm'

const schema = (JSON.parse(raw) as { schema: FormSchema }).schema
const section = (key: string): SectionDef => {
  const s = schema.sections.find((x) => x.key === key)
  if (!s) throw new Error(key)
  return s
}

const renderForm = (key: string, data: Record<string, unknown> = {}, onSave = vi.fn().mockResolvedValue(undefined)) => {
  render(<SectionForm section={section(key)} data={data} editable saving={false} onSave={onSave} onDirtyChange={() => {}} />)
  return onSave
}

const PHONE = 'Enter a Singapore number: 8 digits starting with 3, 6, 8 or 9, for example +65 9123 4567.'

describe('SectionForm with the Singapore rules', () => {
  it('names a wrong phone number while it is typed, and clears the message once it is right', async () => {
    renderForm('business')
    const phone = screen.getByLabelText(/Contact phone/)
    expect(phone).toHaveAttribute('inputmode', 'tel')
    expect(phone).toHaveAttribute('autocomplete', 'tel')
    expect(phone).toHaveAttribute('type', 'tel')
    await userEvent.type(phone, '+65 1234')
    expect(await screen.findByText(PHONE)).toBeInTheDocument()
    await userEvent.clear(phone)
    await userEvent.type(phone, '9123 4567')
    await waitFor(() => expect(screen.queryByText(PHONE)).not.toBeInTheDocument())
  })

  it('checks the UEN as it is typed, in any of the three ACRA formats', async () => {
    renderForm('business')
    const uen = screen.getByLabelText(/UEN/)
    await userEvent.type(uen, '2023')
    expect(await screen.findByText('Enter a valid UEN, for example 202312345K.')).toBeInTheDocument()
    await userEvent.clear(uen)
    await userEvent.type(uen, 't08ll0001a')
    await waitFor(() => expect(screen.queryByText(/Enter a valid UEN/)).not.toBeInTheDocument())
  })

  it('gives the postal code a number pad and checks the sector', async () => {
    renderForm('premises')
    const postal = screen.getByLabelText(/Postal code/)
    expect(postal).toHaveAttribute('inputmode', 'numeric')
    await userEvent.type(postal, '831234')
    expect(await screen.findByText('Postal codes start with 01 to 82. Check the first two digits.')).toBeInTheDocument()
  })

  it('saves the hours picker as one object, and shows its summary', async () => {
    const onSave = renderForm('operations', {
      cuisine_description: 'Kaya toast, soft-boiled eggs, kopi and teh.',
      seating_capacity: 24,
      food_handlers_count: 4,
    })
    await userEvent.click(screen.getByRole('button', { name: 'Every day' }))
    await userEvent.selectOptions(screen.getByLabelText('Opens'), '07:00')
    await userEvent.selectOptions(screen.getByLabelText('Closes'), '21:00')
    expect(screen.getByText('Every day, 07:00 to 21:00')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    await waitFor(() => expect(onSave).toHaveBeenCalled())
    expect(onSave.mock.calls[0]?.[0]).toEqual({
      cuisine_description: 'Kaya toast, soft-boiled eggs, kopi and teh.',
      seating_capacity: 24,
      food_handlers_count: 4,
      operating_hours: {
        days: ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'],
        opens: '07:00',
        closes: '21:00',
        open_24h: false,
      },
    })
  })

  it('blocks Save and continue when no day is chosen, and when the times are the same', async () => {
    const onSave = renderForm('operations', {
      cuisine_description: 'Kaya toast, soft-boiled eggs, kopi and teh.',
      seating_capacity: 24,
      food_handlers_count: 4,
    })
    await userEvent.selectOptions(screen.getByLabelText('Opens'), '09:00')
    await userEvent.selectOptions(screen.getByLabelText('Closes'), '09:00')
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    expect(await screen.findByText('Choose at least one day you open.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Mon to Fri' }))
    expect(await screen.findByText('Opening and closing time cannot be the same.')).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
  })

  it('shows an older free-text entry once and asks for a new pick', async () => {
    const onSave = renderForm('operations', {
      cuisine_description: 'Kaya toast, soft-boiled eggs, kopi and teh.',
      seating_capacity: 24,
      operating_hours: 'Mon-Sun 7am-9pm',
      food_handlers_count: 4,
    })
    expect(screen.getByText(/Your earlier entry was/)).toHaveTextContent('Mon-Sun 7am-9pm')
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    expect(await screen.findByText('This field is required.')).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
  })

  it('puts the server message on the hours picker when the server refuses it', async () => {
    const { AppError } = await import('@/api/client')
    const refuse = vi.fn().mockRejectedValue(
      new AppError(422, {
        code: 'validation_failed',
        message: 'Some fields need attention.',
        details: { fields: { operating_hours: 'Pick your opening days and hours.' } },
      }),
    )
    renderForm(
      'operations',
      {
        cuisine_description: 'Kaya toast, soft-boiled eggs, kopi and teh.',
        seating_capacity: 24,
        food_handlers_count: 4,
        operating_hours: { days: ['mon'], opens: '07:00', closes: '21:00', open_24h: false },
      },
      refuse,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Save section' }))
    expect(await screen.findAllByText('Pick your opening days and hours.')).not.toHaveLength(0)
  })
})
