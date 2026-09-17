import type { ReactNode } from 'react'

import { Logo } from '@/features/shared/Logo'

interface AppShellProps {
  children: ReactNode
}

/** Masthead + top bar + content. Role navigation is added by the auth story (US-001). */
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <div className="flex h-7 items-center gap-2 bg-text px-4 text-xs text-[#c5cbd3] sm:px-6">
        <span className="font-semibold text-white">Secure licensing portal</span>
        <span>· Food Establishments Unit</span>
      </div>
      <header className="flex h-14 items-center gap-4 border-b border-line bg-surface px-4 sm:px-6">
        <Logo />
      </header>
      <main className="flex-1">{children}</main>
    </div>
  )
}
