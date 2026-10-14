import { describe, expect, it } from 'vitest'
import { isTransient } from './connection'

describe('isTransient', () => {
  it('retries a lost connection and a server that is busy', () => {
    expect(isTransient(null)).toBe(true)
    expect(isTransient({ status: 0 })).toBe(true)
    expect(isTransient({ status: 503 })).toBe(true)
    expect(isTransient({ status: 408 })).toBe(true)
    expect(isTransient({ status: 429 })).toBe(true)
  })

  it('does not retry storage_full (507) or a rejected request', () => {
    expect(isTransient({ status: 507 })).toBe(false)
    expect(isTransient({ status: 413 })).toBe(false)
    expect(isTransient({ status: 422 })).toBe(false)
  })
})
