import { useQuery } from '@tanstack/react-query'

import { getHealth } from '@/api/health'

/** The build that answers (US-094). Public; one read, kept for the session; never blocks the page. */
export function useBuildInfo() {
  return useQuery({ queryKey: ['health'], queryFn: getHealth, staleTime: Infinity, retry: 0 })
}
