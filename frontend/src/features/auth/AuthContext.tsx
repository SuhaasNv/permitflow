import type { ReactNode } from "react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { setTokenProvider } from "@/api/client";
import type { Role, TokenResponse, User } from "@/api/auth";
import { me } from "@/api/auth";

const STORAGE_KEY = "permitflow.session";

interface StoredSession {
  token: string;
  user: User;
  expiresAt: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  ready: boolean;
  signIn: (response: TokenResponse) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function readStored(): StoredSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return null;
    const s = parsed as Partial<StoredSession>;
    if (
      typeof s.token !== "string" ||
      typeof s.expiresAt !== "string" ||
      !s.user
    )
      return null;
    if (new Date(s.expiresAt).getTime() <= Date.now()) return null;
    return { token: s.token, user: s.user, expiresAt: s.expiresAt };
  } catch {
    return null;
  }
}

function writeStored(session: StoredSession | null): void {
  try {
    if (session) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage may be unavailable (private mode); the in-memory session still works.
  }
}

/** Token kept in memory and mirrored to sessionStorage so a reload keeps the session (UC0-A). */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(() =>
    readStored(),
  );
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setTokenProvider(() => session?.token ?? null);
  }, [session]);

  const signOut = useCallback(() => {
    setSession(null);
    writeStored(null);
  }, []);

  // Re-validate a restored session against the server once (role or active flag may have changed).
  useEffect(() => {
    let cancelled = false;
    if (!session) {
      setReady(true);
      return;
    }
    setTokenProvider(() => session.token);
    me()
      .then((user) => {
        if (cancelled) return;
        setSession((current) => (current ? { ...current, user } : current));
      })
      .catch(() => {
        if (!cancelled) signOut();
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = useCallback((response: TokenResponse) => {
    const next = {
      token: response.access_token,
      user: response.user,
      expiresAt: response.expires_at,
    };
    setSession(next);
    writeStored(next);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user: session?.user ?? null,
      token: session?.token ?? null,
      ready,
      signIn,
      signOut,
    }),
    [session, ready, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

export function homeFor(role: Role): string {
  switch (role) {
    case "operator":
      return "/app/dashboard";
    case "officer":
      return "/officer/queue";
    case "admin":
      return "/admin/overview";
  }
}
