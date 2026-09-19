import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AppError, setUnauthorizedHandler } from './client'
import { downloadDocument, downloadLicence, fetchLicencePreview, setUploadTokenProvider, uploadDocument, validateFile } from './documents'

function file(name: string, size: number, type = 'application/pdf'): File {
  const f = new File([new Uint8Array(size)], name, { type })
  return f
}

describe('validateFile (SEC-005 client pre-check)', () => {
  it('accepts the allowlist regardless of case and rejects everything else', () => {
    expect(validateFile(file('plan.PDF', 10))).toBeNull()
    expect(validateFile(file('scan.jpeg', 10))).toBeNull()
    expect(validateFile(file('notes.txt', 10))).toBeNull()
    expect(validateFile(file('macro.docx', 10))).toMatch(/not accepted/)
    expect(validateFile(file('noextension', 10))).toMatch(/not accepted/)
  })

  it('rejects empty files and files over 10 MB', () => {
    expect(validateFile(file('empty.pdf', 0))).toMatch(/empty/)
    expect(validateFile(file('big.pdf', 10 * 1024 * 1024 + 1))).toMatch(/larger than 10 MB/)
    expect(validateFile(file('edge.pdf', 10 * 1024 * 1024))).toBeNull()
  })
})

class FakeXhr {
  static instances: FakeXhr[] = []
  status = 0
  responseText = ''
  upload: { onprogress: ((e: { lengthComputable: boolean; loaded: number; total: number }) => void) | null } = {
    onprogress: null,
  }
  onload: (() => void) | null = null
  onerror: (() => void) | null = null
  headers: Record<string, string> = {}
  sent: FormData | null = null
  opened: [string, string] | null = null
  responseHeaders: Record<string, string> = {}
  constructor() {
    FakeXhr.instances.push(this)
  }
  open(method: string, url: string): void {
    this.opened = [method, url]
  }
  setRequestHeader(k: string, v: string): void {
    this.headers[k] = v
  }
  getResponseHeader(k: string): string | null {
    return this.responseHeaders[k] ?? null
  }
  send(body: FormData): void {
    this.sent = body
  }
}

describe('uploadDocument (XHR with progress)', () => {
  beforeEach(() => {
    FakeXhr.instances = []
    vi.stubGlobal('XMLHttpRequest', FakeXhr)
    setUploadTokenProvider(() => 'tok')
    setUnauthorizedHandler(() => undefined)
  })
  afterEach(() => vi.unstubAllGlobals())

  it('posts the type and file with the bearer token, reports progress and resolves the result', async () => {
    const progress: number[] = []
    const p = uploadDocument('app-1', 'floor_plan', file('plan.pdf', 3), (f) => progress.push(f))
    const xhr = FakeXhr.instances[0]
    expect(xhr.opened?.[0]).toBe('POST')
    expect(xhr.opened?.[1]).toMatch(/\/applications\/app-1\/documents$/)
    expect(xhr.headers.Authorization).toBe('Bearer tok')
    expect(xhr.sent?.get('document_type')).toBe('floor_plan')
    expect((xhr.sent!.get('file') as File).name).toBe('plan.pdf')
    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 4 })
    xhr.upload.onprogress?.({ lengthComputable: false, loaded: 0, total: 0 })
    xhr.status = 200
    xhr.responseText = JSON.stringify({ application: { id: 'app-1' }, document: { id: 'd1' }, unchanged: false })
    xhr.onload?.()
    await expect(p).resolves.toMatchObject({ unchanged: false, document: { id: 'd1' } })
    expect(progress).toEqual([0.25])
  })

  it('rejects with the server envelope, notifies on 401, and maps a network failure', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    const p1 = uploadDocument('app-1', 'floor_plan', file('plan.pdf', 3), () => undefined)
    const x1 = FakeXhr.instances[0]
    x1.status = 415
    x1.responseHeaders['X-Request-ID'] = 'r-9'
    x1.responseText = JSON.stringify({ error: { code: 'unsupported_type', message: 'PDF only.' } })
    x1.onload?.()
    const e1 = (await p1.catch((e: unknown) => e)) as AppError
    expect(e1.code).toBe('unsupported_type')
    expect(e1.requestId).toBe('r-9')

    const p2 = uploadDocument('app-1', 'floor_plan', file('plan.pdf', 3), () => undefined)
    const x2 = FakeXhr.instances[1]
    x2.status = 401
    x2.responseText = 'not json'
    x2.onload?.()
    const e2 = (await p2.catch((e: unknown) => e)) as AppError
    expect(e2.code).toBe('http_error')
    expect(onUnauthorized).toHaveBeenCalledTimes(1)

    const p3 = uploadDocument('app-1', 'floor_plan', file('plan.pdf', 3), () => undefined)
    FakeXhr.instances[2].onerror?.()
    const e3 = (await p3.catch((e: unknown) => e)) as AppError
    expect(e3.code).toBe('network_error')
  })
})

describe('downloads', () => {
  const fetchMock = vi.fn<typeof fetch>()
  const clicks: string[] = []
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    setUploadTokenProvider(() => 'tok')
    setUnauthorizedHandler(() => undefined)
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:x')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      clicks.push(this.download)
    })
    clicks.length = 0
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
    vi.useRealTimers()
    fetchMock.mockReset()
  })

  it('downloads a document with the original name and revokes the object URL afterwards', async () => {
    fetchMock.mockResolvedValue(new Response(new Blob(['%PDF']), { status: 200 }))
    await downloadDocument('app-1', 'doc-1', 'plan.pdf')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/documents\/doc-1\/download$/)
    expect((fetchMock.mock.calls[0][1]!.headers as Record<string, string>).Authorization).toBe('Bearer tok')
    expect(clicks).toEqual(['plan.pdf'])
    vi.runAllTimers()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:x')
  })

  it('names the licence file after the licence number and explains 404 and 409', async () => {
    fetchMock.mockResolvedValueOnce(new Response(new Blob(['%PDF']), { status: 200 }))
    await downloadLicence('app-1', 'FEL-2026-000005')
    expect(clicks).toEqual(['FEL-2026-000005.pdf'])

    fetchMock.mockResolvedValueOnce(new Response('', { status: 404 }))
    const e404 = (await downloadLicence('app-1', 'x').catch((e: unknown) => e)) as AppError
    expect(e404.message).toMatch(/not available/)

    fetchMock.mockResolvedValueOnce(new Response('', { status: 409 }))
    const e409 = (await fetchLicencePreview('app-1').catch((e: unknown) => e)) as AppError
    expect(e409.message).toMatch(/this state/)
  })

  it('reports a missing file on 404 and notifies on 401', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    fetchMock.mockResolvedValueOnce(new Response('', { status: 404 }))
    const e = (await downloadDocument('app-1', 'doc-1', 'plan.pdf').catch((x: unknown) => x)) as AppError
    expect(e.message).toMatch(/no longer available/)
    fetchMock.mockResolvedValueOnce(new Response('', { status: 401 }))
    await downloadDocument('app-1', 'doc-1', 'plan.pdf').catch(() => undefined)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
  })
})
