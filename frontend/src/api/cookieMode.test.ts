import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { downloadAiUsageCsv } from './aiUsage'
import { login, logout } from './auth'
import { API_URL, request, setCsrfToken, setTokenProvider, setUnauthorizedHandler } from './client'
import { downloadDocument, setUploadTokenProvider, uploadDocument } from './documents'

// Cookie mode (US-104, ADR-018): the sign-in answer without `access_token` is the switch; the page holds only a
// CSRF value, in memory. Token mode is covered by client.test.ts and documents.test.ts, which are unchanged.

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status })
}
const csrfFailed = () => reply(403, { error: { code: 'csrf_failed', message: 'Reload the page and try again.' } })
const user = { id: 'u1', email: 'o@permitflow.example.sg', full_name: 'Op', role: 'operator' as const }

describe('cookie mode: the client', () => {
  const fetchMock = vi.fn<typeof fetch>()
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    setTokenProvider(() => null)
    setUploadTokenProvider(() => null)
    setUnauthorizedHandler(() => undefined)
    setCsrfToken('csrf-1')
  })
  afterEach(() => {
    setCsrfToken(null)
    vi.unstubAllGlobals()
    fetchMock.mockReset()
    sessionStorage.clear()
    localStorage.clear()
  })

  const init = (n = 0) => fetchMock.mock.calls[n][1]!
  const headers = (n = 0) => init(n).headers as Record<string, string>

  it('includes credentials, sends no Authorization header and stores nothing', async () => {
    fetchMock.mockResolvedValue(reply(200, {}))
    await request('/things')
    expect(init().credentials).toBe('include')
    expect(headers().Authorization).toBeUndefined()
    expect(sessionStorage.length).toBe(0)
    expect(localStorage.length).toBe(0)
  })

  it('sends X-CSRF-Token on POST, PUT, PATCH and DELETE but not on GET', async () => {
    fetchMock.mockImplementation(async () => reply(200, {}))
    await request('/a')
    for (const method of ['POST', 'PUT', 'PATCH', 'DELETE'] as const) await request('/a', { method, body: {} })
    expect(headers(0)['X-CSRF-Token']).toBeUndefined()
    for (const n of [1, 2, 3, 4]) {
      expect(headers(n)['X-CSRF-Token']).toBe('csrf-1')
      expect(init(n).credentials).toBe('include')
    }
  })

  it('on 403 csrf_failed reads /auth/me for a fresh value and retries once', async () => {
    fetchMock
      .mockResolvedValueOnce(csrfFailed())
      .mockResolvedValueOnce(reply(200, { ...user, csrf_token: 'csrf-2' }))
      .mockResolvedValueOnce(reply(200, { ok: true }))
    await expect(request('/things', { method: 'POST', body: { a: 1 } })).resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(fetchMock.mock.calls[1][0]).toBe(`${API_URL}/auth/me`)
    expect(headers(0)['X-CSRF-Token']).toBe('csrf-1')
    expect(headers(2)['X-CSRF-Token']).toBe('csrf-2')
    expect(init(2).body).toBe('{"a":1}')
  })

  it('surfaces csrf_failed when the retry fails again, without a third attempt', async () => {
    fetchMock
      .mockResolvedValueOnce(csrfFailed())
      .mockResolvedValueOnce(reply(200, { ...user, csrf_token: 'csrf-2' }))
      .mockResolvedValueOnce(csrfFailed())
    await expect(request('/things', { method: 'POST' })).rejects.toMatchObject({ status: 403, code: 'csrf_failed' })
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('still hands 401 session_revoked to the unauthorized handler', async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    fetchMock.mockResolvedValue(reply(401, { error: { code: 'session_revoked', message: 'x', details: { reason: 'taken_over' } } }))
    await expect(request('/things')).rejects.toMatchObject({ status: 401 })
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({ code: 'session_revoked' }))
  })

  it('logout posts with the CSRF header and credentials', async () => {
    fetchMock.mockResolvedValue(reply(204))
    await logout()
    expect(fetchMock.mock.calls[0][0]).toBe(`${API_URL}/auth/logout`)
    expect(init().method).toBe('POST')
    expect(headers()['X-CSRF-Token']).toBe('csrf-1')
    expect(init().credentials).toBe('include')
  })

  it('downloads include credentials and send no token', async () => {
    fetchMock.mockImplementation(async () => new Response('x', { status: 200 }))
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => undefined }))
    await downloadDocument('a', 'd', 'f.pdf')
    await downloadAiUsageCsv({ user: '', reference: '', from: '', to: '' })
    for (const n of [0, 1]) {
      expect(init(n).credentials).toBe('include')
      expect(headers(n).Authorization).toBeUndefined()
      expect(headers(n)['X-CSRF-Token']).toBeUndefined()
    }
  })
})

