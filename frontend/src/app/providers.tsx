import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useState } from 'react'

import { AppError } from '@/api/client'
import { ToastProvider } from '@/features/shared/Toast'

function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof AppError && error.status >= 400 && error.status < 500) return false
  return failureCount < 2
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: shouldRetry,
            refetchOnWindowFocus: false,
            staleTime: 5_000,
          },
        },
      }),
  )
  return (
    <QueryClientProvider client={client}>
      <ToastProvider>{children}</ToastProvider>
    </QueryClientProvider>
  )
}
