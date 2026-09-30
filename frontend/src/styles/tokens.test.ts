import { describe, expect, it } from 'vitest'

import css from './index.css?raw'

function token(name: string): string {
  const m = css.match(new RegExp(`--color-${name}:\\s*(#[0-9a-f]{6})`, 'i'))
  if (!m) throw new Error(`token ${name} not found`)
  return m[1]
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

describe('design tokens (US-095)', () => {
  it('control borders reach 3:1 against the surface and the page background (WCAG 1.4.11)', () => {
    expect(ratio(token('line-strong'), token('surface'))).toBeGreaterThanOrEqual(3)
    expect(ratio(token('line-strong'), token('bg'))).toBeGreaterThanOrEqual(3)
  })

  it('the focus colour reaches 3:1 against the surface and the page background', () => {
    expect(ratio(token('focus'), token('surface'))).toBeGreaterThanOrEqual(3)
    expect(ratio(token('focus'), token('bg'))).toBeGreaterThanOrEqual(3)
  })
})
