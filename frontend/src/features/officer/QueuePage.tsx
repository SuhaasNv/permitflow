import { useEffect, useState } from 'react'

import { PageHeader } from '@/features/shared/PageHeader'
import { EmptyPanel } from '@/features/shared/states'
import { formatRelative } from '@/lib/format'

/** Officer work queue. The list itself arrives with US-020; until then the empty state is the real screen. */
export function OfficerQueuePage() {
  const [checkedAt] = useState(() => new Date().toISOString())
  const [, tick] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => tick((n) => n + 1), 30_000)
    return () => clearInterval(timer)
  }, [])
  return (
    <>
      <PageHeader
        eyebrow="Licensing officer"
        title="Review queue"
        subtitle="Submitted applications, newest activity first. Amber rows are waiting on the operator; blue rows are waiting on you."
      />
      <EmptyPanel
        done
        title="You are all caught up"
        description="No applications currently require review. New submissions and resubmissions appear here as soon as they arrive."
        footnote={`Last checked ${formatRelative(checkedAt)}`}
      />
    </>
  )
}
