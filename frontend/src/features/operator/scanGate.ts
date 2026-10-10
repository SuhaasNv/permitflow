import type { DocumentSlotView } from '@/api/applications'

/** US-099: why submitting waits while a document is blocked or being scanned; null when nothing holds it (and always null with the scan off). */
export function scanGateReason(slots: DocumentSlotView[], action: string): string | null {
  const blocked = slots.filter((s) => s.document?.scan_state === 'infected').length
  const scanning = slots.filter((s) => s.document?.scan_state === 'scanning').length
  if (blocked + scanning === 0) return null
  const counts = [blocked ? `${blocked} blocked` : '', scanning ? `${scanning} being scanned` : ''].filter(Boolean).join(', ')
  return `${action} opens when no document is blocked or being scanned. ${counts}.`
}
