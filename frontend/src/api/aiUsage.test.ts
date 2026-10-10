import { afterEach, describe, expect, it, vi } from 'vitest'

import { downloadAiUsageCsv } from './aiUsage'
import { AppError } from './client'
import { setUploadTokenProvider } from './documents'

const query = { user: 'u1', reference: 'PF-2026-001109', from: '2026-10-04', to: '2026-10-10' }

describe('downloadAiUsageCsv', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    setUploadTokenProvider(() => null)
  })

  it('asks for the CSV with the filters and the bearer header, never a token in the address', async () => {
    setUploadTokenProvider(() => 'secret-token')
    const fetchMock = vi.fn().mockResolvedValue(new Response('a,b', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    URL.createObjectURL = vi.fn(() => 'blob:csv')
    URL.revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    await downloadAiUsageCsv(query)
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/admin/ai-usage.csv?user_id=u1&reference=PF-2026-001109&from=2026-10-04&to=2026-10-10')
    expect(url).not.toContain('secret-token')
        expect(init.headers).toEqual({ Authorization: 'Bearer secret-token' })
    expect(click).toHaveBeenCalledOnce()
  })

  it('throws a readable error when the server refuses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('', { status: 500 })))
    await expect(downloadAiUsageCsv(query)).rejects.toBeInstanceOf(AppError)
  })
})
