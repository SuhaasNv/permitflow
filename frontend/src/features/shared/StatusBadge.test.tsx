import { render, screen } from '@testing-library/react'

import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it('renders the label it is given and exposes the tone', () => {
    render(<StatusBadge label="Pending Site Visit" tone="info" />)
    const badge = screen.getByText('Pending Site Visit')
    expect(badge).toHaveAttribute('data-tone', 'info')
  })
})
