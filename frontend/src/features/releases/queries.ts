import { useQuery } from '@tanstack/react-query'

import { getHealth } from '@/api/health'

/** The build that answers (US-094). Public; one read, kept for the session; never blocks the page. */
export function useBuildInfo() {
  return useQuery({ queryKey: ['health'], queryFn: getHealth, staleTime: Infinity, retry: 0 })
}

/** Whether release candidates may be listed (US-110): only once /health has answered with an environment other
 * than production. While it loads or has failed the answer is no, so production never flashes a test build. */
export function useShowCandidates(): boolean {
  const { data } = useBuildInfo()
  return data !== undefined && data.environment !== 'production'
}
