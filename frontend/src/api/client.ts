/**
 * Thin fetch client. Adds the bearer token, maps the standard error body
 * `{ error: { code, message, details? } }` to an AppError (REL-001).
 */

// Runtime value first (container, see public/config.js), then the build-time value, then the local default.
export const API_URL: string =
  (typeof window !== 'undefined' && window.__PERMITFLOW__?.apiUrl) || import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> }
}

export class AppError extends Error {
  readonly status: number
  readonly code: string
  readonly details?: Record<string, unknown>
  readonly requestId?: string

  constructor(status: number, body: ApiErrorBody['error'], requestId?: string) {
    super(body.message)
    this.name = 'AppError'
    this.status = status
    this.code = body.code
    this.details = body.details
    this.requestId = requestId
  }
}

let tokenProvider: () => string | null = () => null
export function setTokenProvider(fn: () => string | null): void {
  tokenProvider = fn
}

/** What a 401 said, so the sign-in page can explain why the session ended (US-093). */
export interface UnauthorizedInfo {
  code: string
  message?: string
  details?: Record<string, unknown>
}

/** Called once per 401 so the session can end cleanly (redirect to sign-in with a return path). */
let unauthorizedHandler: (info: UnauthorizedInfo) => void = () => undefined
export function setUnauthorizedHandler(fn: (info: UnauthorizedInfo) => void): void {
  unauthorizedHandler = fn
}
export function notifyUnauthorized(info: UnauthorizedInfo = { code: 'unauthorized' }): void {
  unauthorizedHandler(info)
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) return false
  const err = (value as { error?: unknown }).error
  return typeof err === 'object' && err !== null && 'code' in err && 'message' in err
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  formData?: FormData
  signal?: AbortSignal
  /** Let the browser finish the request after the page is hidden or unloaded (a last autosave). */
  keepalive?: boolean
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const token = tokenProvider()
  if (token) headers.Authorization = `Bearer ${token}`
  let body: BodyInit | undefined
  if (options.formData) {
    body = options.formData
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method ?? 'GET',
      headers,
      body,
      signal: options.signal,
      keepalive: options.keepalive,
    })
  } catch {
    throw new AppError(0, {
      code: 'network_error',
      message: 'Could not reach the server. Check your connection and try again.',
    })
  }
  const requestId = response.headers.get('X-Request-ID') ?? undefined
  if (response.status === 204) return undefined as T
  const text = await response.text()
  let parsed: unknown = null
  if (text) {
    try {
      parsed = JSON.parse(text)
    } catch {
      parsed = null
    }
  }
  if (!response.ok) {
    if (response.status === 401) {
      notifyUnauthorized(
        isApiErrorBody(parsed)
          ? { code: parsed.error.code, message: parsed.error.message, details: parsed.error.details }
          : undefined,
      )
    }
    if (isApiErrorBody(parsed)) throw new AppError(response.status, parsed.error, requestId)
    throw new AppError(response.status, { code: 'http_error', message: `Request failed (${response.status})` }, requestId)
  }
  return parsed as T
}
