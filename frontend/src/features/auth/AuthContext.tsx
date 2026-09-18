import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { AppError, setTokenProvider, setUnauthorizedHandler } from '@/api/client'
import { setUploadTokenProvider } from '@/api/documents'
import type { Role, TokenResponse, User } from '@/api/auth'
import { me } from '@/api/auth'

const STORAGE_KEY = 'permitflow.session'

interface StoredSession {
  token: string
  user: User
  expiresAt: string
}

export type EndedReason = 'expired' | 'unauthorized' | null

interface AuthState {
  user: User | null
  token: string | null
  expiresAt: string | null
  ready: boolean
  /** Why the last session ended without the user clicking Sign out, for the sign-in page to explain. */
  endedReason: EndedReason
  signIn: (response: TokenResponse) => void
  signOut: () => void
}

const AuthContext = createContext<AuthState | null>(null)

function readStored(): StoredSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null) return null
    const s = parsed as Partial<StoredSession>
    if (typeof s.token !== 'string' || typeof s.expiresAt !== 'string' || !s.user) return null
    if (new Date(s.expiresAt).getTime() <= Date.now()) return null
    return { token: s.token, user: s.user, expiresAt: s.expiresAt }
  } catch {
    return null
  }
}

function writeStored(session: StoredSession | null): void {
  try {
    if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    else sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage may be unavailable (private mode); the in-memory session still works.
  }
}

/** Token kept in memory and mirrored to sessionStorage so a reload keeps the session (UC0-A). */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(() => readStored())
  const [ready, setReady] = useState(false)
  const [endedReason, setEndedReason] = useState<EndedReason>(null)

  useEffect(() => {
    setTokenProvider(() => session?.token ?? null)
    setUploadTokenProvider(() => session?.token ?? null)
  }, [session])

  // Every cached query belongs to the account that fetched it: drop the cache with the session.
  const queryClient = useQueryClient()
  const signOut = useCallback(() => {
    setSession(null)
    writeStored(null)
    queryClient.clear()
  }, [queryClient])

  // A 401 from any request ends the session in one place; the sign-in page explains and keeps the return path.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setSession((current) => {
        if (current) setEndedReason('unauthorized')
        return null
      })
      writeStored(null)
      queryClient.clear()
    })
    return () => setUnauthorizedHandler(() => undefined)
  }, [queryClient])

  // Sign out proactively when the token expires, so the user is never left with a dead session.
  useEffect(() => {
    if (!session) return
    const ms = new Date(session.expiresAt).getTime() - Date.now()
    if (ms <= 0) {
      setEndedReason('expired')
      signOut()
      return
    }
    const timer = setTimeout(
      () => {
        setEndedReason('expired')
        signOut()
      },
      Math.min(ms, 2_147_000_000),
    )
    return () => clearTimeout(timer)
  }, [session, signOut])

  // Re-validate a restored session against the server once (role or active flag may have changed).
  useEffect(() => {
    let cancelled = false
    if (!session) {
      setReady(true)
      return
    }
    setTokenProvider(() => session.token)
    me()
      .then((user) => {
        if (cancelled) return
        setSession((current) => (current ? { ...current, user } : current))
      })
      .catch((error: unknown) => {
        // Only a definite rejection ends the session; a network blip keeps the token for a retry.
        if (!cancelled && error instanceof AppError && (error.status === 401 || error.status === 403)) signOut()
      })
      .finally(() => {
        if (!cancelled) setReady(true)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const signIn = useCallback((response: TokenResponse) => {
    const next = {
      token: response.access_token,
      user: response.user,
      expiresAt: response.expires_at,
    }
    setSession(next)
    writeStored(next)
    setEndedReason(null)
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      user: session?.user ?? null,
      token: session?.token ?? null,
      expiresAt: session?.expiresAt ?? null,
      ready,
      endedReason,
      signIn,
      signOut,
    }),
    [session, ready, endedReason, signIn, signOut],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

export function homeFor(role: Role): string {
  switch (role) {
    case 'operator':
      return '/app/dashboard'
    case 'officer':
      return '/officer/queue'
    case 'admin':
      return '/admin/overview'
  }
}
