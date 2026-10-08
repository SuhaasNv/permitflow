import { act, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { RELEASE_NOTES } from './ReleasesPage'
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
    const [rail, strip] = screen.getAllByRole('link', { name: new RegExp(`^v${__APP_VERSION__.replace(/\./g, '\\.')}.*what's new$`, 'i') })
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

  it('the New mark follows this build only; candidate sections in the notes never count, so production never shows it for a test build (US-110)', () => {
    // The real notes hold candidate sections; the chip must not look at them.
    expect(RELEASE_NOTES.releases.some((r) => r.candidate)).toBe(true)
    render(
      <MemoryRouter>
        <VersionChip variant="rail" />
      </MemoryRouter>,
    )
    const chip = screen.getByRole('link', { name: /what's new$/i })
    expect(chip).toHaveTextContent('New')
    // Having read this build's release, the mark clears even though candidate sections sit in the file.
    act(() => markReleaseSeen(__APP_VERSION__))
    expect(chip).toHaveTextContent("What's new")
    expect(chip).not.toHaveTextContent(/\bNew\b/)
    // A candidate's own version being "seen" does not clear a production build's mark.
    act(() => markReleaseSeen('0.4.0-rc.2'))
    expect(chip).toHaveTextContent('New')
  })
})
