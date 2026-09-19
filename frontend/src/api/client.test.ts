import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { API_URL, AppError, request, setTokenProvider, setUnauthorizedHandler } from './client'

function response(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  const text = body === undefined ? '' : typeof body === 'string' ? body : JSON.stringify(body)
  return new Response(text, { status, headers })
}

describe('api client (REL-001 error envelope)', () => {
  const fetchMock = vi.fn<typeof fetch>()
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    setTokenProvider(() => null)
    setUnauthorizedHandler(() => undefined)
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    fetchMock.mockReset()
  })

  it('sends the bearer token and JSON body, and parses the JSON response', async () => {
    setTokenProvider(() => 'tok')
    fetchMock.mockResolvedValue(response(200, { ok: true }))
    const out = await request<{ ok: boolean }>('/things', { method: 'POST', body: { a: 1 } })
    expect(out).toEqual({ ok: true })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${API_URL}/things`)
    expect(init!.method).toBe('POST')
    expect((init!.headers as Record<string, string>).Authorization).toBe('Bearer tok')
    expect((init!.headers as Record<string, string>)['Content-Type']).toBe('application/json')
    expect(init!.body).toBe('{"a":1}')
  })

  it('sends FormData without a JSON content type', async () => {
    fetchMock.mockResolvedValue(response(200, {}))
    const fd = new FormData()
    await request('/upload', { method: 'POST', formData: fd })
    const init = fetchMock.mock.calls[0][1]!
    expect(init.body).toBe(fd)
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined()
  })

  it('returns undefined for 204', async () => {
    fetchMock.mockResolvedValue({ status: 204, ok: true, headers: new Headers(), text: async () => '' } as Response)
    await expect(request('/gone', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('maps the standard error body to an AppError with code, details and request id', async () => {
    fetchMock.mockResolvedValue(
      response(409, { error: { code: 'version_conflict', message: 'Reload.', details: { current: 4 } } }, { 'X-Request-ID': 'req-1' }),
    )
    const err = await request('/x').catch((e: unknown) => e)
    expect(err).toBeInstanceOf(AppError)
    const app = err as AppError
    expect(app.status).toBe(409)
    expect(app.code).toBe('version_conflict')
    expect(app.message).toBe('Reload.')
    expect(app.details).toEqual({ current: 4 })
    expect(app.requestId).toBe('req-1')
  })

  it('wraps a non-envelope failure as http_error and a thrown fetch as network_error', async () => {
    fetchMock.mockResolvedValueOnce(response(502, '<html>bad gateway</html>'))
    const http = (await request('/x').catch((e: unknown) => e)) as AppError
    expect(http.code).toBe('http_error')
    expect(http.status).toBe(502)

    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))
    const net = (await request('/x').catch((e: unknown) => e)) as AppError
    expect(net.code).toBe('network_error')
    expect(net.status).toBe(0)
  })

  it('notifies the unauthorized handler exactly on 401', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    fetchMock.mockResolvedValueOnce(response(401, { error: { code: 'unauthorized', message: 'Sign in.' } }))
    await request('/me').catch(() => undefined)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
    fetchMock.mockResolvedValueOnce(response(403, { error: { code: 'forbidden', message: 'No.' } }))
    await request('/officer').catch(() => undefined)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })
})
