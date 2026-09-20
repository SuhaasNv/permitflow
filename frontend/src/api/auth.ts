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

/** `takeOver` signs out the device that holds this account's session and continues here (US-093). */
export function login(email: string, password: string, takeOver = false): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: takeOver ? { email, password, take_over: true } : { email, password },
  })
}

/** Ends this sign-in on the server; the token stops working on its next use. */
export function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST', keepalive: true })
}

export function me(): Promise<User> {
  return request<User>('/auth/me')
}
