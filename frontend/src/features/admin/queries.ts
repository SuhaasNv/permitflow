import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { AdminUser, UserCreate, UserPatch } from '@/api/admin'
import { createAdminUser, getAdminOverview, getAdminUsers, getAuditFeed, patchAdminUser } from '@/api/admin'

export const adminKeys = {
  overview: ['admin', 'overview'] as const,
  feed: ['admin', 'feed'] as const,
  users: ['admin', 'users'] as const,
}

/** The overview refreshes every 60 s while open, as the page header says. */
export function useAdminOverview() {
  return useQuery({ queryKey: adminKeys.overview, queryFn: getAdminOverview, refetchInterval: 60_000 })
}

/** Keyset pages: each page carries the cursor of the one after it; null ends the list. */
export function useAuditFeed() {
  return useInfiniteQuery({
    queryKey: adminKeys.feed,
    queryFn: ({ pageParam }) => getAuditFeed(pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  })
}

export function useAdminUsers() {
  return useQuery({ queryKey: adminKeys.users, queryFn: getAdminUsers })
}

function replaceUser(users: { users: AdminUser[]; self_id: string } | undefined, user: AdminUser) {
  if (!users) return users
  return { ...users, users: users.users.map((u) => (u.id === user.id ? user : u)) }
}

export function usePatchUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UserPatch }) => patchAdminUser(id, body),
    onSuccess: (user) => {
      qc.setQueryData(adminKeys.users, (current: { users: AdminUser[]; self_id: string } | undefined) => replaceUser(current, user))
      void qc.invalidateQueries({ queryKey: adminKeys.feed })
    },
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: UserCreate) => createAdminUser(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: adminKeys.users })
      void qc.invalidateQueries({ queryKey: adminKeys.feed })
    },
  })
}
