import { request } from './client'

export type Role = 'operator' | 'officer' | 'admin'

export interface User {
  id: string
  email: string
  full_name: string
  role: Role
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_at: string
  user: User
}

/** Cookie mode (US-104): no bearer token; the session is an HttpOnly cookie the page cannot read. */
export interface SessionResponse {
  expires_at: string
  user: User
  csrf_token: string
}

/** The sign-in answer tells which mode the server runs: `access_token` is present only in token mode. */
export type LoginResponse = TokenResponse | SessionResponse

export interface MeResponse extends User {
  /** Cookie mode only. */
  csrf_token?: string
}

/** `takeOver` signs out the device that holds this account's session and continues here (US-093). */
export function login(email: string, password: string, takeOver = false): Promise<LoginResponse> {
  return request<LoginResponse>('/auth/login', {
    method: 'POST',
    credentials: 'include',
    body: takeOver ? { email, password, take_over: true } : { email, password },
  })
}

/** Ends this sign-in on the server; the token stops working on its next use. */
export function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST', keepalive: true })
}

/** `first`: no session is known yet (the load-time check for a cookie session), so send credentials. */
export function me(first = false): Promise<MeResponse> {
  return request<MeResponse>('/auth/me', first ? { credentials: 'include' } : {})
}
