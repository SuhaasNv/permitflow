import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { markReleaseSeen } from './seen'
import { VersionChip } from './VersionChip'

describe('VersionChip (US-094)', () => {
  afterEach(() => localStorage.clear())

  it('links to What\'s new, says New until the page is read, then What\'s new; the strip variant shows the chip alone', () => {
    render(
      <MemoryRouter>
        <VersionChip variant="rail" />
        <VersionChip variant="strip" />
      </MemoryRouter>,
    )
    const [rail, strip] = screen.getAllByRole('link', { name: `Version ${__APP_VERSION__}, what's new` })
    expect(rail).toHaveAttribute('href', '/releases')
    expect(rail).toHaveTextContent(`v${__APP_VERSION__}`)
    expect(rail).toHaveTextContent('New')
    expect(strip).toHaveTextContent('New')
    act(() => markReleaseSeen(__APP_VERSION__))
    expect(rail).toHaveTextContent("What's new")
    expect(rail).not.toHaveTextContent(/\bNew\b/)
    expect(strip).not.toHaveTextContent('New')
    expect(strip).not.toHaveTextContent("What's new")
  })
})
