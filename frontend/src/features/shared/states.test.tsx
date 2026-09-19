import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { AppError } from '@/api/client'
import { EmptyPanel, ErrorPanel, NotFoundPanel } from './states'

describe('page states (UI_STATES.md)', () => {
  it('shows the server message, the request id for support, and a retry when one is offered', async () => {
    const onRetry = vi.fn()
    render(
      <ErrorPanel error={new AppError(503, { code: 'db_unavailable', message: 'The database is busy.' }, 'req-42')} onRetry={onRetry} />,
    )
    expect(screen.getByText(/The database is busy\. Nothing you entered has been lost\./)).toBeInTheDocument()
    expect(screen.getByText('Request ID req-42')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('falls back to a generic message for unknown errors and offers no retry without a handler', () => {
    render(<ErrorPanel error="boom" />)
    expect(screen.getByText(/Something went wrong\./)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })

  it("links Not found back to the caller's list", () => {
    render(
      <MemoryRouter>
        <NotFoundPanel backTo="/app/applications" backLabel="Back to my applications" />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'Back to my applications' })).toHaveAttribute('href', '/app/applications')
  })

  it('renders an empty state with its action', () => {
    render(
      <MemoryRouter>
        <EmptyPanel
          title="No applications yet"
          description="Start your first application."
          action={<a href="/app/new">New application</a>}
        />
      </MemoryRouter>,
    )
    expect(screen.getByText('No applications yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'New application' })).toBeInTheDocument()
  })
})
