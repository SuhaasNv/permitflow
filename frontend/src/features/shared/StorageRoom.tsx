import type { StorageView } from '@/api/applications'
import { formatBytes } from '@/lib/format'

/** One sentence before an upload: how much of the application's storage room is left (US-085). */
export function storageRoomSentence(storage: StorageView): string {
  const budget = formatBytes(storage.budget_bytes)
  if (storage.remaining_bytes <= 0) return `This application has used its ${budget} of storage room. Remove a file you no longer need before adding one.`
  return `${formatBytes(storage.remaining_bytes)} of the application's ${budget} storage room is left.`
}

export function StorageRoom({ storage, className }: { storage: StorageView | null; className?: string }) {
  if (!storage) return null
  return (
    <span className={className} data-testid="storage-room">
      {storageRoomSentence(storage)}
    </span>
  )
}
