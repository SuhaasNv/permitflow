import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Button } from './Button'

describe('Button while loading (WCAG 2.4.3)', () => {
  it('is aria-disabled and busy, not disabled, so it keeps keyboard focus', async () => {
    const { rerender } = render(<Button>Sign in</Button>)
    const button = screen.getByRole('button', { name: 'Sign in' })
    await userEvent.tab()
    expect(button).toHaveFocus()
    rerender(<Button loading>Sign in</Button>)
    expect(button).toHaveAttribute('aria-disabled', 'true')
    expect(button).toHaveAttribute('aria-busy', 'true')
    expect(button).not.toBeDisabled()
    expect(button).toHaveFocus()
  })

  it('swallows clicks, so a second press sends nothing', async () => {
    const onClick = vi.fn()
    render(
      <Button loading onClick={onClick}>
        Save
      </Button>,
    )
    await userEvent.click(screen.getByRole('button', { name: 'Save' }))
    await userEvent.keyboard('{Enter}')
    expect(onClick).not.toHaveBeenCalled()
  })

  it('does not submit its form while loading, and does when it is not', () => {
    const onSubmit = vi.fn((e: { preventDefault: () => void }) => e.preventDefault())
    const { rerender } = render(
      <form onSubmit={onSubmit}>
        <Button type="submit" loading>
          Go
        </Button>
      </form>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Go' }))
    expect(onSubmit).not.toHaveBeenCalled()
    rerender(
      <form onSubmit={onSubmit}>
        <Button type="submit">Go</Button>
      </form>,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Go' }))
    expect(onSubmit).toHaveBeenCalledTimes(1)
  })

  it('stays truly disabled when disabled is passed', () => {
    render(<Button disabled>Nope</Button>)
    expect(screen.getByRole('button', { name: 'Nope' })).toBeDisabled()
  })
})