class FakeXhr {
  static instances: FakeXhr[] = []
  status = 0
  responseText = ''
  withCredentials = false
  upload = { onprogress: null }
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  headers: Record<string, string> = {}
  constructor() {
    FakeXhr.instances.push(this)
  }
  open(): void {}
  setRequestHeader(k: string, v: string): void {
    this.headers[k] = v
  }
  getResponseHeader(): string | null {
    return null
  }
  send(): void {}
}

describe('cookie mode: uploads over XMLHttpRequest', () => {
  const fetchMock = vi.fn<typeof fetch>()
  beforeEach(() => {
    FakeXhr.instances = []
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    vi.stubGlobal('fetch', fetchMock)
    setUploadTokenProvider(() => null)
    setCsrfToken('csrf-1')
  })
  afterEach(() => {
    setCsrfToken(null)
    vi.unstubAllGlobals()
    fetchMock.mockReset()
  })
  const pdf = () => new File([new Uint8Array(10)], 'plan.pdf', { type: 'application/pdf' })

  it('sets withCredentials and X-CSRF-Token, and no Authorization', () => {
    void uploadDocument('app', 'floor_plan', pdf(), () => undefined)
    const xhr = FakeXhr.instances[0]
    expect(xhr.withCredentials).toBe(true)
    expect(xhr.headers['X-CSRF-Token']).toBe('csrf-1')
    expect(xhr.headers.Authorization).toBeUndefined()
  })

  it('on csrf_failed refreshes the value and sends the upload once more', async () => {
    fetchMock.mockImplementation(async () => reply(200, { ...user, csrf_token: 'csrf-2' }))
    const done = uploadDocument('app', 'floor_plan', pdf(), () => undefined)
    const first = FakeXhr.instances[0]
    first.status = 403
    first.responseText = JSON.stringify({ error: { code: 'csrf_failed', message: 'Reload.' } })
    first.onload?.()
    await vi.waitFor(() => expect(FakeXhr.instances).toHaveLength(2))
    const second = FakeXhr.instances[1]
    expect(second.headers['X-CSRF-Token']).toBe('csrf-2')
    second.status = 200
    second.responseText = '{"unchanged":false}'
    second.onload?.()
    await expect(done).resolves.toEqual({ unchanged: false })
  })
})

describe('the sign-in response decides the mode', () => {
  const fetchMock = vi.fn<typeof fetch>()
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    setTokenProvider(() => null)
    setCsrfToken(null)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    fetchMock.mockReset()
  })

  it('tries the sign-in with credentials first so a cookie server can set its cookie', async () => {
    fetchMock.mockImplementation(async () => reply(200, { expires_at: 'x', user, csrf_token: 'c' }))
    const out = await login(user.email, 'pw')
    expect(fetchMock.mock.calls[0][1]!.credentials).toBe('include')
    expect('access_token' in out).toBe(false)
  })

  // Last in the file: the "server refuses credentials" memory lives for the page load.
  it('falls back to a plain request when a token server refuses credentialed ones', async () => {
    fetchMock
      .mockRejectedValueOnce(new TypeError('Failed to fetch'))
      .mockResolvedValueOnce(reply(200, { access_token: 't', token_type: 'bearer', expires_at: 'x', user }))
    const out = await login(user.email, 'pw')
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[1][1]!.credentials).toBeUndefined()
    expect('access_token' in out).toBe(true)
  })
})
