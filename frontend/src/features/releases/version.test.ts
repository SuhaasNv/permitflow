import { afterEach, describe, expect, it, vi } from 'vitest'

import { appVersion } from './version'

describe('appVersion (US-111)', () => {
  afterEach(() => {
    delete window.__PERMITFLOW__
    vi.unstubAllGlobals()
  })

  it('falls back to the version compiled in when config.js carries none', () => {
    vi.stubGlobal('__APP_VERSION__', '0.5.0-rc.4')
    expect(appVersion()).toBe('0.5.0-rc.4')
    window.__PERMITFLOW__ = { apiUrl: 'https://api.example.com/api/v1' }
    expect(appVersion()).toBe('0.5.0-rc.4')
    window.__PERMITFLOW__ = { appVersion: '' }
    expect(appVersion()).toBe('0.5.0-rc.4')
  })

  it('prefers the version config.js carries, so a promoted candidate reports the release', () => {
    vi.stubGlobal('__APP_VERSION__', '0.5.0-rc.4')
    window.__PERMITFLOW__ = { appVersion: '0.5.0' }
    expect(appVersion()).toBe('0.5.0')
  })
})
