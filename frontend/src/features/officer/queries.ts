import { useQuery } from '@tanstack/react-query'

import { getQueue } from '@/api/officer'

export const officerKeys = {
  queue: ['officer', 'queue'] as const,
}

/** The queue refreshes every 30 s while open so new submissions appear without a reload. */
export function useQueue() {
  return useQuery({ queryKey: officerKeys.queue, queryFn: getQueue, refetchInterval: 30_000 })
}
