/**
 * WCAG 2.4.7 / 1.4.11 (audit of 9 Oct 2026): no button, toggle or checkbox may switch the global focus outline
 * off (`outline-hidden`, `outline-none`). A faint halo had replaced it on the hours picker, the site visit slots,
 * the checklist results and the checkbox (1.36:1). Text inputs and selects are the one exception: they swap the
 * outline for a border in the focus colour plus a halo, and Tailwind's `outline-hidden` still draws a transparent
 * outline in forced-colours mode. The skip targets (`main`, the error summary) take programmatic focus only.
 */
import { describe, expect, it } from 'vitest'

const sources = import.meta.glob<string>('/src/**/*.tsx', { query: '?raw', import: 'default', eager: true })

/** Files allowed to carry the suppression, with the reason. */
const ALLOWED: Record<string, string> = {
  '/src/features/shared/Field.tsx': 'text input: border in the focus colour, halo and a forced-colours outline',
  '/src/features/shared/SearchBox.tsx': 'search input: the same',
  '/src/app/AppShell.tsx': '<main tabIndex={-1}>, focused by the skip link only',
  '/src/features/landing/LandingPage.tsx': '<main tabIndex={-1}>',
  '/src/features/shared/NotFoundPage.tsx': '<main tabIndex={-1}>',
  '/src/features/releases/ReleasesPage.tsx': '<main tabIndex={-1}>',
  '/src/features/legal/PolicyPage.tsx': '<main tabIndex={-1}>',
  '/src/features/operator/SectionForm.tsx': 'the error summary, focused by code',
}

describe('focus outline', () => {
  it('is never suppressed on a button, toggle or checkbox', () => {
    const offenders = Object.entries(sources)
      .filter(([path, text]) => !path.endsWith('.test.tsx') && /outline-(hidden|none)/.test(text) && !(path in ALLOWED))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('leaves the hours picker, slot buttons, checklist results and checkbox on the global 2px outline', () => {
    for (const path of [
      '/src/features/operator/HoursField.tsx',
      '/src/features/shared/SiteVisit.tsx',
      '/src/features/officer/ChecklistPage.tsx',
      '/src/features/shared/Controls.tsx',
    ]) {
      const text = sources[path] ?? ''
      expect(text, path).not.toBe('')
      expect(text, path).not.toMatch(/focus-visible:outline-(hidden|none)/)
      expect(text, path).not.toMatch(/focus-visible:shadow-\[0_0_0_3px_rgba\(23,92,211,0\.2\)\]/)
    }
  })
})
