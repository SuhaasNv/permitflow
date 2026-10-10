/**
 * Thin fetch client. Sends the session (a bearer token, or in cookie mode the cookie plus the CSRF header,
 * US-104 / ADR-018), maps the standard error body
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

/**
 * Cookie mode (US-104): the server keeps the session in an HttpOnly cookie and hands the page only a CSRF value,
 * held here in memory and never stored. A non-null value IS the mode; the sign-in answer decides it.
 */
let csrfToken: string | null = null
export function setCsrfToken(value: string | null): void {
  csrfToken = value
}
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

/** Fetch options carrying the session, for direct fetches outside `request` (downloads). Token mode: the bearer. */
export function authInit(token: string | null, method = 'GET'): { headers: Record<string, string>; credentials?: 'include' } {
  if (csrfToken === null) return { headers: token ? { Authorization: `Bearer ${token}` } : {} }
  return { headers: SAFE_METHODS.has(method) ? {} : { 'X-CSRF-Token': csrfToken }, credentials: 'include' }
}

/** The same for an XMLHttpRequest (uploads): the cookie goes with `withCredentials`, the bearer as a header. */
export function authXhr(xhr: XMLHttpRequest, token: string | null): void {
  const { headers, credentials } = authInit(token, 'POST')
  xhr.withCredentials = credentials === 'include'
  for (const [name, value] of Object.entries(headers)) xhr.setRequestHeader(name, value)
}

/** One re-read of /auth/me for a fresh CSRF value; false when it gave none (not a cookie session any more). */
export async function refreshCsrf(): Promise<boolean> {
  const out = await request<{ csrf_token?: string }>('/auth/me')
  if (out.csrf_token) csrfToken = out.csrf_token
  return Boolean(out.csrf_token)
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
  /** Before any session is known (sign-in, the load-time /auth/me): send credentials, so a cookie server's
   * Set-Cookie sticks and its cookie is read. Both server modes allow credentials for the listed origins. */
  credentials?: 'include'
  /** Set by `request` itself on the one retry after a refreshed CSRF value. */
  retried?: boolean
}

/** When a signed-in request last succeeded: the server's idle clock restarts on each one (US-093, US-095). */
let lastActivityAt = Date.now()
export function lastActivity(): number {
  return lastActivityAt
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const token = tokenProvider()
  const method = options.method ?? 'GET'
  const cookie = csrfToken !== null
  if (cookie) {
    if (!SAFE_METHODS.has(method)) headers['X-CSRF-Token'] = csrfToken as string
  } else if (token) headers.Authorization = `Bearer ${token}`
  let body: BodyInit | undefined
  if (options.formData) {
    body = options.formData
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }
  const send = (credentials?: 'include') =>
    fetch(`${API_URL}${path}`, { method, headers, body, signal: options.signal, keepalive: options.keepalive, credentials })
  let response: Response
  try {
    response = await send(cookie ? 'include' : options.credentials)
  } catch {
    throw new AppError(0, {
      code: 'network_error',
      message: 'Could not reach the server. Check your connection and try again.',
    })
  }
  const requestId = response.headers.get('X-Request-ID') ?? undefined
  if ((token || cookie) && response.ok) lastActivityAt = Date.now()
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
    if (cookie && !options.retried && response.status === 403 && isApiErrorBody(parsed) && parsed.error.code === 'csrf_failed') {
      // The CSRF value went stale (a new sign-in elsewhere in this browser): read it again and retry once.
      if (await refreshCsrf().catch(() => false)) return request<T>(path, { ...options, retried: true })
    }
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
