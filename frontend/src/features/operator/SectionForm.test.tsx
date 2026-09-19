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

  const mixed: SectionDef = {
    key: 'premises',
    title: 'Premises',
    description: '',
    fields: [
      {
        key: 'premises_type',
        label: 'Premises type',
        kind: 'select',
        required: true,
        max_length: null,
        pattern: null,
        pattern_message: null,
        options: [
          { value: 'shophouse', label: 'Shophouse' },
          { value: 'mall_unit', label: 'Mall unit' },
        ],
        min_value: null,
        max_value: null,
        help: null,
        must_be_true: false,
      },
      {
        key: 'floor_area_sqm',
        label: 'Floor area (sqm)',
        kind: 'number',
        required: true,
        max_length: null,
        pattern: null,
        pattern_message: null,
        options: [],
        min_value: 1,
        max_value: 10000,
        help: 'Whole premises',
        must_be_true: false,
      },
      {
        key: 'seating',
        label: 'Seating capacity',
        kind: 'integer',
        required: false,
        max_length: null,
        pattern: null,
        pattern_message: null,
        options: [],
        min_value: 0,
        max_value: 500,
        help: null,
        must_be_true: false,
      },
      {
        key: 'tenancy_expiry',
        label: 'Tenancy expiry date',
        kind: 'date',
        required: true,
        max_length: null,
        pattern: null,
        pattern_message: null,
        options: [],
        min_value: null,
        max_value: null,
        help: null,
        must_be_true: false,
      },
      {
        key: 'cuisine',
        label: 'Description of food',
        kind: 'textarea',
        required: true,
        max_length: 500,
        pattern: null,
        pattern_message: null,
        options: [],
        min_value: null,
        max_value: null,
        help: null,
        must_be_true: false,
      },
      {
        key: 'accurate',
        label: 'I confirm the information is accurate.',
        kind: 'checkbox',
        required: true,
        max_length: null,
        pattern: null,
        pattern_message: null,
        options: [],
        min_value: null,
        max_value: null,
        help: null,
        must_be_true: true,
      },
    ],
  }

  it('renders every field kind from the server schema and enforces range, option and declaration rules on continue', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined)
    render(<SectionForm section={mixed} data={{}} editable saving={false} onSave={onSave} onDirtyChange={() => {}} />)
    await userEvent.selectOptions(screen.getByLabelText(/Premises type/), 'mall_unit')
    await userEvent.type(screen.getByLabelText(/Floor area/), '20000')
    await userEvent.type(screen.getByLabelText(/Seating capacity/), '12')
    await userEvent.type(screen.getByLabelText(/Tenancy expiry date/), '2027-10-31')
    await userEvent.type(screen.getByLabelText(/Description of food/), 'Kaya toast and kopi.')
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    // The range rule fails at the field level, before anything is sent.
    expect(await screen.findByText(/at most 10000/)).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()

    await userEvent.clear(screen.getByLabelText(/Floor area/))
    await userEvent.type(screen.getByLabelText(/Floor area/), '48')
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    // A valid draft still cannot continue while the declaration is unticked (complete-mode rule).
    expect(await screen.findByText(/1 field needs attention/)).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()

    await userEvent.click(screen.getByLabelText(/I confirm the information is accurate/))
    await userEvent.click(screen.getByRole('button', { name: 'Save and continue' }))
    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith(
        expect.objectContaining({
          premises_type: 'mall_unit',
          floor_area_sqm: 48,
          seating: 12,
          tenancy_expiry: '2027-10-31',
          accurate: true,
        }),
        true,
      ),
    )
  })

  it('keeps unsaved edits when the server data changes underneath, and can discard them', async () => {
    const { rerender } = render(
      <SectionForm
        section={business}
        data={{ business_name: 'Old Name' }}
        editable
        saving={false}
        onSave={vi.fn()}
        onDirtyChange={() => {}}
      />,
    )
    await userEvent.clear(screen.getByLabelText(/Business name/))
    await userEvent.type(screen.getByLabelText(/Business name/), 'My Edit')
    rerender(
      <SectionForm
        section={business}
        data={{ business_name: 'Other Tab Name' }}
        editable
        saving={false}
        onSave={vi.fn()}
        onDirtyChange={() => {}}
      />,
    )
    expect(await screen.findByText('This section was updated elsewhere')).toBeInTheDocument()
    expect(screen.getByLabelText(/Business name/)).toHaveValue('My Edit')
    await userEvent.click(screen.getByRole('button', { name: 'Discard my edits' }))
    expect(screen.getByLabelText(/Business name/)).toHaveValue('Other Tab Name')
    expect(screen.queryByText('This section was updated elsewhere')).not.toBeInTheDocument()
  })

  it('shows a server refusal inline and keeps the input', async () => {
    const onSave = vi.fn().mockRejectedValue(new Error('This application can no longer be edited.'))
    render(<SectionForm section={business} data={{}} editable saving={false} onSave={onSave} onDirtyChange={() => {}} />)
    await userEvent.type(screen.getByLabelText(/Business name/), 'Kopi House')
    await userEvent.click(screen.getByRole('button', { name: 'Save section' }))
    expect(await screen.findByText(/can no longer be edited/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Business name/)).toHaveValue('Kopi House')
  })
})
