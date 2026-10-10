import { describe, expect, it } from 'vitest'

import type { PlatformSetting } from '@/api/admin'
import { AppError } from '@/api/client'
import {
  BYTES_PER_MB,
  boundError,
  formatSpan,
  formatValue,
  formatWhen,
  inputText,
  parseNumber,
  rangeText,
  saidInMegabytes,
  writeFailure,
} from './settingsFormat'

const base: PlatformSetting = {
  key: 'rate_limit_per_minute',
  label: 'Requests per minute per client',
  description: '',
  group: 'traffic',
  kind: 'int',
  unit: 'requests',
  value: 180,
  default: 240,
  overridden: true,
  minimum: 10,
  maximum: 1240,
  max_source: 'env',
  choices: [],
  in_use: true,
  updated_by_name: null,
  updated_at: null,
  reason: null,
}
const upload: PlatformSetting = { ...base, key: 'upload_max_bytes', label: 'Upload size', unit: 'bytes', minimum: BYTES_PER_MB, maximum: 10 * BYTES_PER_MB, max_source: 'cap' }

describe('settings values', () => {
  it('writes numbers with separators, switches and choices in words, sizes in megabytes', () => {
    expect(formatValue(base, 1240)).toBe('1,240')
    expect(formatValue(base, true)).toBe('On')
    expect(formatValue(base, 'closed')).toBe('Closed')
    expect(formatValue(upload, 10 * BYTES_PER_MB)).toBe('10 MB')
    expect(formatValue(upload, 2.5 * BYTES_PER_MB)).toBe('2.5 MB')
    expect(rangeText(upload)).toBe('1 MB to 10 MB')
    expect(rangeText(base)).toBe('10 to 1,240')
    expect(inputText(upload, 5 * BYTES_PER_MB)).toBe('5')
  })

  it('turns the typed megabytes into bytes, and refuses what is not a number', () => {
    expect(parseNumber(upload, '5')).toEqual({ value: 5242880 })
    expect(parseNumber(upload, ' 2.5 ')).toEqual({ value: 2621440 })
    expect(parseNumber(upload, 'ten').error).toMatch(/number of megabytes/)
    expect(parseNumber(base, '180')).toEqual({ value: 180 })
    expect(parseNumber(base, '1.5').error).toBe('Requests per minute per client must be a whole number.')
    expect(parseNumber(base, '').error).toBe('Requests per minute per client must be a whole number.')
  })

  it('says a bound the way the server does, in megabytes for a size', () => {
    expect(boundError(base, 9)).toBe('Requests per minute per client cannot go below 10; a limit cannot be switched off from the panel.')
    expect(boundError(base, 1241)).toBe('Requests per minute per client cannot go above 1,240 (the environment ceiling).')
    expect(boundError(base, 50)).toBeNull()
    expect(boundError(upload, 11 * BYTES_PER_MB)).toBe('Upload size cannot go above 10 MB (the absolute cap).')
    expect(saidInMegabytes(upload, 'Upload size cannot go above 10485760 (the absolute cap).')).toBe(
      'Upload size cannot go above 10 MB (the absolute cap).',
    )
  })

  it('files a refused write under the field it belongs to', () => {
    expect(writeFailure(new AppError(403, { code: 'step_up_failed', message: 'Wrong.' }), base)).toEqual({ field: 'password', message: 'Wrong.' })
    expect(writeFailure(new AppError(429, { code: 'rate_limited', message: 'Slow down.' }), base).field).toBe('password')
    expect(
      writeFailure(new AppError(422, { code: 'validation_failed', message: 'Too low.', details: { reason: 'below_minimum' } }), base).field,
    ).toBe('value')
    expect(writeFailure(new AppError(500, { code: 'internal_error', message: 'Broke.' }), base).field).toBe('general')
    expect(writeFailure(new Error('x'), base)).toEqual({ field: 'general', message: 'Something went wrong. Try again.' })
  })

  it('writes times in Singapore and spans in hours and minutes', () => {
    expect(formatWhen('2026-10-10T01:14:00Z')).toBe('10 Oct 2026, 09:14')
    expect(formatSpan(178 * 60_000)).toBe('2 h 58 min')
    expect(formatSpan(12 * 60_000)).toBe('12 min')
    expect(formatSpan(2 * 3_600_000)).toBe('2 h')
    expect(formatSpan(5_000)).toBe('under a minute')
  })
})
