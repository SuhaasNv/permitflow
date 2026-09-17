import { EmptyPanel } from '@/features/shared/states'
import { PageHeader } from '@/features/shared/PageHeader'

export function OfficerQueuePage() {
  return (
    <>
      <PageHeader title="Review queue" subtitle="All submitted applications, newest activity first." />
      <EmptyPanel title="No applications in the queue" description="Submitted applications appear here (US-020)." />
    </>
  )
}
