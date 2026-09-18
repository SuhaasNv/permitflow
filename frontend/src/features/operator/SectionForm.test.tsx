import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'

import type { SectionDef } from '@/api/formSchema'
import { SectionForm } from './SectionForm'

const business: SectionDef = {
  key: 'business',
  title: 'Business details',
  description: '',
  fields: [
    {
      key: 'business_name',
      label: 'Business name',
      kind: 'text',
      required: true,
      max_length: 120,
      pattern: null,
      pattern_message: null,
      options: [],
      min_value: null,
      max_value: null,
      help: null,
      must_be_true: false,
    },
    {
      key: 'uen',
      label: 'UEN',
      kind: 'text',
      required: true,
      max_length: null,
      pattern: '^[0-9]{8,9}[A-Z]$',
      pattern_message: 'Enter a valid UEN.',
      options: [],
      min_value: null,
      max_value: null,
      help: null,
      must_be_true: false,
    },
  ],
}

describe('SectionForm', () => {
  it('blocks "Save and continue" with a summary when required fields are empty', async () => {
    const onSave = vi.fn()
    render(<SectionForm section={business} data={{}} editable saving={false} onSave={onSave} onDirtyChange={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    expect(await screen.findByText(/2 fields need attention/)).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
  })

  it('"Save section" saves a partial draft but rejects bad formats', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<SectionForm section={business} data={{}} editable saving={false} onSave={onSave} onDirtyChange={() => {}} />)
    await userEvent.type(screen.getByLabelText(/UEN/), 'abc')
    await userEvent.click(screen.getByRole('button', { name: 'Save section' }))
    expect(await screen.findByText('Enter a valid UEN.')).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
    await userEvent.clear(screen.getByLabelText(/UEN/))
    await userEvent.type(screen.getByLabelText(/Business name/), 'Kopi House')
    await userEvent.click(screen.getByRole('button', { name: 'Save section' }))
    await waitFor(() => expect(onSave).toHaveBeenCalledWith({ business_name: 'Kopi House' }, false))
  })
})
