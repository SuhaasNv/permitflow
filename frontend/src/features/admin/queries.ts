import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import type { AdminUser, PlatformSetting, PlatformSettings, SettingValue, SettingWrite, UserCreate, UserPatch } from '@/api/admin'
import {
  changePlatformSetting,
  createAdminUser,
  getAdminOverview,
  getAdminUsers,
  getAuditFeed,
  getPlatformSettings,
  getSettingsHistory,
  patchAdminUser,
  revertSettingChange,
} from '@/api/admin'

export const adminKeys = {
  overview: ['admin', 'overview'] as const,
  feed: ['admin', 'feed'] as const,
  users: ['admin', 'users'] as const,
  settings: ['admin', 'settings'] as const,
  settingsHistory: ['admin', 'settings-history'] as const,
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

export function usePlatformSettings() {
  return useQuery({ queryKey: adminKeys.settings, queryFn: getPlatformSettings })
}

/** Newest first, keyset-paged, optionally for one setting; each page carries the cursor of the next. */
export function useSettingsHistory(key: string | null) {
  return useInfiniteQuery({
    queryKey: [...adminKeys.settingsHistory, key] as const,
    queryFn: ({ pageParam }) => getSettingsHistory(key, pageParam),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor,
  })
}

/** A write returns the setting as it now stands: swap it into the list, then refresh what shows the change. */
function useAfterSettingWrite() {
  const qc = useQueryClient()
  return (setting: PlatformSetting) => {
    qc.setQueryData(adminKeys.settings, (current: PlatformSettings | undefined) =>
      current ? { ...current, settings: current.settings.map((s) => (s.key === setting.key ? setting : s)) } : current,
    )
    void qc.invalidateQueries({ queryKey: adminKeys.settingsHistory })
    void qc.invalidateQueries({ queryKey: adminKeys.feed })
    void qc.invalidateQueries({ queryKey: adminKeys.overview })
  }
}

export function useChangeSetting() {
  const after = useAfterSettingWrite()
  return useMutation({
    mutationFn: ({ key, value, ...write }: SettingWrite & { key: string; value: SettingValue }) =>
      changePlatformSetting(key, { value, ...write }),
    onSuccess: after,
  })
}

export function useRevertSetting() {
  const after = useAfterSettingWrite()
  return useMutation({
    mutationFn: ({ entryId, ...write }: SettingWrite & { entryId: string }) => revertSettingChange(entryId, write),
    onSuccess: after,
  })
}
